#!/usr/bin/env python3
"""
인플루언서 분석용 테스트 데이터 생성 스크립트
"""

import os
import sys
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.models import (
    Base, InfluencerProfile, InfluencerPost, InfluencerReel, 
    InfluencerAnalysis, SystemPrompt
)
from app.db.database import get_database_url

# 한국 인플루언서 샘플 데이터
SAMPLE_INFLUENCERS = [
    {
        "username": "beauty_guru_kr",
        "full_name": "김아름",
        "followers": 150000,
        "following": 800,
        "bio": "🇰🇷 뷰티 인플루언서 💄 일상 메이크업부터 특별한 날까지",
        "category_name": "뷰티",
        "profile_name": "아름이의 뷰티 다이어리",
        "email_address": "beauty@example.com",
        "posts_count": 245,
        "avg_engagement": 0.048
    },
    {
        "username": "fitness_trainer_seoul",
        "full_name": "박건강",
        "followers": 89000,
        "following": 1200,
        "bio": "💪 서울 기반 피트니스 트레이너 🏋️‍♂️ 홈트레이닝 전문",
        "category_name": "피트니스",
        "profile_name": "건강이의 홈트",
        "email_address": "fitness@example.com",
        "posts_count": 189,
        "avg_engagement": 0.062
    },
    {
        "username": "fashion_style_korea",
        "full_name": "이스타일",
        "followers": 203000,
        "following": 650,
        "bio": "👗 한국 패션 스타일리스트 ✨ 데일리룩 & 코디 팁",
        "category_name": "패션",
        "profile_name": "스타일의 정석",
        "email_address": "fashion@example.com",
        "posts_count": 312,
        "avg_engagement": 0.041
    },
    {
        "username": "food_blogger_busan",
        "full_name": "최맛있",
        "followers": 67000,
        "following": 900,
        "bio": "🍜 부산 맛집 탐방 전문가 🦐 해산물 러버",
        "category_name": "음식",
        "profile_name": "맛있이의 부산 맛집",
        "email_address": "food@example.com",
        "posts_count": 156,
        "avg_engagement": 0.055
    },
    {
        "username": "travel_korea_life",
        "full_name": "정여행",
        "followers": 124000,
        "following": 1100,
        "bio": "🌏 국내외 여행 전문 📸 숨은 여행지 발굴",
        "category_name": "여행",
        "profile_name": "여행이의 발견",
        "email_address": "travel@example.com",
        "posts_count": 278,
        "avg_engagement": 0.039
    },
    {
        "username": "tech_reviewer_kr",
        "full_name": "김테크",
        "followers": 98000,
        "following": 450,
        "bio": "💻 IT 제품 리뷰어 📱 스마트폰 & 가젯 전문",
        "category_name": "테크",
        "profile_name": "테크의 모든 것",
        "email_address": "tech@example.com",
        "posts_count": 167,
        "avg_engagement": 0.043
    },
    {
        "username": "lifestyle_mom_kr",
        "full_name": "박육아",
        "followers": 145000,
        "following": 1350,
        "bio": "👶 육아맘의 일상 🏠 살림 노하우 & 육아 팁",
        "category_name": "라이프스타일",
        "profile_name": "육아의 달인",
        "email_address": "lifestyle@example.com",
        "posts_count": 334,
        "avg_engagement": 0.051
    },
    {
        "username": "dance_artist_korea",
        "full_name": "이댄스",
        "followers": 76000,
        "following": 800,
        "bio": "💃 K-POP 댄스 커버 🎵 안무 튜토리얼",
        "category_name": "댄스",
        "profile_name": "댄스의 신",
        "email_address": "dance@example.com",
        "posts_count": 198,
        "avg_engagement": 0.067
    }
]

# 구독 동기 카테고리
SUBSCRIPTION_MOTIVATIONS = [
    "정보 습득", "엔터테인먼트", "영감", "트렌드 파악", "전문성", "친근감"
]

# 컨텐츠 카테고리
CONTENT_CATEGORIES = [
    "뷰티", "패션", "피트니스", "음식", "여행", "테크", "라이프스타일", "댄스", "교육", "엔터테인먼트"
]

# 샘플 캡션
SAMPLE_CAPTIONS = [
    "오늘의 메이크업 튜토리얼! 여러분도 따라해보세요 💄",
    "새로운 운동법을 소개합니다. 집에서도 쉽게! 💪",
    "이번 주 코디 추천! 어떠신가요? 👗",
    "부산에서 발견한 숨은 맛집! 꼭 가보세요 🍜",
    "제주도 여행 꿀팁 공유합니다 🌴",
    "최신 스마트폰 리뷰! 구매 전 꼭 보세요 📱",
    "육아맘의 하루 일상 공유 👶",
    "K-POP 댄스 커버! 어떠신가요? 💃"
]

