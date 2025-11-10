from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_
from typing import Any, Dict, List, Optional
from collections import defaultdict, Counter

from app.db.database import get_db
from app.db import models
from app.services.grade_service import instagram_grade_service

router = APIRouter()


def _calculate_influencer_grade(db: Session, username: str) -> Optional[str]:
    """
    사용자의 등급을 계산합니다.
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
    
    return grade


def _get_latest_reel_view_count(db: Session, reel_id: str, profile_id: int) -> int:
    """
    특정 릴스의 최신 조회수를 반환합니다.
    """
    reel = db.query(models.InfluencerReel).filter(
        models.InfluencerReel.reel_id == reel_id,
        models.InfluencerReel.profile_id == profile_id
    ).order_by(models.InfluencerReel.created_at.desc()).first()
    
    if not reel:
        return 0
    
    return reel.video_play_count or reel.views or 0


def _extract_reel_ids_from_campaign_urls(campaign_urls: List[models.CampaignURL]) -> set:
    """
    캠페인 URL에서 릴스 ID들을 추출합니다.
    """
    reel_ids = set()
    
    for campaign_url in campaign_urls:
        try:
            url = campaign_url.url.strip().rstrip('/')
            if '/reel/' in url:
                # 릴스 URL에서 릴스 ID 추출
                parts = url.split('/reel/')
                if len(parts) > 1:
                    reel_id = parts[1].split('/')[0].split('?')[0]
                    reel_ids.add(reel_id)
        except Exception:
            continue
    
    return reel_ids


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
        
        # 계정별 집계된 구독 동기/카테고리 조회 (aggregated-summary와 동일한 로직 사용)
        from app.services.influencer_service import InfluencerService
        from app.services.openai_service import OpenAIService
        from sqlalchemy import func
        influencer_service = InfluencerService(db)
        openai_service = OpenAIService(db)
        
        # 캠페인에 포함된 모든 사용자명 수집
        campaign_usernames = {reel.username for reel in campaign_reels if reel.username}
        
        # 각 계정별 집계 결과 조회
        account_classifications = {}
        for username in campaign_usernames:
            profile = db.query(models.InfluencerProfile).filter(
                models.InfluencerProfile.username == username
            ).first()
            
            if profile:
                account_motivation = None
                account_category = None
                
                # 1순위: InfluencerClassificationSummary 테이블 기반 집계 (aggregated-summary와 동일)
                try:
                    # 최신 job_id 조회
                    motivation_job_id = db.query(
                        func.max(models.InfluencerReel.subscription_motivation_job_id)
                    ).filter(
                        models.InfluencerReel.profile_id == profile.id
                    ).scalar()
                    
                    category_job_id = db.query(
                        func.max(models.InfluencerReel.category_job_id)
                    ).filter(
                        models.InfluencerReel.profile_id == profile.id
                    ).scalar()
                    
                    # 구독 동기 집계
                    try:
                        has_motivation_summary = False
                        if motivation_job_id is not None:
                            has_motivation_summary = True
                        else:
                            summary_check = db.query(models.InfluencerClassificationSummary.id).filter(
                                models.InfluencerClassificationSummary.profile_id == profile.id,
                                models.InfluencerClassificationSummary.motivation.isnot(None)
                            ).first()
                            has_motivation_summary = summary_check is not None
                        
                        if has_motivation_summary:
                            motivation_summary = openai_service.aggregate_classification_results(
                                username,
                                motivation_job_id,
                                "subscription_motivation"
                            )
                            if motivation_summary and not motivation_summary.get("error"):
                                account_motivation = motivation_summary.get("primary_classification")
                    except Exception as e:
                        print(f"⚠️ '{username}' 구독 동기 집계 실패: {str(e)}")
                    
                    # 카테고리 집계
                    try:
                        has_category_summary = False
                        if category_job_id is not None:
                            has_category_summary = True
                        else:
                            summary_check = db.query(models.InfluencerClassificationSummary.id).filter(
                                models.InfluencerClassificationSummary.profile_id == profile.id,
                                models.InfluencerClassificationSummary.category.isnot(None)
                            ).first()
                            has_category_summary = summary_check is not None
                        
                        if has_category_summary:
                            category_summary = openai_service.aggregate_classification_results(
                                username,
                                category_job_id,
                                "category"
                            )
                            if category_summary and not category_summary.get("error"):
                                account_category = category_summary.get("primary_classification")
                    except Exception as e:
                        print(f"⚠️ '{username}' 카테고리 집계 실패: {str(e)}")
                except Exception as e:
                    import traceback
                    print(f"⚠️ '{username}' 집계 결과 조회 실패: {str(e)}")
                    traceback.print_exc()
                
                # 2순위: InfluencerAnalysis 테이블 사용 (집계 결과가 없을 경우)
                if not account_motivation:
                    motivation_analysis = influencer_service.get_analysis_result(
                        profile.id, 
                        "subscription_motivation"
                    )
                    if motivation_analysis and motivation_analysis.analysis_result:
                        result = motivation_analysis.analysis_result
                        if isinstance(result, dict):
                            account_motivation = (
                                result.get("primary_motivation") or 
                                result.get("primary_classification") or 
                                result.get("classification")
                            )
                
                if not account_category:
                    category_analysis = influencer_service.get_analysis_result(
                        profile.id, 
                        "category"
                    )
                    if category_analysis and category_analysis.analysis_result:
                        result = category_analysis.analysis_result
                        if isinstance(result, dict):
                            account_category = (
                                result.get("primary_category") or 
                                result.get("primary_classification") or 
                                result.get("classification")
                            )
                
                account_classifications[username] = {
                    'motivation': account_motivation,
                    'category': account_category
                }
        
        # 릴스 데이터 리스트 생성 (집계 결과 우선 사용)
        reels_list = []
        for reel in campaign_reels:
            # 집계 결과가 있으면 우선 사용, 없으면 개별 릴스 데이터 사용
            account_data = account_classifications.get(reel.username, {})
            reel_motivation = account_data.get('motivation') or reel.subscription_motivation
            reel_category = account_data.get('category') or reel.category
            
            reels_list.append({
                'id': reel.id,
                'reel_id': reel.reel_id,
                'username': reel.username,
                'display_name': reel.display_name,
                'follower_count': reel.follower_count,
                's3_thumbnail_url': reel.s3_thumbnail_url,
                'video_view_count': reel.video_view_count,
                'likes_count': getattr(reel, 'likes_count', None),
                'comments_count': getattr(reel, 'comments_count', None),
                'subscription_motivation': reel_motivation,  # 집계 결과 우선 사용
                'category': reel_category,  # 집계 결과 우선 사용
                'grade': reel.grade,
                'product': reel.product,
                'posted_at': reel.posted_at,
                'collection_date': reel.collection_date,
                'campaign_url': reel.campaign_url
            })
        
        # 각 계정별 구독 동기 상위 1위 계산 (집계 결과 우선 사용)
        # InfluencerAnalysis 테이블의 집계 결과를 우선 사용하므로, 이미 account_classifications에 저장됨
        # 각 릴스 데이터에 계정별 구독 동기 추가
        for reel in reels_list:
            username = reel.get('username')
            account_data = account_classifications.get(username, {})
            # 집계 결과의 구독 동기를 우선 사용 (이미 reel_motivation에 반영됨)
            reel['account_subscription_motivation'] = account_data.get('motivation') or reel.get('subscription_motivation')
        
        return {
            'campaign': {
                'name': campaign.name,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'product': campaign.product,
                'budget': campaign.budget
            },
            'unique_reel_count': unique_campaign_urls,
            'reels': reels_list,
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
    """인스타그램 릴스 보고서 데이터 - 기존 캠페인 데이터와 인플루언서 수집 데이터 통합"""
    try:
        # 캠페인 정보 조회
        campaign = db.query(models.Campaign).filter(
            models.Campaign.name == campaign_name,
            models.Campaign.campaign_type.in_(['instagram_reel', 'instagram_post', 'all'])
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 1. 기존 캠페인 시스템 데이터 조회
        campaign_reels = db.query(models.CampaignInstagramReel).filter(
            and_(
                models.CampaignInstagramReel.campaign_id == campaign.id,
                models.CampaignInstagramReel.collection_date >= campaign.start_date,
                models.CampaignInstagramReel.collection_date <= campaign.end_date
            )
        ).all()
        
        # 2. 인플루언서 시스템 데이터 조회 (즉시 연결)
        influencer_reels = []
        
        # 기존 캠페인 릴스에서 사용자명 수집
        campaign_usernames = set()
        for reel in campaign_reels:
            if reel.username:
                campaign_usernames.add(reel.username)
        
        # 캠페인 URL 조회
        campaign_urls = db.query(models.CampaignURL).filter(
            models.CampaignURL.campaign_id == campaign.id,
            models.CampaignURL.channel.in_(['instagram_reel', 'instagram_post'])
        ).all()
        
        # 캠페인 URL에서 릴스 ID 추출
        campaign_reel_ids = _extract_reel_ids_from_campaign_urls(campaign_urls)
        print(f"🎬 캠페인 URL에서 추출한 릴스 ID {len(campaign_reel_ids)}개: {list(campaign_reel_ids)[:5]}")
        
        # 캠페인 URL에서 추가 사용자명 추출
        for campaign_url in campaign_urls:
            try:
                url = campaign_url.url.strip().rstrip('/')
                if 'instagram.com/' in url:
                    if '/reel/' in url or '/p/' in url:
                        # 릴스/게시물 URL에서는 사용자명을 직접 추출할 수 없으므로 스킵
                        continue
                    else:
                        # 프로필 URL에서 사용자명 추출
                        url_parts = url.split('instagram.com/')[-1].split('/')
                        username = url_parts[0].split('?')[0]
                        if username not in ['reel', 'p', 'tv', 'stories']:
                            campaign_usernames.add(username)
            except Exception:
                continue
        
        print(f"🔍 캠페인 '{campaign_name}' 사용자명 {len(campaign_usernames)}개: {list(campaign_usernames)}")
        
        # 각 사용자명에 대해 인플루언서 데이터 조회
        for username in campaign_usernames:
            try:
                print(f"🎯 사용자명 '{username}'로 인플루언서 데이터 검색")
                
                # 인플루언서 프로필 조회 (정확한 매칭)
                influencer_profile = db.query(models.InfluencerProfile).filter(
                    models.InfluencerProfile.username == username
                ).first()
                
                if influencer_profile:
                    print(f"✅ 인플루언서 프로필 발견: {influencer_profile.username}")
                    
                    # 계정별 집계된 구독 동기/카테고리 조회 (aggregated-summary와 동일한 로직 사용)
                    from app.services.influencer_service import InfluencerService
                    from app.services.openai_service import OpenAIService
                    from sqlalchemy import func
                    influencer_service = InfluencerService(db)
                    openai_service = OpenAIService(db)
                    
                    # aggregated-summary와 동일한 우선순위로 집계 결과 조회
                    account_motivation = None
                    account_category = None
                    
                    # 1순위: InfluencerClassificationSummary 테이블 기반 집계 (aggregated-summary와 동일)
                    try:
                        # 최신 job_id 조회 (aggregated-summary와 동일한 로직)
                        motivation_job_id = db.query(
                            func.max(models.InfluencerReel.subscription_motivation_job_id)
                        ).filter(
                            models.InfluencerReel.profile_id == influencer_profile.id
                        ).scalar()
                        
                        category_job_id = db.query(
                            func.max(models.InfluencerReel.category_job_id)
                        ).filter(
                            models.InfluencerReel.profile_id == influencer_profile.id
                        ).scalar()
                        
                        # 구독 동기 집계 (최신 job_id 사용)
                        try:
                            has_motivation_summary = False
                            if motivation_job_id is not None:
                                has_motivation_summary = True
                            else:
                                summary_check = db.query(models.InfluencerClassificationSummary.id).filter(
                                    models.InfluencerClassificationSummary.profile_id == influencer_profile.id,
                                    models.InfluencerClassificationSummary.motivation.isnot(None)
                                ).first()
                                has_motivation_summary = summary_check is not None
                            
                            if has_motivation_summary:
                                motivation_summary = openai_service.aggregate_classification_results(
                                    username,
                                    motivation_job_id,
                                    "subscription_motivation"
                                )
                                if motivation_summary and not motivation_summary.get("error"):
                                    account_motivation = motivation_summary.get("primary_classification")
                        except Exception as e:
                            print(f"⚠️ '{username}' 구독 동기 집계 실패: {str(e)}")
                        
                        # 카테고리 집계 (최신 job_id 사용)
                        try:
                            has_category_summary = False
                            if category_job_id is not None:
                                has_category_summary = True
                            else:
                                summary_check = db.query(models.InfluencerClassificationSummary.id).filter(
                                    models.InfluencerClassificationSummary.profile_id == influencer_profile.id,
                                    models.InfluencerClassificationSummary.category.isnot(None)
                                ).first()
                                has_category_summary = summary_check is not None
                            
                            if has_category_summary:
                                category_summary = openai_service.aggregate_classification_results(
                                    username,
                                    category_job_id,
                                    "category"
                                )
                                if category_summary and not category_summary.get("error"):
                                    account_category = category_summary.get("primary_classification")
                        except Exception as e:
                            print(f"⚠️ '{username}' 카테고리 집계 실패: {str(e)}")
                    except Exception as e:
                        import traceback
                        print(f"⚠️ '{username}' 집계 결과 조회 실패: {str(e)}")
                        traceback.print_exc()
                    
                    # 2순위: InfluencerAnalysis 테이블 사용 (집계 결과가 없을 경우)
                    if not account_motivation:
                        motivation_analysis = influencer_service.get_analysis_result(
                            influencer_profile.id, 
                            "subscription_motivation"
                        )
                        if motivation_analysis and motivation_analysis.analysis_result:
                            result = motivation_analysis.analysis_result
                            if isinstance(result, dict):
                                account_motivation = (
                                    result.get("primary_motivation") or 
                                    result.get("primary_classification") or 
                                    result.get("classification")
                                )
                    
                    if not account_category:
                        category_analysis = influencer_service.get_analysis_result(
                            influencer_profile.id, 
                            "category"
                        )
                        if category_analysis and category_analysis.analysis_result:
                            result = category_analysis.analysis_result
                            if isinstance(result, dict):
                                account_category = (
                                    result.get("primary_category") or 
                                    result.get("primary_classification") or 
                                    result.get("classification")
                                )
                    
                    print(f"📊 '{username}' 집계 결과 - 구독동기: {account_motivation}, 카테고리: {account_category}")
                    
                    # 해당 프로필의 모든 릴스 조회 (최신순)
                    profile_reels = db.query(models.InfluencerReel).filter(
                        models.InfluencerReel.profile_id == influencer_profile.id
                    ).order_by(models.InfluencerReel.created_at.desc()).all()
                    
                    print(f"📱 '{influencer_profile.username}' 릴스 개수: {len(profile_reels)}")
                    
                    # 사용자의 등급 계산 (24개 릴스 평균 조회수 기준)
                    user_grade = _calculate_influencer_grade(db, username)
                    print(f"🏆 '{username}' 등급: {user_grade}")
                    
                    if profile_reels:
                        # 실제 릴스 데이터가 있는 경우
                        # 캠페인 URL에 특정 릴스 ID가 있으면 그것만 포함, 없으면 모든 릴스 포함
                        reels_to_include = []
                        if campaign_reel_ids:
                            # 특정 릴스 ID들이 지정된 경우
                            reels_to_include = [r for r in profile_reels if r.reel_id in campaign_reel_ids]
                            if not reels_to_include:
                                # 지정된 릴스 ID가 없으면 모든 릴스 포함
                                reels_to_include = profile_reels
                        else:
                            # 지정된 릴스 ID가 없으면 모든 릴스 포함
                            reels_to_include = profile_reels
                        
                        for reel in reels_to_include:
                            # 최신 조회수 조회
                            latest_view_count = _get_latest_reel_view_count(db, reel.reel_id, influencer_profile.id)
                            
                            # 구독 동기/카테고리는 집계 결과를 우선 사용, 없으면 개별 릴스 데이터 사용
                            reel_motivation = account_motivation or reel.subscription_motivation
                            reel_category = account_category or reel.category
                            
                            reel_data = {
                                'id': f"influencer_{reel.id}",
                                'reel_id': reel.reel_id,
                                'username': influencer_profile.username,
                                'display_name': influencer_profile.full_name or influencer_profile.username,
                                'follower_count': influencer_profile.followers or 0,
                                's3_thumbnail_url': reel.media_urls[0] if reel.media_urls else None,
                                'video_view_count': latest_view_count,
                                'likes_count': reel.likes_count,
                                'comments_count': reel.comments_count,
                                'subscription_motivation': reel_motivation,  # 집계 결과 우선 사용
                                'category': reel_category,  # 집계 결과 우선 사용
                                'grade': user_grade or 'C',  # 등급 계산 결과 사용
                                'product': campaign.product,
                                'posted_at': reel.timestamp,
                                'collection_date': reel.created_at,
                                'campaign_url': f"https://www.instagram.com/reel/{reel.reel_id}/",
                                'data_source': 'influencer'
                            }
                            influencer_reels.append(reel_data)
                            print(f"📝 릴스 추가: {reel.reel_id} (조회수: {latest_view_count}, 구독동기: {reel_motivation}, 카테고리: {reel_category})")
                    else:
                        # 릴스가 아직 수집되지 않았지만 프로필은 있는 경우 - 스킵
                        print(f"⚠️ '{username}' 프로필은 있지만 릴스 데이터가 없음 - 스킵")
                else:
                    print(f"❌ 인플루언서 프로필을 찾을 수 없음: '{username}'")
            except Exception as e:
                print(f"❌ 사용자명 처리 실패: {username} - {str(e)}")
                continue
        
        # 3. 데이터 우선순위 통합 (reel_id 기준 중복 제거, 인플루언서 데이터 우선)
        all_reels = []
        
        # 인플루언서 데이터를 우선으로 추가 (최신 데이터)
        all_reels.extend(influencer_reels)
        print(f"📊 인플루언서 데이터 추가됨: {len(influencer_reels)}개")
        
        # 기존 캠페인 데이터는 reel_id가 중복되지 않는 경우에만 추가
        added_reel_ids = {reel['reel_id'] for reel in influencer_reels if reel.get('reel_id')}
        
        for reel in campaign_reels:
            # reel_id가 이미 추가되지 않은 경우에만 추가
            if reel.reel_id and reel.reel_id not in added_reel_ids:
                # 등급 재계산
                campaign_grade = _calculate_influencer_grade(db, reel.username) if reel.username else None
                
                all_reels.append({
                    'id': f"campaign_{reel.id}",
                    'reel_id': reel.reel_id,
                    'username': reel.username,
                    'display_name': reel.display_name,
                    'follower_count': reel.follower_count,
                    's3_thumbnail_url': reel.s3_thumbnail_url,
                    'video_view_count': reel.video_view_count,
                    'subscription_motivation': reel.subscription_motivation,
                    'category': reel.category,
                    'grade': campaign_grade or reel.grade,  # 재계산된 등급 사용
                    'product': reel.product,
                    'posted_at': reel.posted_at,
                    'collection_date': reel.collection_date,
                    'campaign_url': reel.campaign_url,
                    'data_source': 'campaign'
                })
                added_reel_ids.add(reel.reel_id)
                print(f"📝 캠페인 릴스 추가: {reel.reel_id} (등급: {campaign_grade or reel.grade})")
        
        print(f"📈 총 릴스 데이터: {len(all_reels)}개 (인플루언서: {len(influencer_reels)}, 캠페인 추가: {len(campaign_reels)}, 실제 추가된 총: {len(all_reels)})")
        
        # 3.5. 각 계정별 구독 동기 상위 1위 계산 (집계 결과 우선 사용)
        # InfluencerAnalysis 테이블의 집계 결과를 이미 사용했으므로, account_subscription_motivation은 subscription_motivation과 동일
        # 각 릴스 데이터에 계정별 구독 동기 추가 (이미 집계 결과가 반영된 subscription_motivation 사용)
        for reel in all_reels:
            # 집계 결과가 이미 subscription_motivation에 반영되었으므로 동일하게 사용
            reel['account_subscription_motivation'] = reel.get('subscription_motivation')
        
        # 4. 날짜별 비디오 조회 수 집계 (통합 데이터)
        view_data = {}
        for reel in all_reels:
            collection_date = reel.get('collection_date')
            if collection_date:
                if hasattr(collection_date, 'strftime'):
                    date_key = collection_date.strftime('%Y-%m-%d')
                else:
                    date_key = str(collection_date)[:10]  # YYYY-MM-DD 형식으로 자르기
                
                if date_key not in view_data:
                    view_data[date_key] = 0
                view_data[date_key] += (reel.get('video_view_count') or 0)
        
        # 5. 차트 데이터 생성 (날짜순 정렬)
        sorted_dates = sorted(view_data.keys())
        chart_data = {
            'labels': sorted_dates,
            'data': [view_data[date] for date in sorted_dates]
        }
        
        # 6. 고유 릴스 개수 계산 (reel_id 기준)
        unique_reel_ids = set()
        for reel in all_reels:
            if reel.get('reel_id'):
                unique_reel_ids.add(reel['reel_id'])
        
        print(f"🎯 고유 릴스 개수: {len(unique_reel_ids)}개")
        
        return {
            'campaign': {
                'name': campaign.name,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'product': campaign.product,
                'budget': campaign.budget
            },
            'unique_reel_count': len(unique_reel_ids),  # reel_id 기준으로 계산
            'total_reels': len(all_reels),
            'campaign_reels': len(campaign_reels),
            'influencer_reels': len(influencer_reels),
            'reels': all_reels,
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
    """사용 가능한 캠페인 목록 - 실제 데이터가 수집된 캠페인만 반환"""
    
    # 기존 캠페인 시스템에서 수집된 데이터가 있는 캠페인들
    campaigns_with_reels = db.query(models.CampaignInstagramReel.campaign_id).distinct().subquery()
    campaigns_with_posts = db.query(models.CampaignInstagramPost.campaign_id).distinct().subquery()
    campaigns_with_blogs = db.query(models.CampaignBlog.campaign_id).distinct().subquery()
    
    # 인플루언서 분석 시스템에서 데이터가 수집된 캠페인 찾기
    campaigns_with_influencer_data = []
    
    # 모든 캠페인 확인
    campaigns = db.query(models.Campaign).all()
    for campaign in campaigns:
        # 1. 기존 캠페인 릴스에서 사용자명 수집
        campaign_usernames = set()
        campaign_reels = db.query(models.CampaignInstagramReel).filter(
            models.CampaignInstagramReel.campaign_id == campaign.id
        ).all()
        
        for reel in campaign_reels:
            if reel.username:
                campaign_usernames.add(reel.username)
        
        # 2. 캠페인 URL에서 추가 사용자명 추출
        campaign_urls = db.query(models.CampaignURL).filter(
            models.CampaignURL.campaign_id == campaign.id,
            models.CampaignURL.channel.in_(['instagram_reel', 'instagram_post'])
        ).all()
        
        for campaign_url in campaign_urls:
            try:
                url = campaign_url.url.strip().rstrip('/')
                if 'instagram.com/' in url:
                    if '/reel/' not in url and '/p/' not in url:
                        # 프로필 URL에서만 사용자명 추출
                        username = url.split('instagram.com/')[-1].split('/')[0].split('?')[0]
                        if username not in ['reel', 'p', 'tv', 'stories']:
                            campaign_usernames.add(username)
            except Exception:
                continue
        
        # 3. 각 사용자명에 대해 인플루언서 프로필 확인
        for username in campaign_usernames:
            try:
                influencer_profile = db.query(models.InfluencerProfile).filter(
                    models.InfluencerProfile.username == username
                ).first()
                
                if influencer_profile:
                    # 실제 릴스 데이터가 있는지 확인 (프로필만으로는 부족)
                    has_reels = db.query(models.InfluencerReel).filter(
                        models.InfluencerReel.profile_id == influencer_profile.id
                    ).first() is not None
                    
                    if has_reels:
                        campaigns_with_influencer_data.append(campaign.id)
                        print(f"✅ 캠페인 '{campaign.name}'에 인플루언서 릴스 데이터 발견: {username}")
                        break
            except Exception:
                continue
    
    # 실제 데이터가 수집된 캠페인들만 조회
    all_campaign_ids = set()
    
    # 기존 캠페인 시스템 데이터
    for subquery in [campaigns_with_reels, campaigns_with_posts, campaigns_with_blogs]:
        campaign_ids = db.execute(
            db.query(subquery.c.campaign_id)
        ).scalars().all()
        all_campaign_ids.update(campaign_ids)
    
    # 인플루언서 시스템 데이터
    all_campaign_ids.update(campaigns_with_influencer_data)
    
    if not all_campaign_ids:
        return []
    
    filtered_campaigns = db.query(models.Campaign).filter(
        models.Campaign.id.in_(all_campaign_ids)
    ).all()
    
    result = []
    for campaign in filtered_campaigns:
        # 각 캠페인별 수집된 데이터 타입 확인
        has_reels = db.query(models.CampaignInstagramReel).filter(
            models.CampaignInstagramReel.campaign_id == campaign.id
        ).first() is not None
        
        has_posts = db.query(models.CampaignInstagramPost).filter(
            models.CampaignInstagramPost.campaign_id == campaign.id
        ).first() is not None
        
        has_blogs = db.query(models.CampaignBlog).filter(
            models.CampaignBlog.campaign_id == campaign.id
        ).first() is not None
        
        # 인플루언서 릴스 데이터도 확인
        has_influencer_reels = campaign.id in campaigns_with_influencer_data
        
        result.append({
            'id': campaign.id,
            'name': campaign.name,
            'campaign_type': campaign.campaign_type,
            'start_date': campaign.start_date,
            'end_date': campaign.end_date,
            'product': campaign.product,
            'has_reels': has_reels or has_influencer_reels,
            'has_posts': has_posts,
            'has_blogs': has_blogs,
            'has_influencer_data': has_influencer_reels
        })
    
    return result
