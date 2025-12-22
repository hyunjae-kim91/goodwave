from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, time

from app.db.database import get_db
from app.db import models
from app.services.campaign_reel_collection_service import CampaignReelCollectionService
from app.services.collection_worker import stop_collection_worker, get_worker_status
from app.services.campaign_schedule_runner import get_campaign_schedule_status
from app.utils.sequence_fixer import fix_all_sequences, fix_table_sequence
from sqlalchemy.orm import selectinload

KST_OFFSET = timedelta(hours=9)

def now_kst() -> datetime:
    """한국 시간(KST) 기준 현재 시간 반환"""
    return datetime.utcnow() + KST_OFFSET

router = APIRouter()

@router.get("/dashboard")
async def get_admin_dashboard(db: Session = Depends(get_db)):
    """관리자 대시보드 데이터"""
    try:
        # 단일 쿼리로 모든 통계 계산 (성능 최적화)
        all_campaigns = db.query(models.Campaign).all()
        total_campaigns = len(all_campaigns)
        
        # 메모리에서 필터링하여 타입별 개수 계산
        instagram_post_campaigns = sum(1 for c in all_campaigns if c.campaign_type in ['instagram_post', 'all'])
        instagram_reel_campaigns = sum(1 for c in all_campaigns if c.campaign_type in ['instagram_reel', 'all'])
        blog_campaigns = sum(1 for c in all_campaigns if c.campaign_type in ['blog', 'all'])
        
        # 활성 캠페인 수 (별도 쿼리)
        active_campaigns = db.query(models.CollectionSchedule).filter(
            models.CollectionSchedule.is_active == True
        ).count()
        
        # 캠페인 정보 (최신순으로 제한하여 성능 개선)
        campaigns = sorted(all_campaigns, key=lambda x: x.created_at if x.created_at else datetime.min, reverse=True)
        
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
                    'start_date': campaign.start_date.isoformat() if campaign.start_date else None,
                    'end_date': campaign.end_date.isoformat() if campaign.end_date else None,
                    'created_at': campaign.created_at.isoformat() if campaign.created_at else None
                }
                for campaign in campaigns
            ]
        }
        
    except Exception as e:
        import traceback
        error_detail = f"Error getting admin dashboard: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
            'schedule_hour': schedule.schedule_hour if hasattr(schedule, 'schedule_hour') else 9,
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

@router.put("/collection-schedules/campaign/{campaign_id}/schedule-time")
async def update_campaign_schedule_time(
    campaign_id: int,
    schedule_hour: int,
    db: Session = Depends(get_db)
):
    """캠페인의 모든 스케줄 시간(시) 업데이트"""
    # 시간 유효성 검사
    if not (0 <= schedule_hour <= 23):
        raise HTTPException(status_code=400, detail="schedule_hour must be between 0 and 23")
    
    # 캠페인 존재 확인
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 해당 캠페인의 모든 스케줄 업데이트
    schedules = db.query(models.CollectionSchedule).filter(
        models.CollectionSchedule.campaign_id == campaign_id
    ).all()
    
    if not schedules:
        raise HTTPException(status_code=404, detail="No schedules found for this campaign")
    
    updated_count = 0
    for schedule in schedules:
        schedule.schedule_hour = schedule_hour
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"Updated schedule time for {updated_count} schedule(s)",
        "campaign_id": campaign_id,
        "schedule_hour": schedule_hour,
        "updated_count": updated_count
    }