SAMPLE_HASHTAGS = [
    ["#뷰티", "#메이크업", "#코스메틱", "#데일리메이크업"],
    ["#피트니스", "#홈트", "#다이어트", "#건강관리"],
    ["#패션", "#코디", "#OOTD", "#스타일링"],
    ["#맛집", "#부산맛집", "#해산물", "#먹스타그램"],
    ["#여행", "#제주도", "#국내여행", "#여행스타그램"],
    ["#테크", "#IT", "#스마트폰", "#가젯리뷰"],
    ["#육아", "#육아일상", "#육아맘", "#라이프스타일"],
    ["#댄스", "#KPOP", "#댄스커버", "#안무"]
]

def create_database_tables():
    """데이터베이스 테이블 생성"""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(bind=engine)
    return engine

def insert_system_prompts(session):
    """시스템 프롬프트 생성"""
    prompts = [
        {
            "prompt_type": "system_prompt",
            "content": """당신은 인스타그램 이미지를 분석하여 구독자들의 구독 동기와 콘텐츠 카테고리를 분류하는 전문가입니다.

주어진 이미지를 분석하여 다음 두 가지를 분류해주세요:

1. 구독 동기 (Subscription Motivation):
- 정보 습득: 유용한 정보나 지식을 얻기 위해
- 엔터테인먼트: 재미나 즐거움을 위해
- 영감: 동기부여나 영감을 얻기 위해
- 트렌드 파악: 최신 트렌드를 파악하기 위해
- 전문성: 전문적인 지식이나 기술을 배우기 위해
- 친근감: 인플루언서와의 친밀감이나 동질감을 위해

2. 콘텐츠 카테고리:
- 뷰티, 패션, 피트니스, 음식, 여행, 테크, 라이프스타일, 댄스, 교육, 엔터테인먼트

응답 형식:
{
  "motivation": "선택된 구독 동기",
  "category": "선택된 카테고리"
}"""
        }
    ]
    
    for prompt_data in prompts:
        existing = session.query(SystemPrompt).filter_by(prompt_type=prompt_data["prompt_type"]).first()
        if not existing:
            prompt = SystemPrompt(**prompt_data)
            session.add(prompt)
    
    session.commit()
    print("✅ 시스템 프롬프트 생성 완료")

def insert_influencer_profiles(session):
    """인플루언서 프로필 생성"""
    profiles = []
    
    for influencer_data in SAMPLE_INFLUENCERS:
        # 중복 체크
        existing = session.query(InfluencerProfile).filter_by(username=influencer_data["username"]).first()
        if existing:
            profiles.append(existing)
            continue
            
        profile = InfluencerProfile(
            username=influencer_data["username"],
            full_name=influencer_data["full_name"],
            followers=influencer_data["followers"],
            following=influencer_data["following"],
            bio=influencer_data["bio"],
            profile_pic_url=f"https://example.com/profiles/{influencer_data['username']}.jpg",
            account=influencer_data["username"],
            posts_count=influencer_data["posts_count"],
            avg_engagement=influencer_data["avg_engagement"],
            category_name=influencer_data["category_name"],
            profile_name=influencer_data["profile_name"],
            email_address=influencer_data["email_address"],
            is_business_account=random.choice([True, False]),
            is_professional_account=random.choice([True, False]),
            is_verified=random.choice([True, False])
        )
        session.add(profile)
        profiles.append(profile)
    
    session.commit()
    print(f"✅ 인플루언서 프로필 {len(SAMPLE_INFLUENCERS)}개 생성 완료")
    return profiles

def insert_influencer_posts(session, profiles):
    """인플루언서 게시물 생성"""
    total_posts = 0
    
    for profile in profiles:
        # 각 프로필마다 10-20개의 게시물 생성
        num_posts = random.randint(10, 20)
        
        for i in range(num_posts):
            # 기존 게시물 체크 (중복 방지)
            post_id = f"{profile.username}_post_{i+1}"
            existing = session.query(InfluencerPost).filter_by(post_id=post_id).first()
            if existing:
                continue
                
            post_date = datetime.now() - timedelta(days=random.randint(1, 365))
            
            post = InfluencerPost(
                profile_id=profile.id,
                post_id=post_id,
                media_type="IMAGE",
                media_urls=[f"https://example.com/media/{post_id}.jpg"],
                caption=random.choice(SAMPLE_CAPTIONS),
                timestamp=post_date,
                user_posted=profile.username,
                profile_url=f"https://instagram.com/{profile.username}",
                date_posted=post_date.strftime("%Y-%m-%d"),
                num_comments=random.randint(5, 200),
                likes=random.randint(100, 5000),
                photos=[f"https://example.com/photos/{post_id}.jpg"],
                content_type="post",
                description=random.choice(SAMPLE_CAPTIONS),
                hashtags=random.choice(SAMPLE_HASHTAGS)
            )
            session.add(post)
            total_posts += 1
    
    session.commit()
    print(f"✅ 인플루언서 게시물 {total_posts}개 생성 완료")

