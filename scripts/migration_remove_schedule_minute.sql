-- CollectionSchedule 테이블에서 schedule_minute 컬럼 제거
-- 시간(시)만 사용하도록 변경

-- schedule_minute 컬럼 제거
ALTER TABLE collection_schedules 
DROP COLUMN IF EXISTS schedule_minute;

