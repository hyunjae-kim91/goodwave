from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.services.campaign_reel_collection_service import CampaignReelCollectionService
from app.services.collection_worker import stop_collection_worker, get_worker_status

router = APIRouter()

@router.get("/dashboard")
async def get_admin_dashboard(db: Session = Depends(get_db)):
    """관리자 대시보드 데이터"""
    try:
        # 전체 통계
        total_campaigns = db.query(models.Campaign).count()
        
        # 캠페인 타입별 개수 계산
        instagram_post_campaigns = db.query(models.Campaign).filter(
            models.Campaign.campaign_type.in_(['instagram_post', 'all'])
        ).count()
        
        instagram_reel_campaigns = db.query(models.Campaign).filter(
            models.Campaign.campaign_type.in_(['instagram_reel', 'all'])
        ).count()
        
        blog_campaigns = db.query(models.Campaign).filter(
            models.Campaign.campaign_type.in_(['blog', 'all'])
        ).count()
        
        # 활성 캠페인 수
        active_campaigns = db.query(models.CollectionSchedule).filter(
            models.CollectionSchedule.is_active == True
        ).count()
        
        # 캠페인 정보
        campaigns = db.query(models.Campaign).order_by(
            models.Campaign.created_at.desc()
        ).all()
        
        return {
            'statistics': {
                'total_campaigns': total_campaigns,
                'active_campaigns': active_campaigns,
                'total_instagram_posts': instagram_post_campaigns,
                'total_instagram_reels': instagram_reel_campaigns,
                'total_blog_posts': blog_campaigns
            },
            'campaigns': [
                {
                    'id': campaign.id,
                    'name': campaign.name,
                    'product': campaign.product,
                    'campaign_type': campaign.campaign_type,
                    'budget': campaign.budget,
                    'start_date': campaign.start_date,
                    'end_date': campaign.end_date,
                    'created_at': campaign.created_at
                }
                for campaign in campaigns
            ]
        }
        
    except Exception as e:
        print(f"Error getting admin dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/collection-schedules")
async def get_collection_schedules(db: Session = Depends(get_db)):
    """정기 수집 스케줄 조회"""
    schedules = db.query(models.CollectionSchedule).all()
    return [
        {
            'id': schedule.id,
            'campaign_id': schedule.campaign_id,
            'channel': schedule.channel,
            'campaign_url': schedule.campaign_url,
            'start_date': schedule.start_date,
            'end_date': schedule.end_date,
            'is_active': schedule.is_active,
            'campaign_name': schedule.campaign.name if schedule.campaign else None
        }
        for schedule in schedules
    ]