def insert_influencer_reels(session, profiles):
    """인플루언서 릴스 생성"""
    total_reels = 0
    
    for profile in profiles:
        # 각 프로필마다 5-15개의 릴스 생성
        num_reels = random.randint(5, 15)
        
        for i in range(num_reels):
            # 기존 릴스 체크 (중복 방지)
            reel_id = f"{profile.username}_reel_{i+1}"
            existing = session.query(InfluencerReel).filter_by(reel_id=reel_id).first()
            if existing:
                continue
                
            reel_date = datetime.now() - timedelta(days=random.randint(1, 180))
            
            reel = InfluencerReel(
                profile_id=profile.id,
                reel_id=reel_id,
                media_type="VIDEO",
                media_urls=[f"https://example.com/reels/{reel_id}.mp4"],
                caption=random.choice(SAMPLE_CAPTIONS),
                timestamp=reel_date,
                user_posted=profile.username,
                profile_url=f"https://instagram.com/{profile.username}",
                date_posted=reel_date.strftime("%Y-%m-%d"),
                num_comments=random.randint(10, 300),
                likes=random.randint(200, 8000),
                photos=[],
                content_type="reel",
                description=random.choice(SAMPLE_CAPTIONS),
                hashtags=random.choice(SAMPLE_HASHTAGS),
                url=f"https://instagram.com/reel/{reel_id}",
                views=random.randint(1000, 50000),
                video_play_count=random.randint(1000, 50000)
            )
            session.add(reel)
            total_reels += 1
    
    session.commit()
    print(f"✅ 인플루언서 릴스 {total_reels}개 생성 완료")

def insert_analysis_results(session, profiles):
    """분석 결과 생성"""
    total_analysis = 0
    
    for profile in profiles:
        # 각 프로필마다 분석 결과 생성
        analysis_results = []
        
        # 구독 동기 분석 결과
        motivation_result = {
            "results": []
        }
        for i in range(random.randint(5, 10)):
            motivation_result["results"].append({
                "image_filename": f"{profile.username}_image_{i+1}.jpg",
                "motivation": random.choice(SUBSCRIPTION_MOTIVATIONS),
                "confidence": round(random.uniform(0.7, 0.95), 2)
            })
        
        analysis = InfluencerAnalysis(
            profile_id=profile.id,
            analysis_type="subscription_motivation",
            analysis_result=motivation_result,
            prompt_used="구독 동기 분석 프롬프트"
        )
        session.add(analysis)
        total_analysis += 1
        
        # 카테고리 분석 결과
        category_result = {
            "results": []
        }
        for i in range(random.randint(5, 10)):
            category_result["results"].append({
                "image_filename": f"{profile.username}_image_{i+1}.jpg",
                "category": random.choice(CONTENT_CATEGORIES),
                "confidence": round(random.uniform(0.7, 0.95), 2)
            })
        
        analysis = InfluencerAnalysis(
            profile_id=profile.id,
            analysis_type="category",
            analysis_result=category_result,
            prompt_used="카테고리 분석 프롬프트"
        )
        session.add(analysis)
        total_analysis += 1
        
        # 통합 분석 결과
        combined_result = {
            "username": profile.username,
            "total_images": random.randint(8, 15),
            "classified_at": datetime.now().isoformat(),
            "results": []
        }
        
        for i in range(combined_result["total_images"]):
            combined_result["results"].append({
                "image_filename": f"{profile.username}_image_{i+1}.jpg",
                "motivation": random.choice(SUBSCRIPTION_MOTIVATIONS),
                "category": random.choice(CONTENT_CATEGORIES),
                "caption": random.choice(SAMPLE_CAPTIONS),
                "hashtags": random.choice(SAMPLE_HASHTAGS),
                "classified_at": datetime.now().isoformat()
            })
        
        analysis = InfluencerAnalysis(
            profile_id=profile.id,
            analysis_type="combined",
            analysis_result=combined_result,
            prompt_used="통합 분석 프롬프트"
        )
        session.add(analysis)
        total_analysis += 1
    
    session.commit()
    print(f"✅ 분석 결과 {total_analysis}개 생성 완료")

def main():
    """메인 실행 함수"""
    print("🚀 인플루언서 분석용 테스트 데이터 생성을 시작합니다...")
    
    # 데이터베이스 연결
    engine = create_database_tables()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. 시스템 프롬프트 생성
        insert_system_prompts(session)
        
        # 2. 인플루언서 프로필 생성
        profiles = insert_influencer_profiles(session)
        
        # 3. 게시물 생성
        insert_influencer_posts(session, profiles)
        
        # 4. 릴스 생성
        insert_influencer_reels(session, profiles)
        
        # 5. 분석 결과 생성
        insert_analysis_results(session, profiles)
        
        print("\n🎉 모든 테스트 데이터 생성이 완료되었습니다!")
        print(f"   - 인플루언서 프로필: {len(SAMPLE_INFLUENCERS)}개")
        print(f"   - 시스템 프롬프트: 1개")
        print("   - 게시물 및 릴스: 각 프로필마다 10-35개")
        print("   - 분석 결과: 각 프로필마다 3개 (구독동기, 카테고리, 통합)")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()