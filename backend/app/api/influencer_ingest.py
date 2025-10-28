from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from typing import List
import uuid

from ..models.influencer_models import (
    IngestRequest, IngestResponse, BatchIngestResponse, ProfileResult,
    PostsRequest, ImageDownloadRequest, Profile, Post
)
from ..db.models import CollectionJob
from ..services.influencer_service import InfluencerService
from ..services.brightdata_service import BrightDataService
from ..services.s3_service import S3Service
from ..services.progress_service import progress_service
from ..services.collection_worker import start_collection_worker, stop_collection_worker, get_worker_status
from ..db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

KST_OFFSET = timedelta(hours=9)


def now_kst() -> datetime:
    return datetime.utcnow() + KST_OFFSET

@router.post("/influencer/ingest/batch")
async def ingest_instagram_data_batch(
    request: IngestRequest,
    db: Session = Depends(get_db)
):
    """여러 인스타그램 계정 URL에서 프로필과 게시물 데이터를 수집 큐에 추가합니다."""
    try:
        logger.info(f"배치 인스타그램 데이터 수집 요청: {len(request.instagramUrls)}개 URL")
        
        # 수집 옵션 설정
        collect_options = request.options or {
            "collectProfile": True,
            "collectReels": True
        }
        
        # URL 검증 및 중복 제거
        valid_urls = []
        for url in request.instagramUrls:
            url = url.strip()
            if not url:
                continue
            if not (url.startswith('http://instagram.com/') or url.startswith('https://instagram.com/') or 
                   url.startswith('http://www.instagram.com/') or url.startswith('https://www.instagram.com/')):
                logger.warning(f"유효하지 않은 Instagram URL: {url}")
                continue
            valid_urls.append(url)
        
        if not valid_urls:
            return {
                "success": False,
                "message": "유효한 Instagram URL이 없습니다",
                "jobs_created": 0
            }
        
        # 각 URL에 대해 수집 작업을 큐에 추가
        created_jobs = []
        for url in valid_urls:
            job_id = str(uuid.uuid4())
            
            # username 추출 (URL 정리 후)
            clean_url = url.strip().rstrip('/')  # trailing slash 제거
            if '?' in clean_url:
                clean_url = clean_url.split('?')[0]  # query params 제거
            username = clean_url.split('/')[-1]  # 마지막 부분이 username
            
            # 큐에 작업 생성
            collection_job = CollectionJob(
                job_id=job_id,
                url=url,
                username=username,
                collect_profile=collect_options.get("collectProfile", True),
                collect_reels=collect_options.get("collectReels", True),
                status="pending",
                priority=0,
                profile_status="pending" if collect_options.get("collectProfile", True) else "skipped",
                reels_status="pending" if collect_options.get("collectReels", True) else "skipped"
            )
            
            db.add(collection_job)
            created_jobs.append(job_id)
        
        # 변경사항 커밋
        db.commit()

        logger.info(f"수집 작업 {len(created_jobs)}개가 큐에 추가되었습니다")

        # Ensure the background worker is running so queued jobs are processed
        worker_status = get_worker_status()
        if not worker_status.get("is_running"):
            logger.info("수집 워커가 비활성화 상태라서 자동으로 시작합니다")
            await start_collection_worker()

        return {
            "success": True,
            "message": f"{len(created_jobs)}개의 수집 작업이 큐에 추가되었습니다",
            "jobs_created": len(created_jobs),
            "job_ids": created_jobs
        }
    except Exception as e:
        logger.error(f"배치 수집 큐 추가 실패: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"수집 작업 추가 실패: {str(e)}",
            "jobs_created": 0
        }

