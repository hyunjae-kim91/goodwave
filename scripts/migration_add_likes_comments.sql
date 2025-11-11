-- CampaignReelCollectionJob 테이블에 likes_count와 comments_count 컬럼 추가 마이그레이션

-- likes_count 컬럼 추가 (이미 존재하면 오류 무시)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'campaign_reel_collection_jobs' 
        AND column_name = 'likes_count'
    ) THEN
        ALTER TABLE campaign_reel_collection_jobs 
        ADD COLUMN likes_count INTEGER;
        RAISE NOTICE 'likes_count 컬럼이 추가되었습니다.';
    ELSE
        RAISE NOTICE 'likes_count 컬럼이 이미 존재합니다.';
    END IF;
END $$;

-- comments_count 컬럼 추가 (이미 존재하면 오류 무시)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'campaign_reel_collection_jobs' 
        AND column_name = 'comments_count'
    ) THEN
        ALTER TABLE campaign_reel_collection_jobs 
        ADD COLUMN comments_count INTEGER;
        RAISE NOTICE 'comments_count 컬럼이 추가되었습니다.';
    ELSE
        RAISE NOTICE 'comments_count 컬럼이 이미 존재합니다.';
    END IF;
END $$;

