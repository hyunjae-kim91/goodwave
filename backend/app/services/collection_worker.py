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
        self.brightdata_service = BrightDataService()
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
                if job.collect_posts:
                    job.posts_status = "pending"
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
        """대기 중인 작업들을 처리"""
        db = self.Session()
        try:
            # 우선순위 순으로 대기 중인 작업 조회 (최대 3개까지 동시 처리)
            pending_jobs = db.query(CollectionJob).filter(
                CollectionJob.status == "pending"
            ).order_by(
                CollectionJob.priority.desc(),
                CollectionJob.created_at.asc()
            ).limit(3).all()
            
            if not pending_jobs:
                return
            
            logger.info(f"📋 처리할 작업 {len(pending_jobs)}개 발견")
            
            # 각 작업을 동시에 처리
            tasks = [self.process_single_job(job.job_id) for job in pending_jobs]
            await asyncio.gather(*tasks, return_exceptions=True)
            
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
            
            # 수집 옵션 설정
            collect_options = {
                "collectProfile": job.collect_profile,
                "collectPosts": job.collect_posts,
                "collectReels": job.collect_reels
            }
            
            # BrightData를 통한 데이터 수집
            result = await self.brightdata_service._collect_profile_with_brightdata(
                job.url, job.username, collect_options
            )
            
            if not result or result.get("status") == "error":
                # 수집 실패
                job.status = "failed"
                job.error_message = result.get("error", "알 수 없는 오류") if result else "데이터 수집 실패"
                job.completed_at = now_kst()
                
                # 각 타입별 상태 업데이트
                if job.collect_profile:
                    job.profile_status = "failed"
                if job.collect_posts:
                    job.posts_status = "failed"
                if job.collect_reels:
                    job.reels_status = "failed"
                    
                logger.error(f"❌ 작업 실패: {job.username} - {job.error_message}")
            else:
                # 수집 성공 - 데이터 저장
                await self.save_collected_data(job, result, influencer_service)
                
                job.status = "completed"
                job.completed_at = now_kst()
                
                logger.info(f"✅ 작업 완료: {job.username}")
            
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
                    if job.collect_posts:
                        job.posts_status = "failed"
                    if job.collect_reels:
                        job.reels_status = "failed"
                    
                    db.commit()
            except Exception as commit_error:
                logger.error(f"작업 상태 업데이트 실패: {str(commit_error)}")
                db.rollback()
        finally:
            db.close()
    
    async def save_collected_data(self, job: CollectionJob, result: dict, influencer_service: InfluencerService):
        """수집된 데이터를 데이터베이스에 저장"""
        try:
            # 프로필 데이터 저장
            if job.collect_profile and result.get("profile"):
                profile_data = result["profile"]
                await influencer_service.save_profile_data(profile_data)
                job.profile_status = "completed"
                job.profile_count = 1
                logger.info(f"💾 프로필 데이터 저장: {job.username}")
            elif job.collect_profile:
                job.profile_status = "failed"
                
            # 게시물 데이터 저장
            if job.collect_posts and result.get("posts"):
                posts_data = result["posts"]
                saved_posts = await influencer_service.save_posts_data(posts_data, job.username)
                job.posts_status = "completed"
                job.posts_count = len(saved_posts)
                logger.info(f"💾 게시물 데이터 저장: {job.username} - {len(saved_posts)}개")
            elif job.collect_posts:
                job.posts_status = "failed"
                
            # 릴스 데이터 저장
            if job.collect_reels and result.get("reels"):
                reels_data = result["reels"]
                saved_reels = await influencer_service.save_reels_data(reels_data, job.username)
                job.reels_status = "completed"
                job.reels_count = len(saved_reels)
                logger.info(f"💾 릴스 데이터 저장: {job.username} - {len(saved_reels)}개")
            elif job.collect_reels:
                job.reels_status = "failed"
                
        except Exception as e:
            logger.error(f"데이터 저장 중 오류: {job.username} - {str(e)}")
            # 저장 실패 시 상태 업데이트
            if job.collect_profile:
                job.profile_status = "failed"
            if job.collect_posts:
                job.posts_status = "failed"
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