@router.get("/influencer/collection-jobs")
async def get_collection_jobs(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """수집 작업 큐 상태를 조회합니다."""
    try:
        query = db.query(CollectionJob)
        
        if status:
            query = query.filter(CollectionJob.status == status)
        
        # 생성 시간 기준 내림차순 정렬
        query = query.order_by(CollectionJob.created_at.desc())
        
        # 페이지네이션
        total = query.count()
        jobs = query.offset(offset).limit(limit).all()
        
        return {
            "success": True,
            "total": total,
            "jobs": [job.to_dict() for job in jobs],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error(f"수집 작업 조회 실패: {str(e)}")
        return {
            "success": False,
            "message": f"수집 작업 조회 실패: {str(e)}",
            "jobs": []
        }

@router.get("/influencer/collection-jobs/summary")
async def get_collection_jobs_summary(db: Session = Depends(get_db)):
    """수집 작업 큐 요약 정보를 조회합니다."""
    try:
        # 상태별 카운트
        pending_count = db.query(CollectionJob).filter(CollectionJob.status == "pending").count()
        processing_count = db.query(CollectionJob).filter(CollectionJob.status == "processing").count()
        completed_count = db.query(CollectionJob).filter(CollectionJob.status == "completed").count()
        failed_count = db.query(CollectionJob).filter(CollectionJob.status == "failed").count()
        
        # 최근 24시간 내 작업들
        yesterday = now_kst() - timedelta(days=1)
        recent_jobs = db.query(CollectionJob).filter(
            CollectionJob.created_at >= yesterday
        ).count()
        
        return {
            "success": True,
            "summary": {
                "pending": pending_count,
                "processing": processing_count,
                "completed": completed_count,
                "failed": failed_count,
                "total": pending_count + processing_count + completed_count + failed_count,
                "recent_24h": recent_jobs
            }
        }
    except Exception as e:
        logger.error(f"수집 작업 요약 조회 실패: {str(e)}")
        return {
            "success": False,
            "message": f"요약 정보 조회 실패: {str(e)}",
            "summary": {}
        }

@router.delete("/influencer/collection-jobs/{job_id}")
async def delete_collection_job(job_id: str, db: Session = Depends(get_db)):
    """수집 작업을 삭제합니다 (진행 중인 작업 제외)."""
    try:
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        
        if not job:
            return {
                "success": False,
                "message": "작업을 찾을 수 없습니다"
            }
        
        if job.status == "processing":
            return {
                "success": False,
                "message": "진행 중인 작업은 삭제할 수 없습니다"
            }

        db.delete(job)
        db.commit()
        
        return {
            "success": True,
            "message": "작업이 삭제되었습니다"
        }
    except Exception as e:
        logger.error(f"수집 작업 삭제 실패: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"작업 삭제 실패: {str(e)}"
        }

@router.post("/influencer/collection-jobs/cleanup")
async def cleanup_completed_jobs(
    older_than_hours: int = 24,
    db: Session = Depends(get_db)
):
    """완료된 작업들을 정리합니다."""
    try:
        from datetime import datetime, timedelta
        
        cutoff_time = now_kst() - timedelta(hours=older_than_hours)
        
        # 완료되거나 실패한 작업 중 지정된 시간보다 오래된 것들 삭제
        deleted_count = db.query(CollectionJob).filter(
            CollectionJob.status.in_(["completed", "failed"]),
            CollectionJob.completed_at < cutoff_time
        ).delete()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"{deleted_count}개의 작업이 정리되었습니다",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"작업 정리 실패: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"작업 정리 실패: {str(e)}",
            "deleted_count": 0
        }

@router.post("/influencer/worker/start")
async def start_worker():
    """수집 워커를 시작합니다."""
    try:
        status = get_worker_status()
        if status["is_running"]:
            return {
                "success": False,
                "message": "워커가 이미 실행 중입니다",
                "status": status
            }
        
        # 워커 시작 (별도 스레드에서 실행되므로 즉시 반환)
        await start_collection_worker()
        
        return {
            "success": True,
            "message": "수집 워커가 시작되었습니다",
            "status": get_worker_status()
        }
    except Exception as e:
        logger.error(f"워커 시작 실패: {str(e)}")
        return {
            "success": False,
            "message": f"워커 시작 실패: {str(e)}"
        }

@router.post("/influencer/worker/stop")
async def stop_worker():
    """수집 워커를 중지합니다."""
    try:
        stop_collection_worker()
        return {
            "success": True,
            "message": "수집 워커가 중지되었습니다",
            "status": get_worker_status()
        }
    except Exception as e:
        logger.error(f"워커 중지 실패: {str(e)}")
        return {
            "success": False,
            "message": f"워커 중지 실패: {str(e)}"
        }

@router.post("/influencer/collection-jobs/stop-processing")
async def stop_processing_jobs(db: Session = Depends(get_db)):
    """진행 중인 수집 작업들을 중지합니다."""
    try:
        # 처리 중인 작업들을 조회
        processing_jobs = db.query(CollectionJob).filter(
            CollectionJob.status == "processing"
        ).all()
        
        stopped_count = 0
        for job in processing_jobs:
            job.status = "cancelled"
            job.error_message = "사용자에 의해 중지됨"
            job.completed_at = now_kst()
            
            # 개별 상태도 중지로 변경
            if job.collect_profile and job.profile_status == "pending":
                job.profile_status = "cancelled"
            if job.collect_reels and job.reels_status == "pending":
                job.reels_status = "cancelled"
            
            stopped_count += 1
        
        db.commit()
        
        logger.info(f"진행 중인 {stopped_count}개 작업이 중지되었습니다")
        
        return {
            "success": True,
            "message": f"{stopped_count}개의 진행 중인 작업이 중지되었습니다",
            "stopped_count": stopped_count
        }
        
    except Exception as e:
        logger.error(f"진행 중인 작업 중지 실패: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"작업 중지 실패: {str(e)}"
        }

@router.post("/influencer/collection-jobs/stop-all")
async def stop_all_jobs(db: Session = Depends(get_db)):
    """워커 중지 + 진행 중인 작업 모두 중지"""
    try:
        # 1. 워커 중지
        stop_collection_worker()
        
        # 2. 처리 중인 작업들 중지
        processing_jobs = db.query(CollectionJob).filter(
            CollectionJob.status == "processing"
        ).all()
        
        # 3. 대기 중인 작업들도 중지
        pending_jobs = db.query(CollectionJob).filter(
            CollectionJob.status == "pending"
        ).all()
        
        stopped_count = 0
        
        # 처리 중인 작업들 중지
        for job in processing_jobs:
            job.status = "cancelled"
            job.error_message = "사용자에 의해 중지됨"
            job.completed_at = now_kst()
            
            # 개별 상태도 중지로 변경
            if job.collect_profile and job.profile_status in ["pending", "processing"]:
                job.profile_status = "cancelled"
            if job.collect_reels and job.reels_status in ["pending", "processing"]:
                job.reels_status = "cancelled"
            
            stopped_count += 1
        
        # 대기 중인 작업들 중지
        for job in pending_jobs:
            job.status = "cancelled"
            job.error_message = "사용자에 의해 중지됨"
            job.completed_at = now_kst()
            
            # 개별 상태도 중지로 변경
            if job.collect_profile and job.profile_status == "pending":
                job.profile_status = "cancelled"
            if job.collect_reels and job.reels_status == "pending":
                job.reels_status = "cancelled"
            
            stopped_count += 1
        
        db.commit()
        
        logger.info(f"워커 중지 및 {stopped_count}개 작업이 중지되었습니다")
        
        return {
            "success": True,
            "message": f"워커가 중지되고 {stopped_count}개 작업이 중지되었습니다",
            "stopped_count": stopped_count,
            "worker_status": get_worker_status()
        }
        
    except Exception as e:
        logger.error(f"전체 중지 실패: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"전체 중지 실패: {str(e)}"
        }

@router.post("/influencer/collection-jobs/retry")
async def retry_failed_jobs(
    job_ids: List[str],
    db: Session = Depends(get_db)
):
    """실패한 작업들을 재실행합니다."""
    try:
        if not job_ids:
            return {
                "success": False,
                "message": "재실행할 작업 ID가 없습니다",
                "retried_count": 0
            }
        
        # 실패한 작업들을 조회
        failed_jobs = db.query(CollectionJob).filter(
            CollectionJob.job_id.in_(job_ids),
            CollectionJob.status == "failed"
        ).all()
        
        if not failed_jobs:
            return {
                "success": False,
                "message": "재실행할 수 있는 실패한 작업이 없습니다",
                "retried_count": 0
            }
        
        # 작업들을 다시 pending 상태로 변경
        retried_count = 0
        for job in failed_jobs:
            job.status = "pending"
            job.started_at = None
            job.completed_at = None
            job.error_message = None
            
            # 개별 상태들도 재설정
            if job.collect_profile:
                job.profile_status = "pending"
            if job.collect_reels:
                job.reels_status = "pending"
            
            retried_count += 1
        
        db.commit()
        
        # 워커가 실행 중이 아니면 시작
        worker_status = get_worker_status()
        if not worker_status.get("is_running"):
            logger.info("재실행을 위해 수집 워커를 자동으로 시작합니다")
            await start_collection_worker()
        
        logger.info(f"{retried_count}개의 실패한 작업이 재실행을 위해 큐에 추가되었습니다")
        
        return {
            "success": True,
            "message": f"{retried_count}개의 작업이 재실행을 위해 큐에 추가되었습니다",
            "retried_count": retried_count
        }
        
    except Exception as e:
        logger.error(f"작업 재실행 실패: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"작업 재실행 실패: {str(e)}",
            "retried_count": 0
        }

@router.get("/influencer/worker/status")
async def get_worker_status_api():
    """수집 워커 상태를 조회합니다."""
    try:
        return {
            "success": True,
            "status": get_worker_status()
        }
    except Exception as e:
        logger.error(f"워커 상태 조회 실패: {str(e)}")
        return {
            "success": False,
            "message": f"워커 상태 조회 실패: {str(e)}"
        }

# 기존 코드는 향후 레거시로 유지하되 사용하지 않음
