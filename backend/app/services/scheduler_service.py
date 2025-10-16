import asyncio
from datetime import datetime, timedelta
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
        """정기 수집 실행"""
        try:
            print(f"Starting scheduled collection at {datetime.now()}")
            
            # 활성 스케줄 조회 (오늘 날짜가 수집 기간 내에 있는 것만)
            today = datetime.now().date()
            active_schedules = self.db.query(models.CollectionSchedule).filter(
                models.CollectionSchedule.is_active == True,
                models.CollectionSchedule.start_date.cast(models.Date) <= today,
                models.CollectionSchedule.end_date.cast(models.Date) >= today
            ).all()
            
            print(f"Found {len(active_schedules)} active schedules")
            
            for schedule in active_schedules:
                try:
                    await self._process_schedule(schedule)
                except Exception as e:
                    print(f"Error processing schedule {schedule.id}: {str(e)}")
                    continue
            
            print(f"Scheduled collection completed at {datetime.now()}")
            
        except Exception as e:
            print(f"Error in scheduled collection: {str(e)}")
        finally:
            self.db.close()

    async def _process_schedule(self, schedule: models.CollectionSchedule):
        """개별 스케줄 처리"""
        campaign = schedule.campaign
        collection_date = datetime.now()
        
        print(f"Processing schedule for campaign: {campaign.name}, channel: {schedule.channel}")
        
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
            
            self.db.commit()
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
        """캠페인 인스타그램 릴스 수집"""
        try:
            reel_data = await instagram_service.collect_instagram_reel_data(schedule.campaign_url)
            if not reel_data:
                print(f"No Instagram reel data collected for {schedule.campaign_url}")
                return
            
            # 사용자 릴스들 수집
            username = reel_data.get('username')
            if not username:
                print(f"Instagram reel lacks username for {schedule.campaign_url}")
                return
            user_reels = await instagram_service.collect_user_reels_thumbnails(username, 24)
            if not user_reels:
                user_reels = [reel_data]
            
            placeholder_message = "인플루언서 분석 수집 필요"

            # 캠페인 테이블에 저장
            for reel in user_reels:
                db_campaign_reel = models.CampaignInstagramReel(
                    campaign_id=campaign.id,
                    campaign_url=schedule.campaign_url,
                    reel_id=reel['reel_id'],
                    username=reel['username'],
                    display_name=reel.get('display_name'),
                    follower_count=reel.get('follower_count', 0),
                    thumbnail_url=reel.get('thumbnail_url'),
                    s3_thumbnail_url=reel.get('s3_thumbnail_url'),
                    video_view_count=reel.get('video_view_count', 0),
                    subscription_motivation=placeholder_message,
                    category=placeholder_message,
                    grade=placeholder_message,
                    product=campaign.product,
                    posted_at=reel.get('posted_at'),
                    collection_date=collection_date
                )
                self.db.add(db_campaign_reel)
            
            self.db.commit()
            print(f"Collected {len(user_reels)} Instagram reels for campaign {campaign.name}")
            
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

            self.db.commit()
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
