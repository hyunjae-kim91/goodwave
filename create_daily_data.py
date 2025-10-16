#!/usr/bin/env python3
"""
일자별 수집 데이터 생성 스크립트
"""

import psycopg2
from datetime import datetime, timedelta
import random

# 데이터베이스 연결
conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="goodwave_report",
    user="postgres",
    password="postgres"
)
cursor = conn.cursor()

# 기존 데이터 조회
print("기존 데이터 조회 중...")
cursor.execute("SELECT id, campaign_id, likes_count, comments_count FROM campaign_instagram_posts")
posts = cursor.fetchall()

cursor.execute("SELECT id, campaign_id, video_view_count FROM campaign_instagram_reels")
reels = cursor.fetchall()

cursor.execute("SELECT id, campaign_id, likes_count, comments_count FROM campaign_blogs")
blogs = cursor.fetchall()

# 날짜 범위 생성 (최근 7일)
dates = []
base_date = datetime.now()
for i in range(7):
    date = base_date - timedelta(days=i)
    dates.append(date)

print(f"생성할 날짜: {[d.strftime('%Y-%m-%d') for d in dates]}")

# 인스타그램 게시물 일자별 데이터 생성
print("인스타그램 게시물 일자별 데이터 생성 중...")
for post in posts:
    post_id, campaign_id, base_likes, base_comments = post
    
    for i, date in enumerate(dates):
        if i == 0:  # 오늘 데이터는 건드리지 않음
            continue
            
        # 점진적으로 감소하는 패턴
        likes_variation = random.uniform(0.8, 1.0) - (i * 0.05)
        comments_variation = random.uniform(0.8, 1.0) - (i * 0.05)
        
        new_likes = max(1, int(base_likes * likes_variation))
        new_comments = max(0, int(base_comments * comments_variation))
        
        cursor.execute("""
            INSERT INTO campaign_instagram_posts 
            (campaign_id, campaign_url, post_id, username, display_name, follower_count, 
             s3_thumbnail_url, likes_count, comments_count, subscription_motivation, 
             category, grade, product, posted_at, collection_date)
            SELECT campaign_id, campaign_url, post_id, username, display_name, follower_count,
                   s3_thumbnail_url, %s, %s, subscription_motivation,
                   category, grade, product, posted_at, %s
            FROM campaign_instagram_posts WHERE id = %s
        """, (new_likes, new_comments, date, post_id))

# 인스타그램 릴스 일자별 데이터 생성
print("인스타그램 릴스 일자별 데이터 생성 중...")
for reel in reels:
    reel_id, campaign_id, base_views = reel
    
    for i, date in enumerate(dates):
        if i == 0:  # 오늘 데이터는 건드리지 않음
            continue
            
        # 점진적으로 증가하는 패턴 (릴스는 시간이 지날수록 조회수 증가)
        views_variation = random.uniform(0.7, 0.9) + (i * 0.02)
        new_views = max(1, int(base_views * views_variation))
        
        cursor.execute("""
            INSERT INTO campaign_instagram_reels
            (campaign_id, campaign_url, reel_id, username, display_name, follower_count,
             s3_thumbnail_url, video_view_count, subscription_motivation,
             category, grade, product, posted_at, collection_date)
            SELECT campaign_id, campaign_url, reel_id, username, display_name, follower_count,
                   s3_thumbnail_url, %s, subscription_motivation,
                   category, grade, product, posted_at, %s
            FROM campaign_instagram_reels WHERE id = %s
        """, (new_views, date, reel_id))

# 블로그 일자별 데이터 생성
print("블로그 일자별 데이터 생성 중...")
for blog in blogs:
    blog_id, campaign_id, base_likes, base_comments = blog
    
    for i, date in enumerate(dates):
        if i == 0:  # 오늘 데이터는 건드리지 않음
            continue
            
        # 조금씩 변하는 패턴
        likes_variation = random.uniform(0.9, 1.1)
        comments_variation = random.uniform(0.9, 1.1)
        
        new_likes = max(0, int(base_likes * likes_variation))
        new_comments = max(0, int(base_comments * comments_variation))
        
        cursor.execute("""
            INSERT INTO campaign_blogs
            (campaign_id, campaign_url, title, likes_count, comments_count, daily_visitors,
             keyword, ranking, product, posted_at, collection_date)
            SELECT campaign_id, campaign_url, title, %s, %s, daily_visitors,
                   keyword, ranking, product, posted_at, %s
            FROM campaign_blogs WHERE id = %s
        """, (new_likes, new_comments, date, blog_id))

# 변경사항 커밋
conn.commit()

print("일자별 데이터 생성 완료!")
print(f"생성된 데이터:")
print(f"- 인스타그램 게시물: {len(posts) * (len(dates) - 1)}개")
print(f"- 인스타그램 릴스: {len(reels) * (len(dates) - 1)}개") 
print(f"- 블로그: {len(blogs) * (len(dates) - 1)}개")

cursor.close()
conn.close()