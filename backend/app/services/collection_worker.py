import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import Session, sessionmaker

from ..db.models import CollectionJob
from ..db.database import get_db, engine
from .brightdata_service import BrightDataService
from .influencer_service import InfluencerService
from .s3_service import S3Service

logger = logging.getLogger(__name__)

KST_OFFSET = timedelta(hours=9)


def now_kst() -> datetime:
    return datetime.utcnow() + KST_OFFSET

class CollectionWorker:
    """백그라운드에서 수집 작업을 처리하는 워커"""
    
    def __init__(self):
        self.is_running = False
        # BrightDataService는 나중에 세션과 함께 초기화
        self.brightdata_service = None  
        self.s3_service = S3Service()
        # 독립적인 DB 세션 팩토리 생성
        self.Session = sessionmaker(bind=engine)
        self._thread: Optional[threading.Thread] = None
        
    async def start(self):
        """워커 시작"""
        if self.is_running:
            logger.warning("워커가 이미 실행 중입니다")
            return
            
        self.is_running = True
        logger.info("🚀 수집 워커 시작됨")

        self.reset_orphaned_jobs()

        while self.is_running:
            try:
                await self.process_pending_jobs()
                # 5초마다 큐를 확인
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"워커 처리 중 오류 발생: {str(e)}")
                await asyncio.sleep(10)  # 오류 시 10초 대기

    def _run_forever(self):
        try:
            asyncio.run(self.start())
        except Exception as exc:  # noqa: BLE001 - 기록 후 종료
            logger.error(f"워커 스레드 오류: {exc}")
        finally:
            self.is_running = False
            self._thread = None

    def start_background(self):
        """워커를 별도 스레드에서 실행"""
        if self._thread and self._thread.is_alive():
            logger.warning("워커가 이미 백그라운드에서 실행 중입니다")
            return

        self._thread = threading.Thread(
            target=self._run_forever,
            name="collection-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """워커 중지"""
        self.is_running = False
        logger.info("⏹️ 수집 워커 중지됨")
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5)
            if thread.is_alive():
                logger.warning("워커 스레드가 5초 안에 종료되지 않았습니다")
        self._thread = None

    def is_active(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def reset_orphaned_jobs(self):
        """중단된 processing 작업을 다시 대기 상태로 되돌립니다."""
        session = self.Session()
        try:
            now = now_kst()
            threshold = now - timedelta(minutes=5)
            stale_jobs = session.query(CollectionJob).filter(
                CollectionJob.status == "processing",
                or_(
                    CollectionJob.started_at.is_(None),
                    CollectionJob.started_at < threshold,
                    CollectionJob.started_at > now
                )
            ).all()

            for job in stale_jobs:
                job.status = "pending"
                if job.collect_profile:
                    job.profile_status = "pending"
                # collect_posts 필드 제거됨
                    # posts_status 필드 제거됨
                if job.collect_reels:
                    job.reels_status = "pending"
                job.started_at = None
                job.completed_at = None
                job.error_message = None

            if stale_jobs:
                session.commit()
        finally:
            session.close()
    
    async def process_pending_jobs(self):
        """대기 중인 작업들을 2단계로 순차 처리: 1) 모든 프로필 먼저, 2) 그 다음 릴스"""
        db = self.Session()
        try:
            # 현재 처리 중인 작업이 있는지 확인
            processing_jobs = db.query(CollectionJob).filter(
                CollectionJob.status == "processing"
            ).count()
            
            if processing_jobs > 0:
                logger.info(f"⏳ 처리 중인 작업 {processing_jobs}개가 있어서 대기 중...")
                return
            
            # 1단계: 프로필 수집이 필요한 작업 우선 처리
            profile_pending_job = db.query(CollectionJob).filter(
                CollectionJob.status == "pending",
                CollectionJob.collect_profile == True,
                CollectionJob.profile_status == "pending"
            ).order_by(
                CollectionJob.priority.desc(),
                CollectionJob.created_at.asc()
            ).first()
            
            if profile_pending_job:
                logger.info(f"📋 [1단계: 프로필] 처리할 작업 발견: {profile_pending_job.username}")
                await self.process_profile_only(profile_pending_job.job_id)
                return
            
            # 2단계: 모든 프로필 수집이 완료되면 릴스 수집 시작
            reels_pending_job = db.query(CollectionJob).filter(
                CollectionJob.status == "pending",
                CollectionJob.collect_reels == True,
                CollectionJob.reels_status == "pending"
            ).order_by(
                CollectionJob.priority.desc(),
                CollectionJob.created_at.asc()
            ).first()
            
            if reels_pending_job:
                logger.info(f"📋 [2단계: 릴스] 처리할 작업 발견: {reels_pending_job.username}")
                await self.process_reels_only(reels_pending_job.job_id)
                return
            
            # 모든 작업 완료
            logger.debug("✅ 모든 대기 작업이 완료되었습니다")
            
        finally:
            db.close()
    
    async def process_profile_only(self, job_id: str):
        """프로필만 수집 (1단계)"""
        db = self.Session()
        try:
            job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
            if not job or job.profile_status != "pending":
                return
            
            # 작업 상태를 processing으로 변경
            job.status = "processing"
            job.profile_status = "processing"
            job.started_at = now_kst()
            db.commit()
            
            logger.info(f"🔄 [프로필 수집 시작] {job.username} ({job.url})")
            
            # 서비스 초기화
            influencer_service = InfluencerService(db, self.s3_service)
            brightdata_service = BrightDataService(db)
            
            # URL에서 username 추출
            url_username = brightdata_service._extract_username_from_url(job.url)
            
            # 기존 인플루언서 계정 삭제
            logger.info(f"🗑️ 기존 인플루언서 계정 삭제: {url_username}")
            try:
                deleted_count = 0
                if influencer_service.delete_profile(url_username):
                    deleted_count += 1
                
                variations = [url_username.lower(), url_username.upper(), url_username.title()]
                for variation in variations:
                    if variation != url_username and influencer_service.delete_profile(variation):
                        deleted_count += 1
                
                if deleted_count > 0:
                    logger.info(f"✅ 기존 계정 {deleted_count}개 삭제 완료")
            except Exception as e:
                logger.error(f"❌ 기존 계정 삭제 실패: {str(e)}")
            
            # 프로필 수집
            try:
                logger.info(f"📡 프로필 API 요청: {url_username}")
                profile_result = await asyncio.wait_for(
                    brightdata_service._collect_single_data_type(
                        job.url, url_username, "profile"
                    ),
                    timeout=60  # 프로필 최대 1분
                )
                
                if profile_result and profile_result.get("profile"):
                    await influencer_service.save_profile_data(profile_result["profile"], url_username)
                    job.profile_status = "completed"
                    job.profile_count = 1
                    logger.info(f"✅ 프로필 수집 완료: {url_username}")
                else:
                    job.profile_status = "failed"
                    logger.error(f"❌ 프로필 수집 실패: {url_username}")
            except asyncio.TimeoutError:
                job.profile_status = "failed"
                logger.error(f"⏰ 프로필 수집 타임아웃: {url_username}")
            except Exception as e:
                job.profile_status = "failed"
                logger.error(f"❌ 프로필 수집 오류: {url_username} - {str(e)}")
            
            # 릴스 수집 여부 확인하여 작업 상태 결정
            if job.collect_reels:
                # 릴스도 수집해야 하면 pending으로 유지
                job.status = "pending"
            else:
                # 프로필만 수집하면 완료
                job.status = "completed" if job.profile_status == "completed" else "failed"
                job.completed_at = now_kst()
            
            db.commit()
            logger.info(f"💾 프로필 작업 상태 저장: {url_username} - {job.profile_status}")
            
            # BrightData API rate limit 방지를 위한 대기
            await asyncio.sleep(3)
            
        except Exception as e:
            logger.error(f"🔥 프로필 처리 중 오류: {job_id} - {str(e)}")
            try:
                job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
                if job:
                    job.status = "pending" if job.collect_reels else "failed"
                    job.profile_status = "failed"
                    job.error_message = str(e)
                    db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()
    
    async def process_reels_only(self, job_id: str):
        """릴스만 수집 (2단계)"""
        db = self.Session()
        try:
            job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
            if not job or job.reels_status != "pending":
                return
            
            # 작업 상태를 processing으로 변경
            job.status = "processing"
            job.reels_status = "processing"
            if not job.started_at:
                job.started_at = now_kst()
            db.commit()
            
            logger.info(f"🔄 [릴스 수집 시작] {job.username} ({job.url})")
            
            # 서비스 초기화
            influencer_service = InfluencerService(db, self.s3_service)
            brightdata_service = BrightDataService(db)
            
            # URL에서 username 추출
            url_username = brightdata_service._extract_username_from_url(job.url)
            
            # 릴스 수집
            try:
                logger.info(f"📡 릴스 API 요청: {url_username}")
                reels_result = await asyncio.wait_for(
                    brightdata_service._collect_single_data_type(
                        job.url, url_username, "reels"
                    ),
                    timeout=600  # 릴스 최대 10분
                )
                
                if reels_result and reels_result.get("reels"):
                    saved_reels = await influencer_service.save_reels_data(reels_result["reels"], url_username)
                    job.reels_status = "completed"
                    job.reels_count = len(saved_reels)
                    logger.info(f"✅ 릴스 수집 완료: {url_username} - {len(saved_reels)}개")
                else:
                    job.reels_status = "failed"
                    logger.error(f"❌ 릴스 수집 실패: {url_username}")
            except asyncio.TimeoutError:
                job.reels_status = "failed"
                logger.error(f"⏰ 릴스 수집 타임아웃: {url_username}")
            except Exception as e:
                job.reels_status = "failed"
                logger.error(f"❌ 릴스 수집 오류: {url_username} - {str(e)}")
                try:
                    db.rollback()
                except Exception:
                    pass
            
            # 전체 작업 완료 처리
            if (not job.collect_profile or job.profile_status == "completed") and \
               (not job.collect_reels or job.reels_status == "completed"):
                job.status = "completed"
                logger.info(f"✅ 전체 작업 완료: {url_username}")
            else:
                job.status = "failed"
                logger.error(f"❌ 일부 작업 실패: {url_username}")
            
            job.completed_at = now_kst()
            db.commit()
            logger.info(f"💾 릴스 작업 상태 저장: {url_username} - {job.reels_status}")
            
            # BrightData API rate limit 방지를 위한 대기
            await asyncio.sleep(3)
            
        except Exception as e:
            logger.error(f"🔥 릴스 처리 중 오류: {job_id} - {str(e)}")
            try:
                job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
                if job:
                    job.status = "failed"
                    job.reels_status = "failed"
                    job.error_message = str(e)
                    job.completed_at = now_kst()
                    db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()
    
    async def process_single_job(self, job_id: str):
        """개별 작업 처리"""
        db = self.Session()
        try:
            # 작업 조회 및 상태 확인
            job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
            if not job or job.status != "pending":
                return
            
            # 작업 상태를 processing으로 변경
            job.status = "processing"
            job.started_at = now_kst()
            db.commit()
            
            logger.info(f"🔄 작업 처리 시작: {job.username} ({job.url})")
            
            # 인플루언서 서비스 초기화
            influencer_service = InfluencerService(db, self.s3_service)
            
            # BrightDataService 초기화 (DB 세션과 함께)
            brightdata_service = BrightDataService(db)
            
            # URL에서 username 추출
            url_username = brightdata_service._extract_username_from_url(job.url)
            
            # 기존 인플루언서 계정 삭제 (수집 전 필수) - 중복키 이슈 완전 방지
            logger.info(f"🗑️ 기존 인플루언서 계정 삭제 시작: {url_username}")
            try:
                # 여러 변형으로 기존 계정 확인 및 삭제
                deleted_count = 0
                
                # 1. 정확한 사용자명으로 삭제
                if influencer_service.delete_profile(url_username):
                    deleted_count += 1
                    
                # 2. 대소문자 변형도 확인
                variations = [url_username.lower(), url_username.upper(), url_username.title()]
                for variation in variations:
                    if variation != url_username and influencer_service.delete_profile(variation):
                        deleted_count += 1
                
                if deleted_count > 0:
                    logger.info(f"✅ 기존 인플루언서 계정 {deleted_count}개 삭제 완료: {url_username}")
                else:
                    logger.info(f"ℹ️ 삭제할 기존 계정이 없음: {url_username}")
                    
                # 3. 최종 확인 - DB에서 완전히 제거되었는지 검증
                remaining = influencer_service.get_profile_by_username(url_username)
                if remaining:
                    logger.warning(f"⚠️ 계정이 아직 남아있음 - 강제 삭제: {url_username}")
                    influencer_service.delete_profile(url_username)
                    
            except Exception as e:
                logger.error(f"❌ 기존 계정 삭제 실패: {url_username} - {str(e)}")
                # 삭제 실패해도 계속 진행 (업데이트 모드로 처리)
            
            # 수집 옵션 설정 - 게시물 수집은 항상 비활성화
            collect_options = {
                "collectProfile": job.collect_profile,
                # collectPosts 필드 제거됨
                "collectReels": job.collect_reels
            }
            
            # 개별 데이터 수집 및 즉시 상태 업데이트
            try:
                # 프로필 수집
                if job.collect_profile:
                    logger.info(f"🔄 프로필 수집 시작: {job.username}")
                    try:
                        profile_result = await asyncio.wait_for(
                            brightdata_service._collect_single_data_type(
                                job.url, url_username, "profile"
                            ),
                            timeout=60  # 프로필 최대 1분
                        )
                        
                        if profile_result and profile_result.get("profile"):
                            await influencer_service.save_profile_data(profile_result["profile"], url_username)
                            job.profile_status = "completed"
                            job.profile_count = 1
                            logger.info(f"✅ 프로필 수집 완료: {job.username}")
                        else:
                            job.profile_status = "failed"
                            logger.error(f"❌ 프로필 수집 실패: {job.username}")
                    except asyncio.TimeoutError:
                        job.profile_status = "failed"
                        logger.error(f"⏰ 프로필 수집 타임아웃 (1분 초과): {job.username}")
                    except Exception as e:
                        job.profile_status = "failed"
                        logger.error(f"❌ 프로필 수집 오류: {job.username} - {str(e)}")
                    
                    # 프로필 상태만 먼저 커밋
                    db.commit()
                
                # 릴스 수집
                if job.collect_reels:
                    logger.info(f"🔄 릴스 수집 시작: {job.username}")
                    try:
                        reels_result = await asyncio.wait_for(
                            brightdata_service._collect_single_data_type(
                                job.url, url_username, "reels"
                            ),
                            timeout=600  # 릴스 최대 10분
                        )
                        
                        if reels_result and reels_result.get("reels"):
                            saved_reels = await influencer_service.save_reels_data(reels_result["reels"], url_username)
                            job.reels_status = "completed"
                            job.reels_count = len(saved_reels)
                            logger.info(f"✅ 릴스 수집 완료: {job.username} - {len(saved_reels)}개")
                        else:
                            job.reels_status = "failed"
                            logger.error(f"❌ 릴스 수집 실패: {job.username}")
                    except asyncio.TimeoutError:
                        job.reels_status = "failed"
                        logger.error(f"⏰ 릴스 수집 타임아웃 (10분 초과): {job.username}")
                    except Exception as e:
                        job.reels_status = "failed"
                        logger.error(f"❌ 릴스 수집 오류: {job.username} - {str(e)}")
                        # 세션 롤백하여 정리
                        try:
                            db.rollback()
                            logger.info(f"🔄 세션 롤백 완료: {job.username}")
                        except Exception as rollback_error:
                            logger.error(f"🔥 롤백 실패: {rollback_error}")
                
                # 전체 작업 완료 처리
                if (not job.collect_profile or job.profile_status == "completed") and \
                   (not job.collect_reels or job.reels_status == "completed"):
                    job.status = "completed"
                    logger.info(f"✅ 전체 작업 완료: {job.username}")
                else:
                    job.status = "failed"
                    logger.error(f"❌ 일부 작업 실패: {job.username}")
                
                job.completed_at = now_kst()
                
            except Exception as e:
                logger.error(f"🔥 전체 수집 오류: {job.username} - {str(e)}")
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = now_kst()
                
                if job.collect_profile:
                    job.profile_status = "failed"
                if job.collect_reels:
                    job.reels_status = "failed"
            
            db.commit()
            
        except Exception as e:
            logger.error(f"🔥 작업 처리 중 오류: {job_id} - {str(e)}")
            # 오류 발생 시 작업 상태를 failed로 변경
            try:
                job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.completed_at = now_kst()
                    
                    # 각 타입별 상태 업데이트
                    if job.collect_profile:
                        job.profile_status = "failed"
                    # 게시물 수집은 항상 건너뛰기
                    # posts_status 필드 제거됨
                    if job.collect_reels:
                        job.reels_status = "failed"
                    
                    db.commit()
            except Exception as commit_error:
                logger.error(f"작업 상태 업데이트 실패: {str(commit_error)}")
                db.rollback()
        finally:
            db.close()
    
    async def save_collected_data(self, job: CollectionJob, result: dict, influencer_service: InfluencerService, username: str):
        """수집된 데이터를 데이터베이스에 저장"""
        try:
            # 프로필 데이터 저장
            if job.collect_profile and result.get("profile"):
                profile_data = result["profile"]
                await influencer_service.save_profile_data(profile_data, username)
                job.profile_status = "completed"
                job.profile_count = 1
                logger.info(f"💾 프로필 데이터 저장: {username}")
            elif job.collect_profile:
                job.profile_status = "failed"
                
            # 게시물 데이터 저장 - 항상 건너뛰기
            # posts_status, posts_count 필드 제거됨
                
            # 릴스 데이터 저장
            if job.collect_reels and result.get("reels"):
                reels_data = result["reels"]
                saved_reels = await influencer_service.save_reels_data(reels_data, username)
                job.reels_status = "completed"
                job.reels_count = len(saved_reels)
                logger.info(f"💾 릴스 데이터 저장: {username} - {len(saved_reels)}개")
            elif job.collect_reels:
                job.reels_status = "failed"
                
        except Exception as e:
            logger.error(f"데이터 저장 중 오류: {job.username} - {str(e)}")
            # 저장 실패 시 상태 업데이트
            if job.collect_profile:
                job.profile_status = "failed"
            # collect_posts 필드 제거됨
            if job.collect_reels:
                job.reels_status = "failed"
            raise e

# 전역 워커 인스턴스
worker_instance: Optional[CollectionWorker] = None

async def start_collection_worker():
    """워커 시작 함수"""
    global worker_instance
    if worker_instance is None:
        worker_instance = CollectionWorker()

    if worker_instance.is_active():
        return

    worker_instance.start_background()

def stop_collection_worker():
    """워커 중지 함수"""
    global worker_instance
    if worker_instance and worker_instance.is_running:
        worker_instance.stop()

def get_worker_status():
    """워커 상태 조회"""
    global worker_instance
    if worker_instance:
        return {
            "is_running": worker_instance.is_running,
            "status": "running" if worker_instance.is_running else "stopped",
            "thread_alive": worker_instance.is_active(),
        }
    return {
        "is_running": False,
        "status": "not_initialized",
        "thread_alive": False,
    }
