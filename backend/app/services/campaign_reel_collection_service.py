import os
import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import CampaignReelCollectionJob, CollectionJob
from app.db.database import SessionLocal
import uuid
import logging

logger = logging.getLogger(__name__)

class CampaignReelCollectionService:
    def __init__(self):
        self.api_token = os.getenv("BRIGHTDATA_API_KEY")
        self.dataset_id = "gd_lyclm20il4r5helnj"  # instagram_reels_by_url.py에서 확인한 dataset_id
        self.api_url = "https://api.brightdata.com/datasets/v3/trigger"
        
    def add_reel_collection_jobs(self, campaign_id: int, reel_urls: List[str], check_existing_data: bool = False) -> List[CampaignReelCollectionJob]:
        """캠페인의 릴스 URL들을 수집 큐에 추가"""
        db = SessionLocal()
        try:
            jobs = []
            for url in reel_urls:
                # 이미 수집 완료된 데이터가 있는지 확인 (옵션)
                if check_existing_data:
                    existing_completed_job = db.query(CampaignReelCollectionJob).filter(
                        and_(
                            CampaignReelCollectionJob.campaign_id == campaign_id,
                            CampaignReelCollectionJob.reel_url == url,
                            CampaignReelCollectionJob.status == "completed",
                            CampaignReelCollectionJob.user_posted.isnot(None)
                        )
                    ).first()
                    
                    if existing_completed_job:
                        logger.info(f"Reel data already exists for {url}, skipping")
                        continue
                
                # 이미 대기 중이거나 처리 중인 작업인지 확인
                existing_job = db.query(CampaignReelCollectionJob).filter(
                    and_(
                        CampaignReelCollectionJob.campaign_id == campaign_id,
                        CampaignReelCollectionJob.reel_url == url,
                        CampaignReelCollectionJob.status.in_(["pending", "processing"])
                    )
                ).first()
                
                if not existing_job:
                    job = CampaignReelCollectionJob(
                        campaign_id=campaign_id,
                        reel_url=url,
                        status="pending",
                        priority=1
                    )
                    db.add(job)
                    jobs.append(job)
            
            db.commit()
            logger.info(f"Added {len(jobs)} reel collection jobs for campaign {campaign_id}")
            return jobs
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding reel collection jobs: {str(e)}")
            raise
        finally:
            db.close()
    
    def collect_single_reel(self, reel_url: str) -> Dict:
        """단일 릴스 정보 수집"""
        if not self.api_token:
            raise ValueError("BRIGHTDATA_API_KEY not found in environment variables")
            
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        params = {
            "dataset_id": self.dataset_id,
            "include_errors": "true",
        }
        
        data = [{"url": reel_url}]
        
        try:
            logger.info(f"Calling BrightData API for {reel_url} with dataset_id: {self.dataset_id}")
            response = requests.post(self.api_url, headers=headers, params=params, json=data, timeout=30)
            
            logger.info(f"BrightData API response status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"BrightData API response for {reel_url}: {result}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling BrightData API for {reel_url}: {str(e)}")
            raise
    
    def process_brightdata_response(self, job_id: int, brightdata_response: Dict) -> bool:
        """BrightData 응답을 처리하여 데이터베이스 업데이트"""
        db = SessionLocal()
        try:
            job = db.query(CampaignReelCollectionJob).filter(
                CampaignReelCollectionJob.id == job_id
            ).first()
            
            if not job:
                logger.error(f"Job {job_id} not found")
                return False
            
            # BrightData 응답에서 snapshot_id 추출
            snapshot_id = brightdata_response.get("snapshot_id")
            logger.info(f"BrightData response for job {job_id}: {brightdata_response}")
            
            if not snapshot_id:
                job.status = "failed"
                job.error_message = f"No snapshot_id in BrightData response: {brightdata_response}"
                job.completed_at = datetime.utcnow()
                db.commit()
                return False
            
            job.brightdata_job_id = snapshot_id
            job.status = "processing"
            job.started_at = datetime.utcnow()
            db.commit()
            
            # 스냅샷 결과 대기 및 처리
            return self._wait_and_process_snapshot(job_id, snapshot_id)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing BrightData response for job {job_id}: {str(e)}")
            return False
        finally:
            db.close()
    
    def _wait_and_process_snapshot(self, job_id: int, snapshot_id: str, max_wait_time: int = 180) -> bool:
        """스냅샷 완료를 대기하고 결과 처리 - 간단하고 빠른 버전"""
        start_time = time.time()
        
        # BrightData에서 스냅샷이 완료되었다고 하니, 먼저 바로 데이터 다운로드 시도
        logger.info(f"Attempting immediate data download for snapshot {snapshot_id}")
        try:
            if self._fetch_and_save_reel_data(job_id, snapshot_id):
                logger.info(f"✅ Immediate data download successful for {snapshot_id}")
                return True
        except Exception as e:
            logger.info(f"Immediate download failed, falling back to status check: {str(e)}")
        
        # 즉시 다운로드가 실패하면 상태 확인 후 재시도
        wait_intervals = [10, 15, 20, 30]  # 점진적으로 대기 시간 증가
        attempt = 0
        
        while time.time() - start_time < max_wait_time:
            try:
                attempt += 1
                wait_time = wait_intervals[min(attempt-1, len(wait_intervals)-1)]
                
                logger.info(f"⏳ Attempt {attempt}: Checking snapshot {snapshot_id} status")
                
                # 간단한 상태 확인 - HTTP 200이면 바로 다운로드 시도
                response_code = self._simple_snapshot_check(snapshot_id)
                
                if response_code == 200:
                    logger.info(f"📡 Snapshot {snapshot_id} returned 200, attempting download")
                    if self._fetch_and_save_reel_data(job_id, snapshot_id):
                        return True
                elif response_code == 202:
                    logger.info(f"⏳ Snapshot {snapshot_id} still processing (202), waiting {wait_time}s")
                elif response_code == 404:
                    logger.error(f"❌ Snapshot {snapshot_id} not found (404)")
                    self._mark_job_failed(job_id, f"Snapshot not found: {snapshot_id}")
                    return False
                else:
                    logger.warning(f"⚠️ Unexpected response code {response_code} for {snapshot_id}")
                
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"❌ Error checking snapshot {snapshot_id}: {str(e)}")
                time.sleep(10)
        
        # 타임아웃
        logger.error(f"⏰ Timeout waiting for snapshot {snapshot_id} after {max_wait_time}s")
        self._mark_job_failed(job_id, f"Timeout waiting for BrightData snapshot after {max_wait_time}s")
        return False
    
    def _simple_snapshot_check(self, snapshot_id: str) -> int:
        """간단한 스냅샷 상태 확인 - HTTP 상태 코드만 반환"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }
        
        status_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
        
        try:
            response = requests.get(status_url, headers=headers, timeout=15)
            return response.status_code
        except requests.exceptions.RequestException:
            return 500  # 네트워크 오류 등
    
    def _get_snapshot_status(self, snapshot_id: str) -> str:
        """스냅샷 상태 확인 - 새로운 BrightData API 응답 구조 대응"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }
        
        status_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
        
        try:
            logger.info(f"Checking snapshot status: {status_url}")
            response = requests.get(status_url, headers=headers, timeout=30)
            
            logger.info(f"Status check response code: {response.status_code}")
            logger.info(f"Status check response text: {response.text[:500]}")
            
            # 200: 데이터 준비됨 (직접 다운로드 가능)
            if response.status_code == 200:
                try:
                    # JSON 응답인 경우 파싱 시도
                    status_data = response.json()
                    logger.info(f"Snapshot {snapshot_id} JSON response: {status_data}")
                    
                    # 응답에 데이터가 있으면 완료로 판단
                    if isinstance(status_data, list) and len(status_data) > 0:
                        logger.info(f"Snapshot {snapshot_id} has data, marking as ready")
                        return "ready"
                    elif isinstance(status_data, dict):
                        # 상태 필드가 있으면 확인
                        status = status_data.get("status", "unknown")
                        if status in ["ready", "done", "completed"]:
                            return "ready"
                        elif status in ["running", "pending", "processing"]:
                            return "running"
                        elif status in ["failed", "error"]:
                            return "failed"
                        else:
                            # 상태 필드가 없거나 알 수 없는 경우, 다른 필드로 판단
                            if "file_urls" in status_data or "data" in status_data:
                                return "ready"
                            else:
                                return "unknown"
                    else:
                        return "unknown"
                        
                except ValueError:
                    # JSON이 아닌 경우 (예: CSV, 텍스트 데이터)
                    if len(response.text.strip()) > 0:
                        logger.info(f"Snapshot {snapshot_id} has non-JSON data, marking as ready")
                        return "ready"
                    else:
                        return "unknown"
            
            # 202: 처리 중
            elif response.status_code == 202:
                logger.info(f"Snapshot {snapshot_id} still processing")
                return "running"
            
            # 404: 스냅샷 찾을 수 없음
            elif response.status_code == 404:
                logger.error(f"Snapshot {snapshot_id} not found")
                return "failed"
            
            # 기타 오류 상태
            else:
                logger.warning(f"Snapshot status check returned {response.status_code}: {response.text[:200]}")
                # 401, 403 등 인증 오류는 실패로 처리
                if response.status_code in [401, 403]:
                    return "failed"
                else:
                    return "unknown"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking snapshot status for {snapshot_id}: {str(e)}")
            return "unknown"
    
    def _fetch_and_save_reel_data(self, job_id: int, snapshot_id: str) -> bool:
        """스냅샷에서 릴스 데이터를 가져와서 저장"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }
        
        # 스냅샷이 ready 상태일 때만 데이터 다운로드
        data_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"
        
        try:
            logger.info(f"Downloading data from {data_url}")
            response = requests.get(data_url, headers=headers, timeout=60)
            
            logger.info(f"Data download response code: {response.status_code}")
            logger.info(f"Data download response text preview: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"Successfully parsed JSON data for snapshot {snapshot_id}: {len(data) if isinstance(data, list) else 1} records")
                except ValueError as e:
                    logger.error(f"Failed to parse JSON response for {snapshot_id}: {str(e)}")
                    logger.info(f"Raw response content: {response.text[:1000]}")
                    return False
            else:
                logger.error(f"Data download failed for {snapshot_id}: {response.status_code} - {response.text[:200]}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading snapshot data for {snapshot_id}: {str(e)}")
            return False
        
        db = SessionLocal()
        try:
            job = db.query(CampaignReelCollectionJob).filter(
                CampaignReelCollectionJob.id == job_id
            ).first()
            
            if not job:
                logger.error(f"Job {job_id} not found")
                return False
            
            # 데이터에서 user_posted와 video_play_count 추출 - 인플루언서 서비스 방식 적용
            if data and len(data) > 0:
                reel_data = data[0]  # 첫 번째 결과 사용
                
                logger.info(f"📊 Raw reel data keys: {list(reel_data.keys()) if isinstance(reel_data, dict) else 'Not a dict'}")
                logger.info(f"📊 Raw reel data sample: {str(reel_data)[:300]}...")
                
                # 인플루언서 서비스 방식으로 견고한 데이터 추출
                user_posted = self._extract_user_posted(reel_data)
                video_play_count = self._extract_video_play_count(reel_data)
                thumbnail_url = self._extract_thumbnail_url(reel_data)
                
                # 썸네일 이미지를 S3에 업로드
                s3_thumbnail_url = None
                if thumbnail_url:
                    s3_thumbnail_url = self._upload_thumbnail_to_s3_sync(thumbnail_url, user_posted, job_id)
                
                job.user_posted = user_posted
                job.video_play_count = video_play_count
                job.thumbnail_url = thumbnail_url
                job.s3_thumbnail_url = s3_thumbnail_url
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.job_metadata = reel_data  # 전체 데이터 저장
                
                logger.info(f"✅ Successfully collected reel data for job {job_id}: user={job.user_posted}, views={job.video_play_count}")
                
                # 인플루언서 프로필 수집 큐에 추가
                if job.user_posted:
                    self._add_influencer_collection_job(job.user_posted)
                
            else:
                job.status = "failed"
                job.error_message = "No data returned from BrightData"
                job.completed_at = datetime.utcnow()
            
            db.commit()
            return job.status == "completed"
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving reel data for job {job_id}: {str(e)}")
            return False
        finally:
            db.close()
    
    def _extract_user_posted(self, reel_data: dict) -> str:
        """인플루언서 서비스 방식으로 사용자명 추출"""
        # 여러 가능한 필드명 시도
        possible_fields = [
            "user_posted", "username", "user", "account", 
            "profile_name", "user_name", "posted_by"
        ]
        
        for field in possible_fields:
            value = reel_data.get(field)
            if value and isinstance(value, str) and value.strip():
                logger.info(f"📋 Found username in field '{field}': {value}")
                return value.strip()
        
        logger.warning(f"⚠️ No username found in reel data. Available fields: {list(reel_data.keys())}")
        return None
    
    def _extract_video_play_count(self, reel_data: dict) -> int:
        """인플루언서 서비스 방식으로 재생 수 추출"""
        # 여러 가능한 필드명 시도
        possible_fields = [
            "video_play_count", "views", "view_count", "play_count", 
            "video_views", "total_views", "playback_count"
        ]
        
        for field in possible_fields:
            value = reel_data.get(field)
            if value is not None:
                # dict 형태인 경우 count 키 확인
                if isinstance(value, dict) and "count" in value:
                    value = value["count"]
                
                # 숫자로 변환 시도
                try:
                    count = int(value)
                    logger.info(f"📋 Found view count in field '{field}': {count}")
                    return count
                except (TypeError, ValueError):
                    logger.warning(f"⚠️ Invalid view count value in field '{field}': {value}")
                    continue
        
        logger.warning(f"⚠️ No valid view count found in reel data. Available fields: {list(reel_data.keys())}")
        return 0
    
    def _add_influencer_collection_job(self, username: str):
        """인플루언서 프로필 수집 작업을 큐에 추가"""
        db = SessionLocal()
        try:
            # 이미 수집 작업이 있는지 확인
            existing_job = db.query(CollectionJob).filter(
                and_(
                    CollectionJob.username == username,
                    CollectionJob.status.in_(["pending", "processing"])
                )
            ).first()
            
            if not existing_job:
                profile_url = f"https://www.instagram.com/{username}"
                collection_job = CollectionJob(
                    job_id=str(uuid.uuid4()),
                    url=profile_url,
                    username=username,
                    collect_profile=True,
                    collect_posts=False,  # 게시물 수집 비활성화
                    collect_reels=True,
                    status="pending",
                    priority=1,
                    job_metadata={"source": "campaign_reel_collection"}
                )
                
                db.add(collection_job)
                db.commit()
                
                logger.info(f"Added influencer collection job for {username}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding influencer collection job for {username}: {str(e)}")
        finally:
            db.close()
    
    def _mark_job_failed(self, job_id: int, error_message: str):
        """작업을 실패로 표시"""
        db = SessionLocal()
        try:
            job = db.query(CampaignReelCollectionJob).filter(
                CampaignReelCollectionJob.id == job_id
            ).first()
            
            if job:
                job.status = "failed"
                job.error_message = error_message
                job.completed_at = datetime.utcnow()
                db.commit()
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error marking job {job_id} as failed: {str(e)}")
        finally:
            db.close()
    
    def process_pending_jobs(self, limit: int = 5, campaign_id: int = None) -> int:
        """대기 중인 작업들을 처리"""
        db = SessionLocal()
        try:
            query = db.query(CampaignReelCollectionJob).filter(
                CampaignReelCollectionJob.status == "pending"
            )
            
            # 특정 캠페인 ID가 지정된 경우 필터링
            if campaign_id is not None:
                query = query.filter(CampaignReelCollectionJob.campaign_id == campaign_id)
            
            pending_jobs = query.order_by(
                CampaignReelCollectionJob.priority.desc(),
                CampaignReelCollectionJob.created_at.asc()
            ).limit(limit).all()
            
            processed_count = 0
            for job in pending_jobs:
                try:
                    logger.info(f"Processing reel collection job {job.id} for URL: {job.reel_url}")
                    
                    # BrightData API 호출
                    brightdata_response = self.collect_single_reel(job.reel_url)
                    
                    # 응답 처리
                    if self.process_brightdata_response(job.id, brightdata_response):
                        processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing job {job.id}: {str(e)}")
                    self._mark_job_failed(job.id, str(e))
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing pending jobs: {str(e)}")
            return 0
        finally:
            db.close()
    
    def retry_failed_jobs(self, campaign_id: int = None, limit: int = 5) -> int:
        """실패한 작업들을 재시도"""
        db = SessionLocal()
        try:
            query = db.query(CampaignReelCollectionJob).filter(
                CampaignReelCollectionJob.status == "failed"
            )
            
            if campaign_id:
                query = query.filter(CampaignReelCollectionJob.campaign_id == campaign_id)
            
            failed_jobs = query.order_by(
                CampaignReelCollectionJob.priority.desc(),
                CampaignReelCollectionJob.created_at.asc()
            ).limit(limit).all()
            
            retried_count = 0
            for job in failed_jobs:
                try:
                    # 상태를 pending으로 초기화
                    job.status = "pending"
                    job.error_message = None
                    job.brightdata_job_id = None
                    job.started_at = None
                    job.completed_at = None
                    
                    retried_count += 1
                    logger.info(f"Retrying failed job {job.id} for URL: {job.reel_url}")
                    
                except Exception as e:
                    logger.error(f"Error retrying job {job.id}: {str(e)}")
                    continue
            
            db.commit()
            
            # 재시도 후 자동으로 처리 시작
            if retried_count > 0:
                logger.info(f"Starting automatic processing of {retried_count} retried jobs")
                try:
                    # 재시도된 작업들 즉시 처리
                    processed_count = self.process_pending_jobs(limit=retried_count, campaign_id=campaign_id)
                    logger.info(f"Automatically processed {processed_count} retried jobs")
                except Exception as e:
                    logger.error(f"Error in automatic processing after retry: {str(e)}")
            
            return retried_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error retrying failed jobs: {str(e)}")
            return 0
        finally:
            db.close()
    
    def get_campaign_collection_status(self, campaign_id: int) -> Dict:
        """캠페인의 수집 현황 조회"""
        db = SessionLocal()
        try:
            jobs = db.query(CampaignReelCollectionJob).filter(
                CampaignReelCollectionJob.campaign_id == campaign_id
            ).all()
            
            status_counts = {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            }
            
            for job in jobs:
                status_counts[job.status] += 1
            
            return {
                "campaign_id": campaign_id,
                "total_jobs": len(jobs),
                "status_counts": status_counts,
                "jobs": [job.to_dict() for job in jobs]
            }
            
        except Exception as e:
            logger.error(f"Error getting campaign collection status: {str(e)}")
            return {}
        finally:
            db.close()
    
    def get_all_campaigns_collection_status(self) -> List[Dict]:
        """모든 캠페인의 수집 현황 조회"""
        db = SessionLocal()
        try:
            # 캠페인별로 그룹화하여 현황 조회
            campaigns = db.query(CampaignReelCollectionJob.campaign_id).distinct().all()
            
            results = []
            for (campaign_id,) in campaigns:
                status = self.get_campaign_collection_status(campaign_id)
                if status:
                    results.append(status)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting all campaigns collection status: {str(e)}")
            return []
        finally:
            db.close()
    
    def cancel_processing_jobs(self, campaign_id: int = None) -> int:
        """현재 처리 중인 작업들을 취소"""
        db = SessionLocal()
        try:
            query = db.query(CampaignReelCollectionJob).filter(
                CampaignReelCollectionJob.status == "processing"
            )
            
            if campaign_id:
                query = query.filter(CampaignReelCollectionJob.campaign_id == campaign_id)
            
            processing_jobs = query.all()
            
            cancelled_count = 0
            for job in processing_jobs:
                try:
                    # 처리 중인 작업을 취소된 상태로 변경
                    job.status = "failed"
                    job.error_message = "Job cancelled by user"
                    job.completed_at = datetime.utcnow()
                    
                    cancelled_count += 1
                    logger.info(f"Cancelled processing job {job.id} for URL: {job.reel_url}")
                    
                except Exception as e:
                    logger.error(f"Error cancelling job {job.id}: {str(e)}")
                    continue
            
            db.commit()
            logger.info(f"Successfully cancelled {cancelled_count} processing jobs")
            return cancelled_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelling processing jobs: {str(e)}")
            return 0
        finally:
            db.close()
    
    def _extract_thumbnail_url(self, reel_data: dict) -> str:
        """릴스 데이터에서 썸네일 URL 추출"""
        # 여러 가능한 필드명 시도
        possible_fields = [
            "thumbnail", "thumbnail_url", "cover_image", "cover_url",
            "media_thumbnail", "preview_image", "poster", "snapshot"
        ]
        
        for field in possible_fields:
            value = reel_data.get(field)
            if value and isinstance(value, str) and value.startswith("http"):
                logger.info(f"📋 Found thumbnail URL in field '{field}': {value}")
                return value
        
        logger.warning(f"⚠️ No valid thumbnail URL found in reel data. Available fields: {list(reel_data.keys())}")
        return None
    
    def _upload_thumbnail_to_s3_sync(self, thumbnail_url: str, username: str, job_id: int) -> str:
        """썸네일 이미지를 S3에 업로드하고 URL 반환 (동기 버전)"""
        try:
            import requests
            import boto3
            import uuid
            from app.core.config import settings
            
            # 이미지 다운로드
            response = requests.get(thumbnail_url, timeout=30)
            if response.status_code != 200:
                logger.error(f"❌ Failed to download thumbnail: HTTP {response.status_code}")
                return None
            
            # S3 클라이언트 초기화
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
                region_name=settings.s3_region
            )
            
            # 파일 확장자 추출
            file_extension = thumbnail_url.split('.')[-1].split('?')[0]
            if file_extension not in ['jpg', 'jpeg', 'png', 'gif']:
                file_extension = 'jpg'
            
            # S3 키 생성
            filename = f"{uuid.uuid4().hex}.{file_extension}"
            s3_key = f"goodwave/instagram/reel/{username}/{filename}"
            
            # S3에 업로드
            s3_client.put_object(
                Bucket=settings.s3_bucket,
                Key=s3_key,
                Body=response.content,
                ContentType=f'image/{file_extension}',
                ACL='public-read'
            )
            
            # 공개 URL 생성
            s3_url = f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{s3_key}"
            logger.info(f"✅ Thumbnail uploaded to S3: {s3_url}")
            return s3_url
                        
        except Exception as e:
            logger.error(f"❌ Error uploading thumbnail to S3: {str(e)}")
            return None