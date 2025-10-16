from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models

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