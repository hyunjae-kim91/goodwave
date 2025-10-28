"""
통합 뷰를 사용하는 캠페인 보고서 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime

from app.db.database import get_db
from app.db.unified_models import CampaignInstagramUnifiedView
from app.db import models

router = APIRouter()

@router.get("/instagram/unified/{campaign_name}")
async def get_unified_instagram_report(
    campaign_name: str,
    db: Session = Depends(get_db)
):
    """통합 뷰를 사용한 인스타그램 캠페인 보고서"""
    try:
        print(f"🔍 통합 뷰에서 캠페인 '{campaign_name}' 조회 시작")
        
        # 캠페인 기본 정보 조회
        campaign = db.query(models.Campaign).filter(
            models.Campaign.name == campaign_name,
            models.Campaign.campaign_type.in_(['instagram_post', 'instagram_reel', 'all'])
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 통합 뷰에서 캠페인 데이터 조회
        unified_data = db.query(CampaignInstagramUnifiedView).filter(
            CampaignInstagramUnifiedView.campaign_id == campaign.id
        ).order_by(CampaignInstagramUnifiedView.collection_date.desc()).all()
        
        print(f"📊 통합 뷰에서 {len(unified_data)}개 레코드 조회됨")
        
        # 데이터 소스별 분류
        campaign_data = []
        influencer_data = []
        
        for record in unified_data:
            record_dict = record.to_dict()
            if record.data_source == 'campaign':
                campaign_data.append(record_dict)
            else:
                influencer_data.append(record_dict)
        
        print(f"📈 데이터 분류: 캠페인 {len(campaign_data)}개, 인플루언서 {len(influencer_data)}개")
        
        # 통합 데이터 (인플루언서 우선)
        all_data = influencer_data + campaign_data
        
        # 중복 제거 (같은 username의 경우 인플루언서 데이터 우선)
        seen_usernames = set()
        unique_data = []
        
        for record in all_data:
            username = record['username']
            if username not in seen_usernames:
                unique_data.append(record)
                seen_usernames.add(username)
        
        print(f"🔄 중복 제거 후: {len(unique_data)}개")
        
        # 날짜별 조회수 집계
        view_data = defaultdict(int)
        for record in unique_data:
            collection_date = record.get('collection_date')
            if collection_date:
                try:
                    if isinstance(collection_date, str):
                        date_obj = datetime.fromisoformat(collection_date.replace('Z', '+00:00'))
                    else:
                        date_obj = collection_date
                    date_key = date_obj.strftime('%Y-%m-%d')
                    view_data[date_key] += record.get('video_view_count', 0)
                except (ValueError, AttributeError):
                    continue
        
        # 차트 데이터 생성
        sorted_dates = sorted(view_data.keys())
        chart_data = {
            'labels': sorted_dates,
            'data': [view_data[date] for date in sorted_dates]
        }
        
        # 통계 계산
        total_views = sum(record.get('video_view_count', 0) for record in unique_data)
        avg_views = total_views / len(unique_data) if unique_data else 0
        
        # 등급별 분포
        grade_distribution = defaultdict(int)
        for record in unique_data:
            grade = record.get('grade', 'Unknown')
            grade_distribution[grade] += 1
        
        return {
            'campaign': {
                'name': campaign.name,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'product': campaign.product,
                'budget': campaign.budget
            },
            'summary': {
                'total_reels': len(unique_data),
                'campaign_source_count': len(campaign_data),
                'influencer_source_count': len(influencer_data),
                'unique_influencers': len(seen_usernames),
                'total_views': total_views,
                'average_views': round(avg_views, 2),
                'grade_distribution': dict(grade_distribution)
            },
            'reels': unique_data,
            'chart_data': chart_data,
            'data_sources': {
                'campaign': len(campaign_data),
                'influencer': len(influencer_data),
                'total_unique': len(unique_data)
            }
        }
        
    except Exception as e:
        print(f"❌ 통합 보고서 조회 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/test-view")
async def test_unified_view(db: Session = Depends(get_db)):
    """통합 뷰 테스트용 엔드포인트"""
    try:
        # 뷰에서 샘플 데이터 조회
        sample_data = db.query(CampaignInstagramUnifiedView).limit(5).all()
        
        return {
            'total_records': len(sample_data),
            'sample_data': [record.to_dict() for record in sample_data]
        }
    except Exception as e:
        return {'error': str(e)}