@router.get("/campaign-collection-status")
async def get_campaign_collection_status(db: Session = Depends(get_db)):
    """캠페인 수집 진행 현황 조회 (릴스 + 블로그)"""
    try:
        collection_service = CampaignReelCollectionService()
        
        # 모든 캠페인의 릴스 수집 현황
        all_status = collection_service.get_all_campaigns_collection_status()
        
        # 블로그 캠페인 데이터 추가
        blog_campaigns = db.query(models.Campaign).filter(
            models.Campaign.campaign_type.in_(['blog', 'all'])
        ).all()
        
        for campaign in blog_campaigns:
            # 이미 릴스 데이터가 있는 캠페인인지 확인
            existing_status = next((s for s in all_status if s["campaign_id"] == campaign.id), None)
            
            # 블로그 데이터 조회
            blog_data = db.query(models.CampaignBlog).filter(
                models.CampaignBlog.campaign_id == campaign.id
            ).options(selectinload(models.CampaignBlog.rankings)).all()
            
            blog_jobs = []
            for blog in blog_data:
                blog_jobs.append({
                    "id": blog.id,
                    "campaign_id": campaign.id,
                    "blog_url": blog.campaign_url,
                    "title": blog.title,
                    "username": blog.username,
                    "likes_count": blog.likes_count,
                    "comments_count": blog.comments_count,
                    "daily_visitors": blog.daily_visitors,
                    "posted_at": blog.posted_at.isoformat() if blog.posted_at else None,
                    "collection_date": blog.collection_date.isoformat() if blog.collection_date else None,
                    "rankings": [
                        {
                            "keyword": ranking.keyword,
                            "ranking": ranking.ranking
                        }
                        for ranking in blog.rankings
                    ]
                })
            
            if existing_status:
                # 릴스 데이터가 있는 캠페인에 블로그 데이터 병합
                existing_status["blog_jobs"] = blog_jobs
                existing_status["has_blog_data"] = len(blog_jobs) > 0
            else:
                # 블로그 전용 캠페인인 경우 새로 추가
                all_status.append({
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "campaign_type": campaign.campaign_type,
                    "product": campaign.product,
                    "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
                    "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
                    "total_jobs": len(blog_jobs),
                    "status_counts": {
                        "pending": 0,
                        "processing": 0,
                        "completed": len(blog_jobs),
                        "failed": 0
                    },
                    "jobs": blog_jobs,
                    "is_blog": True  # 블로그 데이터임을 표시
                })
        
        # 캠페인 정보 추가 및 스케줄 시간 설정
        for status in all_status:
            campaign = db.query(models.Campaign).filter(
                models.Campaign.id == status["campaign_id"]
            ).first()
            
            if campaign:
                if "campaign_name" not in status:
                    status["campaign_name"] = campaign.name
                if "campaign_type" not in status:
                    status["campaign_type"] = campaign.campaign_type
                if "product" not in status:
                    status["product"] = campaign.product
                if "start_date" not in status:
                    status["start_date"] = campaign.start_date.isoformat() if campaign.start_date else None
                if "end_date" not in status:
                    status["end_date"] = campaign.end_date.isoformat() if campaign.end_date else None
                
                # 스케줄 시간 정보 추가 (첫 번째 스케줄의 시간 사용)
                schedule = db.query(models.CollectionSchedule).filter(
                    models.CollectionSchedule.campaign_id == campaign.id
                ).first()
                
                if schedule:
                    status["schedule_hour"] = schedule.schedule_hour if hasattr(schedule, 'schedule_hour') else 9
                else:
                    status["schedule_hour"] = 9
        
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
            status["start_date"] = campaign.start_date.isoformat() if campaign.start_date else None
            status["end_date"] = campaign.end_date.isoformat() if campaign.end_date else None
            
            # 스케줄 시간 정보 추가 (첫 번째 스케줄의 시간 사용)
            schedule = db.query(models.CollectionSchedule).filter(
                models.CollectionSchedule.campaign_id == campaign.id
            ).first()
            
            if schedule:
                status["schedule_hour"] = schedule.schedule_hour if hasattr(schedule, 'schedule_hour') else 9
            else:
                status["schedule_hour"] = 9
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting campaign collection status for {campaign_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/check-today-collection/{campaign_id}")
async def check_today_collection(campaign_id: int, db: Session = Depends(get_db)):
    """오늘 날짜에 해당 캠페인의 릴스/블로그 데이터가 수집되었는지 확인"""
    try:
        # 캠페인 존재 확인
        campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 오늘 날짜 (한국 시간 기준)
        today = now_kst().date()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today + timedelta(days=1), time.min)
        
        # 블로그 캠페인인지 확인
        is_blog_campaign = campaign.campaign_type in ['blog', 'all']
        
        if is_blog_campaign:
            # 블로그 캠페인의 경우 CampaignBlog 테이블에서 오늘 날짜 데이터 확인
            today_blog_data = db.query(models.CampaignBlog).filter(
                models.CampaignBlog.campaign_id == campaign_id,
                models.CampaignBlog.collection_date >= today_start,
                models.CampaignBlog.collection_date < today_end
            ).count()
            
            return {
                "has_today_data": today_blog_data > 0,
                "today_count": today_blog_data,
                "today_date": today.isoformat(),
                "is_blog": True
            }
        else:
            # 릴스 캠페인의 경우 CampaignReelCollectionJob 테이블에서 확인
            today_completed_jobs = db.query(models.CampaignReelCollectionJob).filter(
                models.CampaignReelCollectionJob.campaign_id == campaign_id,
                models.CampaignReelCollectionJob.status == 'completed',
                models.CampaignReelCollectionJob.completed_at >= today_start,
                models.CampaignReelCollectionJob.completed_at < today_end
            ).count()
            
            return {
                "has_today_data": today_completed_jobs > 0,
                "today_count": today_completed_jobs,
                "today_date": today.isoformat(),
                "is_blog": False
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error checking today collection for {campaign_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/test-blog-collection/{campaign_id}")
async def test_blog_collection(campaign_id: int, db: Session = Depends(get_db)):
    """블로그 수집 API 테스트 (특정 캠페인의 블로그 스케줄 수집 테스트)"""
    try:
        # 캠페인 존재 확인
        campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 블로그 스케줄 찾기
        blog_schedules = db.query(models.CollectionSchedule).filter(
            models.CollectionSchedule.campaign_id == campaign_id,
            models.CollectionSchedule.channel == 'blog',
            models.CollectionSchedule.is_active == True
        ).all()
        
        if not blog_schedules:
            return {
                "message": f"캠페인 {campaign_id}에 활성화된 블로그 스케줄이 없습니다.",
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "schedules_found": 0,
                "results": []
            }
        
        from app.services.scheduler_service import SchedulerService
        from datetime import datetime, timedelta
        
        KST_OFFSET = timedelta(hours=9)
        collection_date = datetime.utcnow() + KST_OFFSET
        
        # 새로운 스케줄러 인스턴스 생성 (테스트용)
        scheduler = SchedulerService()
        results = []
        
        for schedule in blog_schedules:
            try:
                print(f"Testing blog collection for schedule {schedule.id}: {schedule.campaign_url}")
                
                # 블로그 수집 실행 (private 메서드이지만 테스트를 위해 접근)
                await scheduler._collect_campaign_blogs(schedule, campaign, collection_date)
                scheduler.db.commit()
                
                # 스케줄러 세션에서 수집된 데이터 확인 (commit 후)
                blog_entry = scheduler.db.query(models.CampaignBlog).filter(
                    models.CampaignBlog.campaign_id == campaign_id,
                    models.CampaignBlog.campaign_url == schedule.campaign_url,
                    models.CampaignBlog.collection_date >= collection_date.replace(hour=0, minute=0, second=0, microsecond=0),
                    models.CampaignBlog.collection_date < (collection_date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
                ).first()
                
                if blog_entry:
                    rankings = scheduler.db.query(models.CampaignBlogRanking).filter(
                        models.CampaignBlogRanking.campaign_blog_id == blog_entry.id
                    ).all()
                    
                    results.append({
                        "schedule_id": schedule.id,
                        "blog_url": schedule.campaign_url,
                        "success": True,
                        "collected_data": {
                            "title": blog_entry.title,
                            "username": blog_entry.username,
                            "likes_count": blog_entry.likes_count,
                            "comments_count": blog_entry.comments_count,
                            "daily_visitors": blog_entry.daily_visitors,
                            "posted_at": blog_entry.posted_at.isoformat() if blog_entry.posted_at else None,
                            "collection_date": blog_entry.collection_date.isoformat() if blog_entry.collection_date else None,
                            "rankings": [
                                {"keyword": r.keyword, "ranking": r.ranking}
                                for r in rankings
                            ]
                        }
                    })
                else:
                    # 수집은 성공했지만 DB에 저장되지 않은 경우 확인
                    results.append({
                        "schedule_id": schedule.id,
                        "blog_url": schedule.campaign_url,
                        "success": False,
                        "message": "데이터가 수집되었지만 DB에 저장되지 않았습니다. 로그를 확인하세요.",
                        "note": "수집은 성공했을 수 있지만, DB 조회 조건이 맞지 않거나 커밋이 되지 않았을 수 있습니다."
                    })
                    
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"Error testing blog collection for schedule {schedule.id}: {error_detail}")
                results.append({
                    "schedule_id": schedule.id,
                    "blog_url": schedule.campaign_url,
                    "success": False,
                    "error": str(e),
                    "traceback": error_detail
                })
            finally:
                # 스케줄러 세션 정리
                scheduler.db.close()
        
        success_count = sum(1 for r in results if r.get("success", False))
        failed_count = len(results) - success_count
        
        return {
            "message": f"블로그 수집 테스트 완료",
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "schedules_tested": len(blog_schedules),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "note": "Playwright 기반 수집이 활성화되었습니다. 일일 방문자 수 API 오류는 무시됩니다 (기본 정보는 정상 수집됨)."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in test blog collection: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/immediate-collection/{campaign_id}")
async def immediate_collection(campaign_id: int, db: Session = Depends(get_db)):
    """캠페인 릴스/블로그 정보 즉시 수집"""
    try:
        # 캠페인 존재 확인
        campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 블로그 캠페인인지 확인
        is_blog_campaign = campaign.campaign_type in ['blog', 'all']
        
        # 오늘 날짜 (한국 시간 기준)
        today = now_kst().date()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today + timedelta(days=1), time.min)
        
        if is_blog_campaign:
            # 블로그 캠페인의 경우 오늘 날짜 데이터 확인
            today_blog_data = db.query(models.CampaignBlog).filter(
                models.CampaignBlog.campaign_id == campaign_id,
                models.CampaignBlog.collection_date >= today_start,
                models.CampaignBlog.collection_date < today_end
            ).count()
            
            if today_blog_data > 0:
                return {
                    "message": f"오늘({today.isoformat()}) 수집된 블로그 데이터가 {today_blog_data}개 있습니다. 큐에 추가하지 않습니다.",
                    "has_today_data": True,
                    "today_count": today_blog_data,
                    "skipped": True
                }
            
            # 블로그 즉시 수집 실행
            from app.services.scheduler_service import SchedulerService
            
            KST_OFFSET = timedelta(hours=9)
            collection_date = datetime.utcnow() + KST_OFFSET
            
            scheduler = SchedulerService()
            blog_schedules = db.query(models.CollectionSchedule).filter(
                models.CollectionSchedule.campaign_id == campaign_id,
                models.CollectionSchedule.channel == 'blog',
                models.CollectionSchedule.is_active == True
            ).all()
            
            if not blog_schedules:
                return {
                    "message": "활성화된 블로그 수집 스케줄이 없습니다.",
                    "has_today_data": False,
                    "today_count": 0,
                    "skipped": False
                }
            
            processed_count = 0
            try:
                for schedule in blog_schedules:
                    try:
                        await scheduler._collect_campaign_blogs(schedule, campaign, collection_date)
                        scheduler.db.commit()
                        processed_count += 1
                    except Exception as e:
                        print(f"Error collecting blog for schedule {schedule.id}: {str(e)}")
                        scheduler.db.rollback()
                        continue
            finally:
                scheduler.db.close()
            
            return {
                "message": f"{processed_count}개의 블로그 수집 작업이 완료되었습니다.",
                "has_today_data": False,
                "today_count": 0,
                "skipped": False,
                "processed_schedules": processed_count
            }
        else:
            # 릴스 캠페인의 경우 기존 로직
            today_completed_jobs = db.query(models.CampaignReelCollectionJob).filter(
                models.CampaignReelCollectionJob.campaign_id == campaign_id,
                models.CampaignReelCollectionJob.status == 'completed',
                models.CampaignReelCollectionJob.completed_at >= today_start,
                models.CampaignReelCollectionJob.completed_at < today_end
            ).count()
            
            if today_completed_jobs > 0:
                return {
                    "message": f"오늘({today.isoformat()}) 완료일시가 오늘인 완료된 작업이 {today_completed_jobs}개 있습니다. 큐에 추가하지 않습니다.",
                    "has_today_data": True,
                    "today_count": today_completed_jobs,
                    "skipped": True
                }
        
        # 스케줄러 서비스를 통한 즉시 수집
        from app.services.scheduler_service import SchedulerService
        scheduler = SchedulerService()
        
        # 캠페인의 활성 스케줄들 가져오기
        schedules = db.query(models.CollectionSchedule).filter(
            models.CollectionSchedule.campaign_id == campaign_id,
            models.CollectionSchedule.is_active == True
        ).all()
        
        if not schedules:
            return {
                "message": "활성화된 수집 스케줄이 없습니다.",
                "has_today_data": False,
                "today_count": 0,
                "skipped": False
            }
        
        # 각 스케줄 처리 (릴스만) - 큐에만 추가하고 실행은 워커가 처리
        processed_count = 0
        jobs_created = 0
        
        from app.services.campaign_reel_collection_service import CampaignReelCollectionService
        collection_service = CampaignReelCollectionService()
        
        for schedule in schedules:
            if schedule.channel in ['instagram_reel', 'instagram_post']:
                try:
                    # 특정 릴스 URL인 경우 작업을 큐에만 추가 (실행은 워커가 처리)
                    if "/reel/" in schedule.campaign_url:
                        jobs = collection_service.add_reel_collection_jobs(
                            campaign_id=campaign.id,
                            reel_urls=[schedule.campaign_url],
                            check_existing_data=False  # 즉시 수집이므로 기존 데이터 체크 안 함
                        )
                        jobs_created += len(jobs)
                        print(f"📋 {len(jobs)}개 작업을 큐에 추가: {schedule.campaign_url}")
                        # 작업은 큐에만 추가하고, 실행은 워커가 하나씩 처리하도록 함
                    else:
                        # 사용자 프로필 URL인 경우, 스케줄러를 통해 처리
                        # 하지만 오늘 날짜 체크를 우회하기 위해 직접 처리
                        await scheduler._collect_campaign_instagram_reels(schedule, campaign, now_kst())
                    
                    processed_count += 1
                except Exception as e:
                    print(f"스케줄 처리 실패 {schedule.campaign_url}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        # 생성된 작업 수 확인
        total_pending_jobs = db.query(models.CampaignReelCollectionJob).filter(
            models.CampaignReelCollectionJob.campaign_id == campaign_id,
            models.CampaignReelCollectionJob.status == "pending"
        ).count()
        
        total_processing_jobs = db.query(models.CampaignReelCollectionJob).filter(
            models.CampaignReelCollectionJob.campaign_id == campaign_id,
            models.CampaignReelCollectionJob.status == "processing"
        ).count()
        
        return {
            "message": f"{jobs_created}개의 작업이 큐에 추가되었습니다. 워커가 하나씩 처리합니다. (대기 중: {total_pending_jobs}개, 처리 중: {total_processing_jobs}개)",
            "has_today_data": False,
            "today_count": 0,
            "skipped": False,
            "processed_schedules": processed_count,
            "jobs_created": jobs_created,
            "pending_jobs": total_pending_jobs,
            "processing_jobs": total_processing_jobs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in immediate collection for {campaign_id}: {str(e)}")
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

@router.get("/campaign-schedule-runner-status")
async def get_campaign_schedule_runner_status():
    """캠페인 스케줄러의 현재 상태 조회"""
    try:
        status = get_campaign_schedule_status()
        kst_now = now_kst()
        
        return {
            "schedule_runner_status": status,
            "current_time_kst": kst_now.strftime('%Y-%m-%d %H:%M:%S'),
            "current_hour_kst": kst_now.hour,
            "should_run_now": kst_now.hour == 9,
            "message": f"Schedule runner is {'running' if status.get('is_running') else 'stopped'}"
        }
        
    except Exception as e:
        print(f"Error getting campaign schedule runner status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/run-scheduled-collection")
async def run_scheduled_collection_manual(force_run_all: bool = False, run_hour: int | None = None):
    """스케줄 수집을 즉시 1회 실행 (수동 트리거)

    - force_run_all=true: schedule_hour 무시하고 모든 활성 스케줄 처리
    - run_hour=0~23: 현재 시간 대신 해당 시간 기준으로 스케줄 매칭
    """
    try:
        if run_hour is not None and not (0 <= run_hour <= 23):
            raise HTTPException(status_code=400, detail="run_hour must be between 0 and 23")

        from app.services.scheduler_service import SchedulerService

        scheduler = SchedulerService()
        result = await scheduler.run_scheduled_collection(force_run_all=force_run_all, run_hour=run_hour)
        return {
            "message": "Triggered scheduled collection",
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error running scheduled collection manually: {str(e)}")
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


@router.post("/fix-sequences")
async def fix_database_sequences(db: Session = Depends(get_db)):
    """
    모든 테이블의 시퀀스를 리셋합니다.
    UniqueViolation (ID 중복) 에러가 발생할 때 사용하세요.
    """
    try:
        results = fix_all_sequences(db)
        
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        return {
            "success": True,
            "message": f"시퀀스 리셋 완료: {success_count}/{total_count} 테이블",
            "results": results
        }
    except Exception as e:
        print(f"Error fixing sequences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시퀀스 리셋 실패: {str(e)}")


@router.post("/fix-sequence/{table_name}")
async def fix_single_table_sequence(table_name: str, db: Session = Depends(get_db)):
    """
    특정 테이블의 시퀀스만 리셋합니다.
    """
    try:
        success = fix_table_sequence(db, table_name)
        
        if success:
            return {
                "success": True,
                "message": f"'{table_name}' 테이블 시퀀스 리셋 완료"
            }
        else:
            return {
                "success": False,
                "message": f"'{table_name}' 테이블 시퀀스 리셋 실패"
            }
    except Exception as e:
        print(f"Error fixing sequence for {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"시퀀스 리셋 실패: {str(e)}")