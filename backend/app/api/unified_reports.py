"""
통합 뷰를 사용하는 캠페인 보고서 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime

from app.db.database import get_db
from app.db.unified_models import CampaignInstagramUnifiedView
from app.db import models
from app.services.grade_service import instagram_grade_service

router = APIRouter()


def _calculate_influencer_grade(db: Session, username: str) -> Optional[str]:
    """
    사용자의 등급을 계산합니다.
    24개 릴스의 평균 조회수 (최상 2개 + 최하위 2개 제외한 나머지 20개의 평균)로 계산
    """
    result = _calculate_influencer_grade_with_avg(db, username)
    return result['grade'] if result else None


def _calculate_influencer_grade_with_avg(db: Session, username: str) -> Optional[Dict[str, Any]]:
    """
    사용자의 등급과 평균 조회수를 계산합니다.
    24개 릴스의 평균 조회수 (최상 2개 + 최하위 2개 제외한 나머지 20개의 평균)로 계산
    """
    # 인플루언서 프로필 조회
    profile = db.query(models.InfluencerProfile).filter(
        models.InfluencerProfile.username == username
    ).first()
    
    if not profile:
        return None
    
    # 최대 24개 릴스의 조회수 조회
    reels = db.query(models.InfluencerReel).filter(
        models.InfluencerReel.profile_id == profile.id,
        models.InfluencerReel.video_play_count.isnot(None)
    ).order_by(models.InfluencerReel.created_at.desc()).limit(24).all()
    
    if not reels:
        return None
    
    # 조회수 추출
    view_counts = [reel.video_play_count for reel in reels if reel.video_play_count is not None and reel.video_play_count > 0]
    
    if len(view_counts) == 0:
        return None
    
    # 최상위 2개, 최하위 2개 제외 (20개 이상일 때만)
    if len(view_counts) > 4:
        view_counts_sorted = sorted(view_counts)
        trimmed_counts = view_counts_sorted[2:-2]  # 최하위 2개, 최상위 2개 제외
    else:
        trimmed_counts = view_counts
    
    if not trimmed_counts:
        return None
    
    # 평균 계산
    average_views = sum(trimmed_counts) / len(trimmed_counts)
    
    # instagram_grade_thresholds 테이블 기준으로 등급 반환
    grade = instagram_grade_service.get_grade_for_average(db, average_views)
    
    return {
        'grade': grade,
        'avg_views': average_views,
        'total_reels': len(view_counts),
        'trimmed_reels': len(trimmed_counts)
    }


def _get_latest_reel_view_count(db: Session, reel_id: str, username: str) -> int:
    """
    특정 릴스의 최신 조회수를 반환합니다.
    """
    # 인플루언서 프로필 조회
    profile = db.query(models.InfluencerProfile).filter(
        models.InfluencerProfile.username == username
    ).first()
    
    if not profile:
        return 0
    
    reel = db.query(models.InfluencerReel).filter(
        models.InfluencerReel.reel_id == reel_id,
        models.InfluencerReel.profile_id == profile.id
    ).order_by(models.InfluencerReel.created_at.desc()).first()
    
    if not reel:
        return 0
    
    return reel.video_play_count or reel.views or 0

@router.get("/instagram/unified/{campaign_name}")
async def get_unified_instagram_report(
    campaign_name: str,
    db: Session = Depends(get_db)
):
    """캠페인 릴스 수집 작업 기반 인스타그램 보고서"""
    try:
        # URL 디코딩 (FastAPI가 자동으로 하지만 명시적으로 처리)
        from urllib.parse import unquote
        decoded_campaign_name = unquote(campaign_name)
        print(f"🔍 캠페인 '{decoded_campaign_name}' 조회 시작 (원본: {campaign_name})")
        
        # 캠페인 기본 정보 조회
        campaign = db.query(models.Campaign).filter(
            models.Campaign.name == decoded_campaign_name,
            models.Campaign.campaign_type.in_(['instagram_post', 'instagram_reel', 'all'])
        ).first()
        
        if not campaign:
            # 디버깅을 위해 사용 가능한 캠페인 출력
            available_campaigns = db.query(models.Campaign.name).all()
            print(f"❌ 캠페인 '{decoded_campaign_name}'을 찾을 수 없습니다.")
            print(f"📋 사용 가능한 캠페인: {[c.name for c in available_campaigns]}")
            raise HTTPException(status_code=404, detail=f"Campaign '{decoded_campaign_name}' not found")
        
        # campaign_reel_collection_jobs에서 완료된 작업 조회
        collection_jobs = db.query(models.CampaignReelCollectionJob).filter(
            models.CampaignReelCollectionJob.campaign_id == campaign.id,
            models.CampaignReelCollectionJob.status == 'completed'
        ).order_by(models.CampaignReelCollectionJob.completed_at.desc()).all()
        
        print(f"📊 총 {len(collection_jobs)}개 수집 작업 완료됨")
        
        # 릴스 URL별로 그룹화 (같은 URL의 일자별 데이터)
        reel_data_by_url = defaultdict(list)
        for job in collection_jobs:
            reel_data_by_url[job.reel_url].append(job)
        
        print(f"🎬 고유 릴스 URL: {len(reel_data_by_url)}개")
        
        # 각 릴스 URL별로 데이터 구성
        reels_list = []
        username_grades = {}  # 사용자별 등급 캐시
        username_avg_views = {}  # 사용자별 평균 조회수 캐시
        
        for reel_url, jobs in reel_data_by_url.items():
            # 최신 작업 선택 (completed_at이 None인 경우 처리)
            valid_jobs = [j for j in jobs if j.completed_at is not None]
            if not valid_jobs:
                print(f"⚠️ 릴스 {reel_url}: 완료 시간이 없는 작업들, 첫 번째 작업 사용")
                latest_job = jobs[0]
            else:
                latest_job = max(valid_jobs, key=lambda j: j.completed_at)
            
            username = latest_job.user_posted
            
            # 인플루언서 프로필 조회
            profile = None
            display_name = username
            follower_count = 0
            
            if username:
                profile = db.query(models.InfluencerProfile).filter(
                    models.InfluencerProfile.username == username
                ).first()
                
                if profile:
                    display_name = profile.full_name or username
                    follower_count = profile.followers or 0
            
            # 사용자 등급 및 평균 조회수 계산 (캐시 사용)
            if username and username not in username_grades:
                grade_result = _calculate_influencer_grade_with_avg(db, username)
                if grade_result:
                    username_grades[username] = grade_result['grade']
                    username_avg_views[username] = grade_result['avg_views']
                    print(f"🏆 '{username}' 등급: {grade_result['grade']}, 평균 조회수: {grade_result['avg_views']:,.0f}, 팔로워: {follower_count:,}")
                else:
                    username_grades[username] = None
                    username_avg_views[username] = None
            
            # 일자별 조회수 데이터 구성
            view_history = []
            # completed_at이 있는 작업만 정렬
            jobs_with_date = [j for j in jobs if j.completed_at is not None]
            for job in sorted(jobs_with_date, key=lambda j: j.completed_at):
                if job.video_play_count is not None:
                    view_history.append({
                        'date': job.completed_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'views': job.video_play_count
                    })
            
            # 인플루언서 데이터에서 추가 정보 가져오기
            subscription_motivation = None
            category = None
            
            # reel_url에서 reel_id 추출
            reel_id = None
            if '/reel/' in reel_url:
                parts = reel_url.split('/reel/')
                if len(parts) > 1:
                    reel_id = parts[1].split('/')[0].split('?')[0]
            
            # 인플루언서 릴스 데이터에서 분류 정보 가져오기
            if reel_id and profile:
                influencer_reel = db.query(models.InfluencerReel).filter(
                    models.InfluencerReel.reel_id == reel_id,
                    models.InfluencerReel.profile_id == profile.id
                ).first()
                
                if influencer_reel:
                    subscription_motivation = influencer_reel.subscription_motivation
                    category = influencer_reel.category
            
            # 안전하게 job_metadata 접근
            posted_at = None
            if latest_job.job_metadata and isinstance(latest_job.job_metadata, dict):
                posted_at = latest_job.job_metadata.get('date_posted')
            
            reel_data = {
                'id': latest_job.id,
                'reel_id': reel_id or f"job_{latest_job.id}",
                'reel_url': reel_url,
                'username': username,
                'display_name': display_name,
                'follower_count': follower_count,
                's3_thumbnail_url': latest_job.s3_thumbnail_url,
                'video_view_count': latest_job.video_play_count or 0,
                'subscription_motivation': subscription_motivation,
                'category': category,
                'grade': username_grades.get(username) if username else None,
                'grade_avg_views': username_avg_views.get(username) if username else None,
                'product': campaign.product,
                'posted_at': posted_at,
                'collection_date': latest_job.completed_at,
                'campaign_url': reel_url,
                'data_source': 'campaign_collection',
                'view_history': view_history  # 일자별 조회수 이력
            }
            
            reels_list.append(reel_data)
            print(f"📝 릴스 추가: {reel_url} (조회수: {latest_job.video_play_count}, 등급: {reel_data['grade']})")
        
        print(f"🔄 최종 릴스 개수: {len(reels_list)}개")
        
        # 릴스별 일자별 조회수 차트 데이터 생성
        chart_data_by_reel = {}
        for reel in reels_list:
            if reel['view_history']:
                dates = [v['date'] for v in reel['view_history']]
                views = [v['views'] for v in reel['view_history']]
                chart_data_by_reel[reel['reel_url']] = {
                    'labels': dates,
                    'data': views
                }
        
        # 통계 계산
        total_views = sum(reel.get('video_view_count', 0) for reel in reels_list)
        avg_views = total_views / len(reels_list) if reels_list else 0
        
        # 등급별 분포
        grade_distribution = defaultdict(int)
        for reel in reels_list:
            grade = reel.get('grade', 'Unknown')
            grade_distribution[grade] += 1
        
        # 고유 사용자 수 계산
        unique_usernames = set(reel.get('username') for reel in reels_list if reel.get('username'))
        
        print(f"📊 최종 통계: 총 {len(reels_list)}개 릴스, {len(unique_usernames)}명 인플루언서")
        print(f"🎯 등급 분포: {dict(grade_distribution)}")
        
        return {
            'campaign': {
                'name': campaign.name,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'product': campaign.product,
                'budget': campaign.budget
            },
            'summary': {
                'total_reels': len(reels_list),
                'unique_influencers': len(unique_usernames),
                'total_views': total_views,
                'average_views': round(avg_views, 2),
                'grade_distribution': dict(grade_distribution)
            },
            'reels': reels_list,
            'chart_data_by_reel': chart_data_by_reel
        }
        
    except HTTPException:
        # HTTPException은 그대로 재발생
        raise
    except Exception as e:
        print(f"❌ 통합 보고서 조회 실패: {str(e)}")
        print(f"❌ 에러 타입: {type(e).__name__}")
        import traceback
        print("❌ 전체 스택 트레이스:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {type(e).__name__}: {str(e)}")

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