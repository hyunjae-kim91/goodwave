-- 일자별 수집 데이터 생성 SQL
-- 최근 7일간의 일자별 데이터 생성

-- 인스타그램 게시물 일자별 데이터 생성
INSERT INTO campaign_instagram_posts 
(campaign_id, campaign_url, post_id, username, display_name, follower_count, 
 s3_thumbnail_url, likes_count, comments_count, subscription_motivation, 
 category, grade, product, posted_at, collection_date)
SELECT 
    campaign_id, campaign_url, post_id, username, display_name, follower_count,
    s3_thumbnail_url, 
    CASE 
        WHEN generate_series = 1 THEN CAST(likes_count * (0.9 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 2 THEN CAST(likes_count * (0.8 + random() * 0.2) AS INTEGER)  
        WHEN generate_series = 3 THEN CAST(likes_count * (0.7 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 4 THEN CAST(likes_count * (0.6 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 5 THEN CAST(likes_count * (0.5 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 6 THEN CAST(likes_count * (0.4 + random() * 0.2) AS INTEGER)
    END as likes_count,
    CASE 
        WHEN generate_series = 1 THEN CAST(comments_count * (0.9 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 2 THEN CAST(comments_count * (0.8 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 3 THEN CAST(comments_count * (0.7 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 4 THEN CAST(comments_count * (0.6 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 5 THEN CAST(comments_count * (0.5 + random() * 0.2) AS INTEGER)
        WHEN generate_series = 6 THEN CAST(comments_count * (0.4 + random() * 0.2) AS INTEGER)
    END as comments_count,
    subscription_motivation, category, grade, product, posted_at,
    NOW() - INTERVAL '1 day' * generate_series as collection_date
FROM campaign_instagram_posts 
CROSS JOIN generate_series(1, 6)
WHERE collection_date > NOW() - INTERVAL '1 hour';

-- 인스타그램 릴스 일자별 데이터 생성
INSERT INTO campaign_instagram_reels
(campaign_id, campaign_url, reel_id, username, display_name, follower_count,
 s3_thumbnail_url, video_view_count, subscription_motivation,
 category, grade, product, posted_at, collection_date)
SELECT 
    campaign_id, campaign_url, reel_id, username, display_name, follower_count,
    s3_thumbnail_url,
    CASE 
        WHEN generate_series = 1 THEN CAST(video_view_count * (1.0 + random() * 0.3) AS INTEGER)
        WHEN generate_series = 2 THEN CAST(video_view_count * (0.9 + random() * 0.3) AS INTEGER)
        WHEN generate_series = 3 THEN CAST(video_view_count * (0.8 + random() * 0.3) AS INTEGER)
        WHEN generate_series = 4 THEN CAST(video_view_count * (0.7 + random() * 0.3) AS INTEGER)
        WHEN generate_series = 5 THEN CAST(video_view_count * (0.6 + random() * 0.3) AS INTEGER)
        WHEN generate_series = 6 THEN CAST(video_view_count * (0.5 + random() * 0.3) AS INTEGER)
    END as video_view_count,
    subscription_motivation, category, grade, product, posted_at,
    NOW() - INTERVAL '1 day' * generate_series as collection_date
FROM campaign_instagram_reels
CROSS JOIN generate_series(1, 6)
WHERE collection_date > NOW() - INTERVAL '1 hour';

-- 블로그 일자별 데이터 생성
INSERT INTO campaign_blogs
(campaign_id, campaign_url, title, likes_count, comments_count, daily_visitors,
 keyword, ranking, product, posted_at, collection_date)
SELECT 
    campaign_id, campaign_url, title,
    CAST(likes_count * (0.8 + random() * 0.4) AS INTEGER) as likes_count,
    CAST(comments_count * (0.8 + random() * 0.4) AS INTEGER) as comments_count,
    CAST(daily_visitors * (0.8 + random() * 0.4) AS INTEGER) as daily_visitors,
    keyword, ranking, product, posted_at,
    NOW() - INTERVAL '1 day' * generate_series as collection_date
FROM campaign_blogs
CROSS JOIN generate_series(1, 6)
WHERE collection_date > NOW() - INTERVAL '1 hour';

-- 생성된 데이터 확인
SELECT 'Instagram Posts' as type, collection_date::date, COUNT(*) 
FROM campaign_instagram_posts 
GROUP BY collection_date::date 
ORDER BY collection_date::date DESC
UNION ALL
SELECT 'Instagram Reels' as type, collection_date::date, COUNT(*)
FROM campaign_instagram_reels 
GROUP BY collection_date::date 
ORDER BY collection_date::date DESC
UNION ALL
SELECT 'Blogs' as type, collection_date::date, COUNT(*)
FROM campaign_blogs 
GROUP BY collection_date::date 
ORDER BY collection_date::date DESC;