-- Goodwave Report Database 초기화 스크립트

-- 데이터베이스 생성 확인
SELECT 'Database goodwave_report initialized successfully!' as message;

-- 확장 프로그램 활성화 (필요한 경우)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 초기 데이터베이스 설정 완료 메시지
-- 테이블은 애플리케이션 시작시 SQLAlchemy로 자동 생성됩니다.

-- 기존 인스타그램 테이블 grade 컬럼 길이 확장 (재실행 안전)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'instagram_posts'
          AND column_name = 'grade'
          AND character_maximum_length < 50
    ) THEN
        ALTER TABLE instagram_posts ALTER COLUMN grade TYPE VARCHAR(50);
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'instagram_reels'
          AND column_name = 'grade'
          AND character_maximum_length < 50
    ) THEN
        ALTER TABLE instagram_reels ALTER COLUMN grade TYPE VARCHAR(50);
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'campaign_instagram_posts'
          AND column_name = 'grade'
          AND character_maximum_length < 50
    ) THEN
        ALTER TABLE campaign_instagram_posts ALTER COLUMN grade TYPE VARCHAR(50);
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'campaign_instagram_reels'
          AND column_name = 'grade'
          AND character_maximum_length < 50
    ) THEN
        ALTER TABLE campaign_instagram_reels ALTER COLUMN grade TYPE VARCHAR(50);
    END IF;
END
$$;
