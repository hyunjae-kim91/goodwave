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
        
        # 캠페인 URL에서 추가 사용자명 추출
        campaign_urls = db.query(models.CampaignURL).filter(
            models.CampaignURL.campaign_id == campaign.id,
            models.CampaignURL.channel.in_(['instagram_reel', 'instagram_post'])
        ).all()
        
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
                    
                    # 해당 프로필의 모든 릴스 조회 (최신순)
                    profile_reels = db.query(models.InfluencerReel).filter(
                        models.InfluencerReel.profile_id == influencer_profile.id
                    ).order_by(models.InfluencerReel.created_at.desc()).all()
                    
                    print(f"📱 '{influencer_profile.username}' 릴스 개수: {len(profile_reels)}")
                    
                    if profile_reels:
                        # 실제 릴스 데이터가 있는 경우
                        for reel in profile_reels:
                            reel_data = {
                                'id': f"influencer_{reel.id}",
                                'reel_id': reel.reel_id,
                                'username': influencer_profile.username,
                                'display_name': influencer_profile.full_name or influencer_profile.username,
                                'follower_count': influencer_profile.followers or 0,
                                's3_thumbnail_url': reel.media_urls[0] if reel.media_urls else None,
                                'video_view_count': reel.views or reel.video_play_count or 0,
                                'subscription_motivation': None,
                                'category': None,
                                'grade': 'A' if (influencer_profile.followers or 0) >= 100000 else 'B' if (influencer_profile.followers or 0) >= 10000 else 'C',
                                'product': campaign.product,
                                'posted_at': reel.timestamp,
                                'collection_date': reel.created_at,
                                'campaign_url': f"https://www.instagram.com/{username}/",
                                'data_source': 'influencer'
                            }
                            influencer_reels.append(reel_data)
                            print(f"📝 릴스 추가: {reel.reel_id} (조회수: {reel_data['video_view_count']})")
                    else:
                        # 릴스가 아직 수집되지 않았지만 프로필은 있는 경우 - 플레이스홀더 생성
                        placeholder_reel = {
                            'id': f"influencer_profile_{influencer_profile.id}",
                            'reel_id': f"profile_{influencer_profile.username}",
                            'username': influencer_profile.username,
                            'display_name': influencer_profile.full_name or influencer_profile.username,
                            'follower_count': influencer_profile.followers or 0,
                            's3_thumbnail_url': None,
                            'video_view_count': 0,
                            'subscription_motivation': None,
                            'category': None,
                            'grade': 'A' if (influencer_profile.followers or 0) >= 100000 else 'B' if (influencer_profile.followers or 0) >= 10000 else 'C',
                            'product': campaign.product,
                            'posted_at': influencer_profile.created_at,
                            'collection_date': influencer_profile.created_at,
                            'campaign_url': f"https://www.instagram.com/{username}/",
                            'data_source': 'influencer_profile'  # 프로필만 있음을 표시
                        }
                        influencer_reels.append(placeholder_reel)
                        print(f"📝 프로필 플레이스홀더 추가: {influencer_profile.username} (팔로워: {influencer_profile.followers or 0})")
                else:
                    print(f"❌ 인플루언서 프로필을 찾을 수 없음: '{username}'")
            except Exception as e:
                print(f"❌ 사용자명 처리 실패: {username} - {str(e)}")
                continue
        
        # 3. 데이터 우선순위 통합 (인플루언서 데이터 우선)
        all_reels = []
        
        # 인플루언서 데이터를 우선으로 추가 (최신 데이터)
        all_reels.extend(influencer_reels)
        print(f"📊 인플루언서 데이터 추가됨: {len(influencer_reels)}개")
        
        # 기존 캠페인 데이터는 인플루언서 데이터가 없는 경우에만 추가
        campaign_usernames = {reel['username'] for reel in influencer_reels}
        for reel in campaign_reels:
            if reel.username not in campaign_usernames:
                all_reels.append({
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
                    'campaign_url': reel.campaign_url,
                    'data_source': 'campaign'
                })
        
        print(f"📈 총 릴스 데이터: {len(all_reels)}개 (인플루언서: {len(influencer_reels)}, 캠페인: {len(campaign_reels)})")
        
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
        
        # 6. 고유 URL 개수 계산
        unique_urls = set()
        for reel in all_reels:
            if reel.get('campaign_url'):
                unique_urls.add(reel['campaign_url'])
        
        return {
            'campaign': {
                'name': campaign.name,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'product': campaign.product,
                'budget': campaign.budget
            },
            'unique_reel_count': len(unique_urls),
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
