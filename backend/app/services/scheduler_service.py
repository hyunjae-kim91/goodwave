import asyncio
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import SessionLocal
import re
from collections import Counter
from app.db import models
from app.services.instagram_service import instagram_service
from app.services.blog_service import blog_service
from app.services.openai_service import OpenAIService
from app.services.grade_service import instagram_grade_service
from app.core.config import settings

KST_OFFSET = timedelta(hours=9)

def now_kst() -> datetime:
    """한국 시간(KST) 기준 현재 시간 반환"""
    return datetime.utcnow() + KST_OFFSET

class SchedulerService:
    def __init__(self):
        self.db = SessionLocal()
        self.openai_service = OpenAIService(self.db)
        instagram_grade_service.ensure_default_thresholds(self.db)

    @staticmethod
    def _is_reel_url(url: str) -> bool:
        if not url:
            return False
        lowered = url.lower()
        return "/reel/" in lowered or "/reels/" in lowered

    def _ensure_reel_channel(self, schedule: models.CollectionSchedule) -> None:
        """스케줄 및 관련 URL의 채널을 릴스로 정규화"""
        updated = False

        if schedule.channel != 'instagram_reel':
            schedule.channel = 'instagram_reel'
            updated = True

        campaign_url = (
            self.db.query(models.CampaignURL)
            .filter(
                models.CampaignURL.campaign_id == schedule.campaign_id,
                models.CampaignURL.url == schedule.campaign_url,
            )
            .first()
        )

        if campaign_url and campaign_url.channel != 'instagram_reel':
            campaign_url.channel = 'instagram_reel'
            updated = True

        if updated:
            self.db.flush()

    async def run_scheduled_collection(self):
        """정기 수집 실행 - 각 스케줄의 설정된 시간(시)에 맞는 것만 실행"""
        try:
            current_time = now_kst()
            current_hour = current_time.hour
            print(f"Starting scheduled collection at {current_time} (KST) - checking for schedules at {current_hour:02d}:00")
            
            # 활성 스케줄 조회 (오늘 날짜가 수집 기간 내에 있는 것만) - 한국 시간 기준
            today = current_time.date()
            active_schedules = self.db.query(models.CollectionSchedule).filter(
                models.CollectionSchedule.is_active == True,
                models.CollectionSchedule.start_date.cast(models.Date) <= today,
                models.CollectionSchedule.end_date.cast(models.Date) >= today
            ).all()
            
            print(f"Found {len(active_schedules)} active schedules")
            
            # 각 스케줄의 설정된 시간(시)과 현재 시간(시)이 일치하는 것만 처리
            processed_count = 0
            skipped_count = 0
            
            for schedule in active_schedules:
                try:
                    # 스케줄 시간 확인 (기본값 9시)
                    schedule_hour = schedule.schedule_hour if hasattr(schedule, 'schedule_hour') and schedule.schedule_hour is not None else 9
                    
                    # 현재 시간(시)이 스케줄 시간(시)과 일치하는지 확인
                    if current_hour == schedule_hour:
                        print(f"✅ Schedule {schedule.id} matches current hour ({schedule_hour:02d}:00) - processing")
                        await self._process_schedule(schedule)
                        # 각 스케줄 처리 후 즉시 커밋하여 다음 스케줄의 중복 체크가 정확히 작동하도록 함
                        self.db.commit()
                        processed_count += 1
                    else:
                        skipped_count += 1
                        print(f"⏭️  Schedule {schedule.id} scheduled for {schedule_hour:02d}:00 - skipping (current: {current_hour:02d}:00)")
                except Exception as e:
                    print(f"Error processing schedule {schedule.id}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self.db.rollback()
                    continue
            
            print(f"Scheduled collection completed: {processed_count} processed, {skipped_count} skipped at {now_kst()} (KST)")
            
        except Exception as e:
            print(f"Error in scheduled collection: {str(e)}")
        finally:
            self.db.close()

    async def _process_schedule(self, schedule: models.CollectionSchedule):
        """개별 스케줄 처리"""
        campaign = schedule.campaign
        collection_date = now_kst()  # 한국 시간 기준
        today = collection_date.date()
        
        print(f"Processing schedule for campaign: {campaign.name}, channel: {schedule.channel}, date: {today} (KST)")
        
        # 이전 스케줄에서 커밋된 데이터를 반영하기 위해 flush
        self.db.flush()
        
        # 오늘 날짜에 이미 수집된 데이터가 있는지 확인
        if schedule.channel in ['instagram_post', 'instagram_reel']:
            # 릴스/포스트의 경우, 오늘 날짜에 이미 수집된 데이터가 있는지 확인
            if schedule.channel == 'instagram_reel' or (schedule.channel == 'instagram_post' and self._is_reel_url(schedule.campaign_url)):
                existing_today = self.db.query(models.CampaignInstagramReel).filter(
                    models.CampaignInstagramReel.campaign_id == campaign.id,
                    models.CampaignInstagramReel.campaign_url == schedule.campaign_url,
                    models.CampaignInstagramReel.collection_date >= datetime.combine(today, time.min),
                    models.CampaignInstagramReel.collection_date < datetime.combine(today + timedelta(days=1), time.min)
                ).first()
                
                if existing_today:
                    print(f"⚠️ 오늘({today}) 이미 수집된 데이터가 있습니다. 스킵합니다.")
                    return
            else:
                # 포스트의 경우 (릴스가 아닌 경우)
                existing_today = self.db.query(models.CampaignInstagramPost).filter(
                    models.CampaignInstagramPost.campaign_id == campaign.id,
                    models.CampaignInstagramPost.campaign_url == schedule.campaign_url,
                    models.CampaignInstagramPost.collection_date >= datetime.combine(today, time.min),
                    models.CampaignInstagramPost.collection_date < datetime.combine(today + timedelta(days=1), time.min)
                ).first()
                
                if existing_today:
                    print(f"⚠️ 오늘({today}) 이미 수집된 데이터가 있습니다. 스킵합니다.")
                    return
        elif schedule.channel == 'blog':
            # 블로그의 경우, 오늘 날짜에 이미 수집된 데이터가 있는지 확인
            existing_today = self.db.query(models.CampaignBlog).filter(
                models.CampaignBlog.campaign_id == campaign.id,
                models.CampaignBlog.campaign_url == schedule.campaign_url,
                models.CampaignBlog.collection_date >= datetime.combine(today, time.min),
                models.CampaignBlog.collection_date < datetime.combine(today + timedelta(days=1), time.min)
            ).first()
            
            if existing_today:
                print(f"⚠️ 오늘({today}) 이미 수집된 데이터가 있습니다. 스킵합니다.")
                return
        
        print(f"✅ 오늘({today}) 수집 시작")
        
        if schedule.channel == 'instagram_post':
            if self._is_reel_url(schedule.campaign_url):
                self._ensure_reel_channel(schedule)
                await self._collect_campaign_instagram_reels(schedule, campaign, collection_date)
            else:
                await self._collect_campaign_instagram_posts(schedule, campaign, collection_date)
        elif schedule.channel == 'instagram_reel':
            await self._collect_campaign_instagram_reels(schedule, campaign, collection_date)
        elif schedule.channel == 'blog':
            await self._collect_campaign_blogs(schedule, campaign, collection_date)

    async def _collect_campaign_instagram_posts(
        self, 
        schedule: models.CollectionSchedule, 
        campaign: models.Campaign, 
        collection_date: datetime
    ):
        """캠페인 인스타그램 게시물 수집"""
        try:
            post_data = await instagram_service.collect_instagram_post_data(schedule.campaign_url)
            if not post_data:
                print(f"No Instagram post data collected for {schedule.campaign_url}")
                return
            
            # 사용자 게시물들 수집
            username = post_data.get('username')
            if not username:
                print(f"Instagram post lacks username for {schedule.campaign_url}")
                return
            user_posts = await instagram_service.collect_user_posts_thumbnails(username, 24)
            if not user_posts:
                user_posts = [post_data]
            
            # 캠페인 테이블에 저장
            for post in user_posts:
                db_campaign_post = models.CampaignInstagramPost(
                    campaign_id=campaign.id,
                    campaign_url=schedule.campaign_url,
                    post_id=post['post_id'],
                    username=post['username'],
                    display_name=post.get('display_name'),
                    follower_count=post.get('follower_count', 0),
                    thumbnail_url=post.get('thumbnail_url'),
                    s3_thumbnail_url=post.get('s3_thumbnail_url'),
                    likes_count=post.get('likes_count', 0),
                    comments_count=post.get('comments_count', 0),
                    subscription_motivation=post.get('subscription_motivation'),
                    category=post.get('category'),
                    grade=post.get('grade'),
                    product=campaign.product,
                    posted_at=post.get('posted_at'),
                    collection_date=collection_date
                )
                self.db.add(db_campaign_post)
            
            # 커밋은 상위 메서드에서 처리하므로 여기서는 flush만 수행
            self.db.flush()
            print(f"Collected {len(user_posts)} Instagram posts for campaign {campaign.name}")
            
        except Exception as e:
            print(f"Error collecting campaign Instagram posts: {str(e)}")
            self.db.rollback()

    async def _collect_campaign_instagram_reels(
        self, 
        schedule: models.CollectionSchedule, 
        campaign: models.Campaign, 
        collection_date: datetime
    ):
        """캠페인 인스타그램 릴스 수집 - BrightData API를 통한 신규 수집 + 기존 데이터 동기화"""
        try:
            from app.services.campaign_reel_collection_service import CampaignReelCollectionService
            from app.services.collection_worker import CollectionWorker
            
            campaign_url = schedule.campaign_url
            if "/reel/" in campaign_url:
                # 특정 릴스 URL인 경우
                print(f"🔄 특정 릴스 신규 수집 시작: {campaign_url}")
                
                # 1. 먼저 새로운 수집 작업 생성
                collection_service = CampaignReelCollectionService()
                jobs = collection_service.add_reel_collection_jobs(
                    campaign_id=campaign.id,
                    reel_urls=[campaign_url],
                    check_existing_data=True
                )
                
                if jobs:
                    print(f"📋 {len(jobs)}개 새 수집 작업 생성됨")
                    
                    # 2. 수집 작업 처리
                    processed = collection_service.process_pending_jobs(limit=10, campaign_id=campaign.id)
                    print(f"🔄 {processed}개 작업 BrightData로 전송됨")
                    
                    # 3. 완료된 작업들 처리 (30초 대기 후)
                    await asyncio.sleep(30)
                    worker = CollectionWorker()
                    await worker.process_pending_jobs()
                    print("✅ 수집 워커 완료")
                
                # 4. 기존 로직: 완료된 데이터를 캠페인 테이블로 동기화
                completed_jobs = self.db.query(models.CampaignReelCollectionJob).filter(
                    models.CampaignReelCollectionJob.campaign_id == campaign.id,
                    models.CampaignReelCollectionJob.status == "completed",
                    models.CampaignReelCollectionJob.user_posted.isnot(None)
                ).all()
                
                print(f"📊 {len(completed_jobs)}개 완료된 릴스 작업 발견")
                
                # 오늘 날짜 기준으로 저장된 데이터 개수 추적
                today = collection_date.date()
                saved_count = 0
                skipped_count = 0
                
                for job in completed_jobs:
                    try:
                        # 오늘 날짜에 이미 캠페인 테이블에 저장된 데이터가 있는지 확인
                        existing_reel = self.db.query(models.CampaignInstagramReel).filter(
                            models.CampaignInstagramReel.campaign_id == campaign.id,
                            models.CampaignInstagramReel.campaign_url == job.reel_url,
                            models.CampaignInstagramReel.collection_date >= datetime.combine(today, time.min),
                            models.CampaignInstagramReel.collection_date < datetime.combine(today + timedelta(days=1), time.min)
                        ).first()
                        
                        if not existing_reel:
                            # job_metadata에서 게시일자 추출
                            posted_at = job.created_at
                            if job.job_metadata and isinstance(job.job_metadata, dict):
                                date_posted_str = job.job_metadata.get('date_posted')
                                if date_posted_str:
                                    try:
                                        posted_at = datetime.fromisoformat(date_posted_str.replace('Z', '+00:00'))
                                    except:
                                        pass
                            
                            # 릴스 ID 생성 (URL에서 추출)
                            reel_id = job.reel_url.split('/')[-2] if job.reel_url.split('/')[-2] else f"reel_{job.id}"
                            
                            # 실제 프로필 데이터에서 팔로워 수와 분류 결과 가져오기
                            profile = self.db.query(models.InfluencerProfile).filter(
                                models.InfluencerProfile.username == job.user_posted
                            ).first()
                            
                            follower_count = 0
                            grade = "등급 없음"
                            
                            if profile:
                                follower_count = profile.followers or 0
                                # 1순위: 계정 내 전체 릴스 평균 조회수 기반 등급
                                grade = self._determine_influencer_grade(job.user_posted)
                                if grade:
                                    print(f"  ✅ {job.user_posted}: 평균 조회수 기반 등급 = {grade}")
                                else:
                                    # 2순위: 팔로워 수 기반 등급 (단일 릴스 조회수는 사용하지 않음)
                                    grade = self._get_grade_from_followers(follower_count)
                                    print(f"  📊 {job.user_posted}: 팔로워 수 기반 등급 = {grade}")
                            else:
                                # 프로필이 없으면 수집 필요
                                grade = "수집 필요"
                                print(f"  ⚠️ {job.user_posted}: 프로필 없음 → {grade}")
                            
                            # 해당 릴스의 분류 결과 가져오기 (influencer_reels 테이블에서)
                            influencer_reel = self.db.query(models.InfluencerReel).filter(
                                models.InfluencerReel.reel_id == reel_id,
                                models.InfluencerReel.profile_id == profile.id if profile else None
                            ).first()
                            
                            subscription_motivation = "미분류"
                            category = "미분류"
                            if influencer_reel:
                                subscription_motivation = influencer_reel.subscription_motivation or "미분류"
                                category = influencer_reel.category or "미분류"
                            
                            db_campaign_reel = models.CampaignInstagramReel(
                                campaign_id=campaign.id,
                                campaign_url=job.reel_url,
                                reel_id=reel_id,
                                username=job.user_posted,
                                display_name=job.user_posted,
                                follower_count=follower_count,
                                thumbnail_url=job.thumbnail_url,
                                s3_thumbnail_url=job.s3_thumbnail_url,
                                video_view_count=job.video_play_count or 0,
                                subscription_motivation=subscription_motivation,
                                category=category,
                                grade=grade,
                                product=campaign.product,
                                posted_at=posted_at,
                                collection_date=collection_date
                            )
                            self.db.add(db_campaign_reel)
                            saved_count += 1
                            print(f"  ➕ 새 릴스 추가: {job.user_posted} - {reel_id}")
                        else:
                            skipped_count += 1
                            print(f"  ⏭️ 오늘({today}) 이미 저장된 릴스 스킵: {job.user_posted} - {job.reel_url}")
                    except Exception as e:
                        print(f"  ❌ 릴스 저장 실패: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                # 커밋은 상위 메서드에서 처리하므로 여기서는 flush만 수행
                self.db.flush()
                print(f"🎉 릴스 데이터 업데이트 완료: {saved_count}개 저장, {skipped_count}개 스킵")
            else:
                # 사용자 프로필 URL인 경우, 해당 사용자의 최신 릴스들을 가져오기
                if "/reels" in campaign_url:
                    username = campaign_url.split('/')[-2]  # reels 앞의 username 추출
                else:
                    username = campaign_url.split('/')[-2] if campaign_url.split('/')[-2] else campaign_url.split('/')[-1]
                
                print(f"🔄 사용자 릴스 업데이트: {username}")
                
                # 인플루언서 프로필에서 최신 릴스들 가져오기
                profile = self.db.query(models.InfluencerProfile).filter(
                    models.InfluencerProfile.username == username
                ).first()
                
                if profile:
                    recent_reels = self.db.query(models.InfluencerReel).filter(
                        models.InfluencerReel.profile_id == profile.id
                    ).order_by(models.InfluencerReel.posted_at.desc()).limit(10).all()
                    
                    print(f"📊 {len(recent_reels)}개 최신 릴스 발견")
                    
                    grade = self._determine_influencer_grade(username) or "등급 없음"
                    
                    # 오늘 날짜 기준으로 저장된 데이터 개수 추적
                    today = collection_date.date()
                    saved_count = 0
                    skipped_count = 0
                    
                    for reel in recent_reels:
                        try:
                            # 오늘 날짜에 이미 캠페인 테이블에 저장된 데이터가 있는지 확인
                            existing_reel = self.db.query(models.CampaignInstagramReel).filter(
                                models.CampaignInstagramReel.campaign_id == campaign.id,
                                models.CampaignInstagramReel.reel_id == reel.reel_id,
                                models.CampaignInstagramReel.collection_date >= datetime.combine(today, time.min),
                                models.CampaignInstagramReel.collection_date < datetime.combine(today + timedelta(days=1), time.min)
                            ).first()
                            
                            if not existing_reel:
                                db_campaign_reel = models.CampaignInstagramReel(
                                    campaign_id=campaign.id,
                                    campaign_url=schedule.campaign_url,
                                    reel_id=reel.reel_id,
                                    username=username,
                                    display_name=profile.display_name,
                                    follower_count=profile.follower_count,
                                    thumbnail_url=reel.thumbnail_url,
                                    s3_thumbnail_url=reel.s3_thumbnail_url,
                                    video_view_count=reel.video_play_count or 0,
                                    subscription_motivation="인플루언서 데이터 기반",
                                    category="인플루언서 데이터 기반",
                                    grade=grade,
                                    product=campaign.product,
                                    posted_at=reel.posted_at,
                                    collection_date=collection_date
                                )
                                self.db.add(db_campaign_reel)
                                saved_count += 1
                                print(f"  ➕ 새 릴스 추가: {reel.reel_id}")
                            else:
                                skipped_count += 1
                                print(f"  ⏭️ 오늘({today}) 이미 저장된 릴스 스킵: {reel.reel_id}")
                        except Exception as e:
                            print(f"  ❌ 릴스 저장 실패: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            continue
                    
                    # 커밋은 상위 메서드에서 처리하므로 여기서는 flush만 수행
                    self.db.flush()
                    print(f"🎉 {username} 릴스 업데이트 완료: {saved_count}개 저장, {skipped_count}개 스킵")
                else:
                    print(f"❌ {username} 프로필을 찾을 수 없음")
            
        except Exception as e:
            print(f"Error collecting campaign Instagram reels: {str(e)}")
            self.db.rollback()

    async def _collect_campaign_blogs(
        self, 
        schedule: models.CollectionSchedule, 
        campaign: models.Campaign, 
        collection_date: datetime
    ):
        """캠페인 블로그 수집"""
        try:
            blog_data = await blog_service.collect_blog_data(schedule.campaign_url)
            if not blog_data:
                print(f"No blog data collected for {schedule.campaign_url}")
                return

            keywords = await self._generate_campaign_keywords(campaign.id, blog_data.get('title'))
            rankings = []
            for keyword in keywords:
                ranking = await blog_service._check_blog_ranking(schedule.campaign_url, keyword)
                if ranking:
                    rankings.append({'keyword': keyword, 'ranking': ranking})

            # 기존 데이터 정리 후 저장 (연관 랭킹 포함)
            existing_blogs = self.db.query(models.CampaignBlog).filter(
                models.CampaignBlog.campaign_id == campaign.id,
                models.CampaignBlog.campaign_url == schedule.campaign_url,
            ).all()
            for blog_entry in existing_blogs:
                self.db.delete(blog_entry)
            self.db.flush()

            base_entry = models.CampaignBlog(
                campaign_id=campaign.id,
                campaign_url=schedule.campaign_url,
                username=blog_data.get('username'),
                title=blog_data.get('title'),
                likes_count=blog_data.get('likes_count', 0),
                comments_count=blog_data.get('comments_count', 0),
                daily_visitors=blog_data.get('daily_visitors', 0),
                product=campaign.product,
                posted_at=blog_data.get('posted_at'),
                collection_date=collection_date
            )

            ranking_records: List[models.CampaignBlogRanking] = []
            ranking_keywords = set()
            for ranking_info in rankings:
                keyword = ranking_info['keyword']
                if not keyword:
                    continue
                ranking_keywords.add(keyword)
                ranking_records.append(
                    models.CampaignBlogRanking(
                        keyword=keyword,
                        ranking=ranking_info.get('ranking')
                    )
                )

            for keyword in keywords:
                if keyword and keyword not in ranking_keywords:
                    ranking_records.append(
                        models.CampaignBlogRanking(
                            keyword=keyword,
                            ranking=None
                        )
                    )

            if ranking_records:
                base_entry.rankings.extend(ranking_records)

            self.db.add(base_entry)

            # 커밋은 상위 메서드에서 처리하므로 여기서는 flush만 수행
            self.db.flush()
            print(f"Collected blog data for campaign {campaign.name}")
            
        except Exception as e:
            print(f"Error collecting campaign blogs: {str(e)}")
            self.db.rollback()

    def _calculate_influencer_average_views(self, username: str) -> Optional[float]:
        profile = (
            self.db.query(models.InfluencerProfile)
            .filter(models.InfluencerProfile.username == username)
            .first()
        )
        if not profile:
            return None

        view_counts = [
            row[0]
            for row in self.db.query(models.InfluencerReel.video_play_count)
            .filter(
                models.InfluencerReel.profile_id == profile.id,
                models.InfluencerReel.video_play_count.isnot(None),
            )
            .all()
            if row[0] is not None
        ]

        if not view_counts:
            return None

        view_counts.sort()
        if len(view_counts) > 4:
            trimmed = view_counts[2:-2]
            if not trimmed:
                trimmed = view_counts
        else:
            trimmed = view_counts

        if not trimmed:
            return None

        return sum(trimmed) / len(trimmed)

    def _determine_influencer_grade(self, username: str) -> Optional[str]:
        average_views = self._calculate_influencer_average_views(username)
        if average_views is None:
            return None
        return instagram_grade_service.get_grade_for_average(self.db, average_views)
    
    def _get_grade_from_followers(self, follower_count: int) -> str:
        """팔로워 수에 따른 기본 등급 분류"""
        if follower_count >= 100000:
            return "A"
        elif follower_count >= 10000:
            return "B"
        elif follower_count > 0:
            return "C"
        else:
            return "등급 없음"
    
    def _get_grade_from_views(self, view_count: int) -> str:
        """조회수에 따른 등급 분류 (instagram_grade_thresholds 테이블 기반)"""
        try:
            # 데이터베이스에서 등급 임계값 조회
            thresholds = self.db.query(models.InstagramGradeThreshold).order_by(
                models.InstagramGradeThreshold.min_view_count.desc()
            ).all()
            
            for threshold in thresholds:
                if view_count >= threshold.min_view_count:
                    if threshold.max_view_count is None or view_count <= threshold.max_view_count:
                        return threshold.grade_name
            
            # 어떤 임계값도 맞지 않으면 기본값
            return "등급 없음"
            
        except Exception as e:
            print(f"등급 계산 오류: {e}")
            return "등급 없음"

    async def _generate_campaign_keywords(self, campaign_id: int, new_title: Optional[str]) -> List[str]:
        """캠페인 전체 제목을 기반으로 GPT를 활용해 핵심 키워드를 도출합니다."""
        titles_query = self.db.query(models.CampaignBlog.title).filter(
            models.CampaignBlog.campaign_id == campaign_id
        )
        titles = [row[0] for row in titles_query if row and row[0]]
        if new_title:
            titles.append(new_title)

        unique_titles: List[str] = []
        for title in titles:
            normalized = title.strip() if title else ""
            if normalized and normalized not in unique_titles:
                unique_titles.append(normalized)

        if not unique_titles:
            return []

        if settings.openai_api_key:
            try:
                keywords = await self.openai_service.extract_keywords_from_titles(unique_titles, top_n=6)
                if keywords:
                    return keywords
            except Exception as exc:  # noqa: BLE001
                print(f"Error generating keywords with OpenAI: {exc}")

        return self._fallback_keywords(unique_titles)

    @staticmethod
    def _fallback_keywords(titles: List[str], limit: int = 5) -> List[str]:
        counter: Counter[str] = Counter()
        for title in titles:
            tokens = re.findall(r'[가-힣a-zA-Z0-9]+', title or '')
            for token in tokens:
                if len(token) >= 2:
                    counter[token] += 1
        return [kw for kw, _ in counter.most_common(limit)]

scheduler_service = SchedulerService()
