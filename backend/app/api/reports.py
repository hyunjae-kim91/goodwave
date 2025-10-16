from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_
from typing import Any, Dict, List

from app.db.database import get_db
from app.db import models

router = APIRouter()

@router.get("/instagram/posts/{campaign_name}")
async def get_instagram_post_report(
    campaign_name: str,
    db: Session = Depends(get_db)
):
    """인스타그램 게시물 보고서 데이터"""
    try:
        # 캠페인 정보 조회
        campaign = db.query(models.Campaign).filter(
            models.Campaign.name == campaign_name,
            models.Campaign.campaign_type.in_(['instagram_post', 'instagram_reel', 'all'])
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 캠페인 기간 내 릴스 데이터 조회
        campaign_reels = (
            db.query(models.CampaignInstagramReel)
            .filter(
                and_(
                    models.CampaignInstagramReel.campaign_id == campaign.id,
                    models.CampaignInstagramReel.collection_date >= campaign.start_date,
                    models.CampaignInstagramReel.collection_date <= campaign.end_date
                )
            )
            .order_by(models.CampaignInstagramReel.collection_date.asc())
            .all()
        )

        # 날짜별 조회 수 집계
        engagement_data: Dict[str, int] = {}
        for reel in campaign_reels:
            if not reel.collection_date:
                continue
            date_key = reel.collection_date.strftime('%Y-%m-%d')
            engagement_data[date_key] = engagement_data.get(date_key, 0) + (reel.video_view_count or 0)

        # 차트 데이터 생성 (날짜순 정렬)
        sorted_dates = sorted(engagement_data.keys())
        chart_data = {
            'labels': sorted_dates,
            'data': [engagement_data[date] for date in sorted_dates]
        }

        # Unique campaign URL 개수 계산
        unique_campaign_urls = len({reel.campaign_url for reel in campaign_reels})
        
        return {
            'campaign': {
                'name': campaign.name,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'product': campaign.product,
                'budget': campaign.budget
            },
            'unique_reel_count': unique_campaign_urls,
            'reels': [
                {
                    'id': reel.id,
                    'reel_id': reel.reel_id,
                    'username': reel.username,
                    'display_name': reel.display_name,
                    'follower_count': reel.follower_count,
                    's3_thumbnail_url': reel.s3_thumbnail_url,
                    'video_view_count': reel.video_view_count,
                    'subscription_motivation': reel.subscription_motivation,
                    'category': reel.category,
                    'grade': reel.grade,
                    'product': reel.product,
                    'posted_at': reel.posted_at,
                    'collection_date': reel.collection_date,
                    'campaign_url': reel.campaign_url
                }
                for reel in campaign_reels
            ],
            'chart_data': chart_data
        }
        
    except Exception as e:
        print(f"Error getting Instagram post report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/instagram/reels/{campaign_name}")
async def get_instagram_reel_report(
    campaign_name: str,
    db: Session = Depends(get_db)
):
    """인스타그램 릴스 보고서 데이터"""
    try:
        # 캠페인 정보 조회
        campaign = db.query(models.Campaign).filter(
            models.Campaign.name == campaign_name,
            models.Campaign.campaign_type.in_(['instagram_reel', 'all'])
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 캠페인 기간 내 데이터 조회
        campaign_reels = db.query(models.CampaignInstagramReel).filter(
            and_(
                models.CampaignInstagramReel.campaign_id == campaign.id,
                models.CampaignInstagramReel.collection_date >= campaign.start_date,
                models.CampaignInstagramReel.collection_date <= campaign.end_date
            )
        ).all()
        
        # 날짜별 비디오 조회 수 집계
        view_data = {}
        for reel in campaign_reels:
            date_key = reel.collection_date.strftime('%Y-%m-%d')
            if date_key not in view_data:
                view_data[date_key] = 0
            view_data[date_key] += reel.video_view_count
        
        # 차트 데이터 생성
        chart_data = {
            'labels': list(view_data.keys()),
            'data': list(view_data.values())
        }
        
        # Unique campaign URL 개수 계산
        unique_campaign_urls = len(set(reel.campaign_url for reel in campaign_reels))
        
        return {
            'campaign': {
                'name': campaign.name,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'product': campaign.product,
                'budget': campaign.budget
            },
            'unique_reel_count': unique_campaign_urls,
            'reels': [
                {
                    'id': reel.id,
                    'reel_id': reel.reel_id,
                    'username': reel.username,
                    'display_name': reel.display_name,
                    'follower_count': reel.follower_count,
                    's3_thumbnail_url': reel.s3_thumbnail_url,
                    'video_view_count': reel.video_view_count,
                    'subscription_motivation': reel.subscription_motivation,
                    'category': reel.category,
                    'grade': reel.grade,
                    'product': reel.product,
                    'posted_at': reel.posted_at,
                    'collection_date': reel.collection_date,
                    'campaign_url': reel.campaign_url
                }
                for reel in campaign_reels
            ],
            'chart_data': chart_data
        }
        
    except Exception as e:
        print(f"Error getting Instagram reel report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/blogs/{campaign_name}")
async def get_blog_report(
    campaign_name: str,
    db: Session = Depends(get_db)
):
    """블로그 보고서 데이터"""
    try:
        # 캠페인 정보 조회
        campaign = db.query(models.Campaign).filter(
            models.Campaign.name == campaign_name,
            models.Campaign.campaign_type.in_(['blog', 'all'])
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 캠페인 기간 내 데이터 조회
        campaign_blogs = db.query(models.CampaignBlog).options(
            selectinload(models.CampaignBlog.rankings)
        ).filter(
            and_(
                models.CampaignBlog.campaign_id == campaign.id,
                models.CampaignBlog.collection_date >= campaign.start_date,
                models.CampaignBlog.collection_date <= campaign.end_date
            )
        ).all()
        
        # 실제 수집된 날짜만 컬럼으로 생성
        collection_dates = set()
        for blog in campaign_blogs:
            collection_dates.add(blog.collection_date.strftime('%Y-%m-%d'))
        date_range = sorted(list(collection_dates))
        
        # 블로그별 순위 데이터 정리
        blog_ranking_data: Dict[str, Dict[str, Any]] = {}
        for blog in campaign_blogs:
            if blog.campaign_url not in blog_ranking_data:
                blog_ranking_data[blog.campaign_url] = {
                    'url': blog.campaign_url,
                    'username': blog.username,
                    'title': blog.title,
                    'likes_count': blog.likes_count,
                    'comments_count': blog.comments_count,
                    'daily_visitors': blog.daily_visitors,
                    'posted_at': blog.posted_at,
                    'rankings': {}
                }
            
            # 날짜별 순위 정보와 방문자 수
            date_key = blog.collection_date.strftime('%Y-%m-%d')
            rankings_map = blog_ranking_data[blog.campaign_url]['rankings']
            entries: List[str] = rankings_map.setdefault(date_key, [])

            if blog.rankings:
                for ranking in blog.rankings:
                    label = f"[{ranking.keyword}]"
                    if ranking.ranking is not None:
                        label = f"{label} {ranking.ranking}위"
                    entries.append(label)
            elif blog.keyword:  # 레거시 데이터 호환
                label = f"[{blog.keyword}]"
                if blog.ranking:
                    label = f"{label} {blog.ranking}위"
                entries.append(label)

            if blog.daily_visitors and f"방문자: {blog.daily_visitors}" not in entries:
                entries.append(f"방문자: {blog.daily_visitors}")

        # 문자열 형태로 정리
        for info in blog_ranking_data.values():
            info['rankings'] = {
                date: " | ".join(items)
                for date, items in info['rankings'].items()
                if items
            }
        
        return {
            'campaign': {
                'name': campaign.name,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'product': campaign.product,
                'budget': campaign.budget
            },
            'date_columns': date_range,
            'blogs': list(blog_ranking_data.values())
        }
        
    except Exception as e:
        print(f"Error getting blog report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/campaigns")
async def get_available_campaigns(db: Session = Depends(get_db)):
    """사용 가능한 캠페인 목록"""
    campaigns = db.query(models.Campaign).all()
    return [
        {
            'id': campaign.id,
            'name': campaign.name,
            'campaign_type': campaign.campaign_type,
            'start_date': campaign.start_date,
            'end_date': campaign.end_date,
            'product': campaign.product
        }
        for campaign in campaigns
    ]
