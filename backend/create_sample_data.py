#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from app.db.models import (
    Campaign, CampaignURL, CollectionSchedule,
    InstagramPost, InstagramReel, BlogPost,
    CampaignInstagramPost, CampaignInstagramReel, CampaignBlog,
    CampaignBlogRanking,
)
from datetime import datetime, timedelta
import random

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

def create_sample_data():
    try:
        # 1. Create sample campaigns
        campaigns_data = [
            {
                "name": "뷰티 제품 인스타그램 캠페인",
                "campaign_type": "instagram_post",
                "budget": 5000000.0,
                "product": "BB크림",
                "start_date": datetime.now() - timedelta(days=30),
                "end_date": datetime.now() + timedelta(days=30)
            },
            {
                "name": "패션 릴스 캠페인", 
                "campaign_type": "instagram_reel",
                "budget": 3000000.0,
                "product": "겨울 코트",
                "start_date": datetime.now() - timedelta(days=20),
                "end_date": datetime.now() + timedelta(days=40)
            },
            {
                "name": "맛집 블로그 캠페인",
                "campaign_type": "blog", 
                "budget": 2000000.0,
                "product": "카페 디저트",
                "start_date": datetime.now() - timedelta(days=15),
                "end_date": datetime.now() + timedelta(days=45)
            }
        ]
        
        campaigns = []
        for data in campaigns_data:
            campaign = Campaign(**data)
            session.add(campaign)
            campaigns.append(campaign)
        
        session.commit()
        print(f"Created {len(campaigns)} campaigns")

        # 2. Create sample Instagram posts
        instagram_usernames = [
            "beauty_blogger_kr", "makeup_artist_seoul", "skincare_lover",
            "fashion_influencer", "style_guru_kr", "trendy_girl_seoul",
            "lifestyle_blogger", "korean_beauty_tips", "Seoul_fashionista"
        ]
        
        categories = ["뷰티", "패션", "라이프스타일", "건강", "여행"]
        motivations = ["제품 체험", "할인 혜택", "브랜드 신뢰도", "트렌드", "추천"]
        grades = ["A", "B", "C"]
        
        instagram_posts = []
        for i in range(50):
            username = random.choice(instagram_usernames)
            post = InstagramPost(
                post_id=f"post_{i+1}_{random.randint(1000, 9999)}",
                username=username,
                display_name=f"{username.replace('_', ' ').title()}",
                follower_count=random.randint(1000, 500000),
                thumbnail_url=f"https://example.com/thumbnails/post_{i+1}.jpg",
                likes_count=random.randint(50, 10000),
                comments_count=random.randint(5, 500),
                subscription_motivation=random.choice(motivations),
                category=random.choice(categories),
                grade=random.choice(grades),
                posted_at=datetime.now() - timedelta(days=random.randint(1, 30))
            )
            session.add(post)
            instagram_posts.append(post)
        
        print(f"Created {len(instagram_posts)} Instagram posts")

        # 3. Create sample Instagram reels
        reel_usernames = [
            "dance_queen_kr", "cooking_master", "fitness_guru_seoul",
            "travel_vlogger_kr", "music_lover_korea", "comedy_king"
        ]
        
        instagram_reels = []
        for i in range(30):
            username = random.choice(reel_usernames)
            reel = InstagramReel(
                reel_id=f"reel_{i+1}_{random.randint(1000, 9999)}",
                username=username,
                display_name=f"{username.replace('_', ' ').title()}",
                follower_count=random.randint(5000, 1000000),
                thumbnail_url=f"https://example.com/thumbnails/reel_{i+1}.jpg",
                video_view_count=random.randint(1000, 100000),
                subscription_motivation=random.choice(motivations),
                category=random.choice(categories),
                grade=random.choice(grades),
                posted_at=datetime.now() - timedelta(days=random.randint(1, 20))
            )
            session.add(reel)
            instagram_reels.append(reel)
        
        print(f"Created {len(instagram_reels)} Instagram reels")

        # 4. Create sample blog posts
        blog_urls = [
            "https://blog.naver.com/beauty_review/123",
            "https://blog.naver.com/fashion_style/456", 
            "https://blog.naver.com/food_lover/789",
            "https://tistory.com/lifestyle_blog/abc",
            "https://tistory.com/travel_diary/def"
        ]
        
        blog_titles = [
            "겨울철 건조한 피부를 위한 스킨케어 루틴",
            "올 겨울 트렌드 코트 추천",
            "서울 맛집 베스트 10곳",
            "데일리 메이크업 꿀팁",
            "주말 나들이 코디 추천"
        ]
        
        blog_posts = []
        for i in range(40):
            blog = BlogPost(
                url=f"{random.choice(blog_urls)}/{i+1}",
                title=random.choice(blog_titles) + f" - {i+1}편",
                likes_count=random.randint(10, 1000),
                comments_count=random.randint(1, 100),
                daily_visitors=random.randint(50, 5000),
                posted_at=datetime.now() - timedelta(days=random.randint(1, 60))
            )
            session.add(blog)
            blog_posts.append(blog)
        
        print(f"Created {len(blog_posts)} blog posts")

        # 5. Create campaign-specific data
        campaign_instagram_posts = []
        for campaign in campaigns:
            if campaign.campaign_type == "instagram_post":
                for i in range(15):
                    username = random.choice(instagram_usernames)
                    campaign_post = CampaignInstagramPost(
                        campaign_id=campaign.id,
                        campaign_url=f"https://www.instagram.com/{username}/",
                        post_id=f"campaign_post_{campaign.id}_{i+1}",
                        username=username,
                        display_name=f"{username.replace('_', ' ').title()}",
                        follower_count=random.randint(1000, 300000),
                        thumbnail_url=f"https://example.com/campaign_thumbnails/{campaign.id}_{i+1}.jpg",
                        likes_count=random.randint(100, 5000),
                        comments_count=random.randint(10, 300),
                        subscription_motivation=random.choice(motivations),
                        category=random.choice(categories),
                        grade=random.choice(grades),
                        product=campaign.product,
                        posted_at=datetime.now() - timedelta(days=random.randint(1, 15)),
                        collection_date=datetime.now() - timedelta(days=random.randint(0, 10))
                    )
                    session.add(campaign_post)
                    campaign_instagram_posts.append(campaign_post)
        
        print(f"Created {len(campaign_instagram_posts)} campaign Instagram posts")

        # Campaign Instagram reels
        campaign_instagram_reels = []
        for campaign in campaigns:
            if campaign.campaign_type == "instagram_reel":
                for i in range(10):
                    username = random.choice(reel_usernames)
                    campaign_reel = CampaignInstagramReel(
                        campaign_id=campaign.id,
                        campaign_url=f"https://www.instagram.com/{username}/",
                        reel_id=f"campaign_reel_{campaign.id}_{i+1}",
                        username=username,
                        display_name=f"{username.replace('_', ' ').title()}",
                        follower_count=random.randint(5000, 500000),
                        thumbnail_url=f"https://example.com/campaign_thumbnails/reel_{campaign.id}_{i+1}.jpg",
                        video_view_count=random.randint(2000, 50000),
                        subscription_motivation=random.choice(motivations),
                        category=random.choice(categories),
                        grade=random.choice(grades),
                        product=campaign.product,
                        posted_at=datetime.now() - timedelta(days=random.randint(1, 12)),
                        collection_date=datetime.now() - timedelta(days=random.randint(0, 8))
                    )
                    session.add(campaign_reel)
                    campaign_instagram_reels.append(campaign_reel)
        
        print(f"Created {len(campaign_instagram_reels)} campaign Instagram reels")

        # Campaign blogs
        campaign_blogs = []
        for campaign in campaigns:
            if campaign.campaign_type == "blog":
                keywords = [f"{campaign.product} 리뷰", f"{campaign.product} 추천", f"{campaign.product} 후기"]
                for i in range(12):
                    blog_entry = CampaignBlog(
                        campaign_id=campaign.id,
                        campaign_url=f"{random.choice(blog_urls)}/campaign_{campaign.id}_{i+1}",
                        username=f"blogger_{i+1}",
                        title=f"{campaign.product} 사용 후기 - {i+1}일차",
                        likes_count=random.randint(20, 800),
                        comments_count=random.randint(2, 80),
                        daily_visitors=random.randint(100, 3000),
                        product=campaign.product,
                        posted_at=datetime.now() - timedelta(days=random.randint(1, 10)),
                        collection_date=datetime.now() - timedelta(days=random.randint(0, 5))
                    )

                    for keyword in keywords:
                        blog_entry.rankings.append(
                            CampaignBlogRanking(
                                keyword=keyword,
                                ranking=random.randint(1, 50)
                            )
                        )

                    session.add(blog_entry)
                    campaign_blogs.append(blog_entry)
        
        print(f"Created {len(campaign_blogs)} campaign blogs")

        session.commit()
        print("✅ Sample data created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_sample_data()