@router.put("/collection-schedules/{schedule_id}/toggle")
async def toggle_collection_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """정기 수집 스케줄 활성화/비활성화"""
    schedule = db.query(models.CollectionSchedule).filter(
        models.CollectionSchedule.id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule.is_active = not schedule.is_active
    db.commit()
    
    return {
        "message": f"Schedule {'activated' if schedule.is_active else 'deactivated'}",
        "is_active": schedule.is_active
    }

@router.get("/campaign-collection-status")
async def get_campaign_collection_status(db: Session = Depends(get_db)):
    """캠페인 수집 진행 현황 조회"""
    try:
        collection_service = CampaignReelCollectionService()
        
        # 모든 캠페인의 수집 현황
        all_status = collection_service.get_all_campaigns_collection_status()
        
        # 캠페인 정보 추가
        for status in all_status:
            campaign = db.query(models.Campaign).filter(
                models.Campaign.id == status["campaign_id"]
            ).first()
            
            if campaign:
                status["campaign_name"] = campaign.name
                status["campaign_type"] = campaign.campaign_type
                status["product"] = campaign.product
        
        return {
            "campaigns": all_status,
            "summary": {
                "total_campaigns": len(all_status),
                "total_jobs": sum(status["total_jobs"] for status in all_status),
                "completed_jobs": sum(status["status_counts"]["completed"] for status in all_status),
                "failed_jobs": sum(status["status_counts"]["failed"] for status in all_status),
                "pending_jobs": sum(status["status_counts"]["pending"] for status in all_status),
                "processing_jobs": sum(status["status_counts"]["processing"] for status in all_status)
            }
        }
        
    except Exception as e:
        print(f"Error getting campaign collection status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/campaign-collection-status/{campaign_id}")
async def get_single_campaign_collection_status(campaign_id: int, db: Session = Depends(get_db)):
    """특정 캠페인의 수집 진행 현황 조회"""
    try:
        # 캠페인 존재 확인
        campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        collection_service = CampaignReelCollectionService()
        status = collection_service.get_campaign_collection_status(campaign_id)
        
        if status:
            status["campaign_name"] = campaign.name
            status["campaign_type"] = campaign.campaign_type
            status["product"] = campaign.product
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting campaign collection status for {campaign_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/process-reel-collection-jobs")
async def process_reel_collection_jobs():
    """대기 중인 릴스 수집 작업들을 처리"""
    try:
        collection_service = CampaignReelCollectionService()
        processed_count = collection_service.process_pending_jobs(limit=5)
        
        return {
            "message": f"Processed {processed_count} reel collection jobs",
            "processed_count": processed_count
        }
        
    except Exception as e:
        print(f"Error processing reel collection jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/retry-failed-reel-jobs")
async def retry_failed_reel_jobs(campaign_id: int = None):
    """실패한 릴스 수집 작업들을 재시도"""
    try:
        collection_service = CampaignReelCollectionService()
        retried_count = collection_service.retry_failed_jobs(campaign_id=campaign_id, limit=10)
        
        return {
            "message": f"Retried {retried_count} failed reel collection jobs",
            "retried_count": retried_count
        }
        
    except Exception as e:
        print(f"Error retrying failed reel collection jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cancel-processing-reel-jobs")
async def cancel_processing_reel_jobs(campaign_id: int = None):
    """현재 처리 중인 릴스 수집 작업들을 취소"""
    try:
        collection_service = CampaignReelCollectionService()
        cancelled_count = collection_service.cancel_processing_jobs(campaign_id=campaign_id)
        
        return {
            "message": f"Cancelled {cancelled_count} processing reel collection jobs",
            "cancelled_count": cancelled_count
        }
        
    except Exception as e:
        print(f"Error cancelling processing reel collection jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/stop-collection-worker")
async def stop_collection_worker_endpoint():
    """현재 실행 중인 수집 워커를 중지"""
    try:
        stop_collection_worker()
        
        return {
            "message": "Collection worker stopped successfully",
            "status": "stopped"
        }
        
    except Exception as e:
        print(f"Error stopping collection worker: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/collection-worker-status")
async def get_collection_worker_status():
    """수집 워커의 현재 상태 조회"""
    try:
        status = get_worker_status()
        
        return {
            "worker_status": status,
            "message": f"Worker is {'running' if status['is_running'] else 'stopped'}"
        }
        
    except Exception as e:
        print(f"Error getting collection worker status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cancel-processing-jobs")
async def cancel_processing_jobs(db: Session = Depends(get_db)):
    """현재 processing 상태인 모든 수집 작업을 취소하고 워커 중지"""
    try:
        # 워커 중지
        stop_collection_worker()
        
        # processing 상태인 작업들을 cancelled로 변경
        processing_jobs = db.query(models.CollectionJob).filter(
            models.CollectionJob.status == "processing"
        ).all()
        
        cancelled_count = 0
        for job in processing_jobs:
            job.status = "cancelled"
            job.error_message = "작업이 사용자에 의해 취소되었습니다"
            if job.profile_status == "processing":
                job.profile_status = "cancelled"
            if job.posts_status == "processing":
                job.posts_status = "cancelled"
            if job.reels_status == "processing":
                job.reels_status = "cancelled"
            cancelled_count += 1
        
        db.commit()
        
        return {
            "message": f"Cancelled {cancelled_count} processing jobs and stopped collection worker",
            "cancelled_count": cancelled_count,
            "worker_stopped": True
        }
        
    except Exception as e:
        print(f"Error cancelling processing jobs: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/delete-pending-jobs")
async def delete_pending_jobs(campaign_id: int = None, db: Session = Depends(get_db)):
    """대기 중인 수집 작업들을 삭제"""
    try:
        # 캠페인 릴스 수집 작업 조회
        query = db.query(models.CampaignReelCollectionJob).filter(
            models.CampaignReelCollectionJob.status == "pending"
        )
        
        # 특정 캠페인이 지정된 경우
        if campaign_id:
            query = query.filter(models.CampaignReelCollectionJob.campaign_id == campaign_id)
        
        pending_jobs = query.all()
        deleted_count = len(pending_jobs)
        
        # 대기 중인 작업들 삭제
        for job in pending_jobs:
            db.delete(job)
        
        db.commit()
        
        return {
            "message": f"Deleted {deleted_count} pending reel collection jobs",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"Error deleting pending jobs: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/delete-failed-jobs")
async def delete_failed_jobs(campaign_id: int = None, db: Session = Depends(get_db)):
    """실패한 수집 작업들을 삭제"""
    try:
        # 캠페인 릴스 수집 작업 조회
        query = db.query(models.CampaignReelCollectionJob).filter(
            models.CampaignReelCollectionJob.status == "failed"
        )
        
        # 특정 캠페인이 지정된 경우
        if campaign_id:
            query = query.filter(models.CampaignReelCollectionJob.campaign_id == campaign_id)
        
        failed_jobs = query.all()
        deleted_count = len(failed_jobs)
        
        # 실패한 작업들 삭제
        for job in failed_jobs:
            db.delete(job)
        
        db.commit()
        
        return {
            "message": f"Deleted {deleted_count} failed reel collection jobs",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"Error deleting failed jobs: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/delete-completed-jobs")
async def delete_completed_jobs(campaign_id: int = None, db: Session = Depends(get_db)):
    """완료된 수집 작업들을 삭제"""
    try:
        # 캠페인 릴스 수집 작업 조회
        query = db.query(models.CampaignReelCollectionJob).filter(
            models.CampaignReelCollectionJob.status == "completed"
        )
        
        # 특정 캠페인이 지정된 경우
        if campaign_id:
            query = query.filter(models.CampaignReelCollectionJob.campaign_id == campaign_id)
        
        completed_jobs = query.all()
        deleted_count = len(completed_jobs)
        
        # 완료된 작업들 삭제
        for job in completed_jobs:
            db.delete(job)
        
        db.commit()
        
        return {
            "message": f"Deleted {deleted_count} completed reel collection jobs",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"Error deleting completed jobs: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/retry-failed-collection-jobs")
async def retry_failed_collection_jobs(db: Session = Depends(get_db)):
    """실패한 인플루언서 분석 작업들을 재시도"""
    try:
        from datetime import datetime
        
        # 실패한 CollectionJob들 조회
        failed_jobs = db.query(models.CollectionJob).filter(
            models.CollectionJob.status == "failed"
        ).all()
        
        retried_count = 0
        for job in failed_jobs:
            job.status = "pending"
            job.started_at = None
            job.completed_at = None
            job.error_message = None
            job.profile_status = "pending"
            job.posts_status = "pending" if job.collect_posts else "skipped"
            job.reels_status = "pending" if job.collect_reels else "skipped"
            retried_count += 1
        
        db.commit()
        
        return {
            "message": f"Retried {retried_count} failed collection jobs",
            "retried_count": retried_count
        }
        
    except Exception as e:
        print(f"Error retrying failed collection jobs: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/emergency-stop-all")
async def emergency_stop_all_collections(db: Session = Depends(get_db)):
    """모든 수집 작업을 긴급 중지합니다"""
    try:
        from ..services.collection_worker import stop_collection_worker
        
        # 1. Collection worker 중지
        stop_collection_worker()
        
        # 2. 처리중인 인플루언서 수집 작업 취소
        processing_influencer_jobs = db.query(models.CollectionJob).filter(
            models.CollectionJob.status == "processing"
        ).all()
        
        for job in processing_influencer_jobs:
            job.status = "cancelled"
            job.completed_at = datetime.utcnow() + timedelta(hours=9)  # KST
            job.error_message = "사용자에 의해 긴급 중지됨"
        
        # 3. 처리중인 캠페인 수집 작업 취소
        processing_campaign_jobs = db.query(models.CampaignReelCollectionJob).filter(
            models.CampaignReelCollectionJob.status == "processing"
        ).all()
        
        for job in processing_campaign_jobs:
            job.status = "cancelled"
            job.completed_at = datetime.utcnow() + timedelta(hours=9)  # KST
            job.error_message = "사용자에 의해 긴급 중지됨"
        
        db.commit()
        
        total_stopped = len(processing_influencer_jobs) + len(processing_campaign_jobs)
        
        return {
            "message": f"모든 수집 작업이 긴급 중지되었습니다",
            "influencer_jobs_stopped": len(processing_influencer_jobs),
            "campaign_jobs_stopped": len(processing_campaign_jobs),
            "total_stopped": total_stopped,
            "worker_stopped": True
        }
        
    except Exception as e:
        print(f"Error in emergency stop: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")