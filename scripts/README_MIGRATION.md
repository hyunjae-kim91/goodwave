# 데이터베이스 마이그레이션 가이드

## CampaignReelCollectionJob 테이블에 likes_count, comments_count 컬럼 추가

### 방법 1: Python 스크립트 실행 (권장)

```bash
cd backend
python ../scripts/run_migration.py
```

**주의**: `.env` 파일에 `DATABASE_URL`이 설정되어 있어야 합니다.

### 방법 2: SQL 파일 직접 실행

PostgreSQL 클라이언트(psql)를 사용하여 직접 실행:

```bash
psql -h [호스트] -U [사용자명] -d [데이터베이스명] -f scripts/migration_add_likes_comments.sql
```

또는 psql에 연결한 후:

```sql
\i scripts/migration_add_likes_comments.sql
```

### 방법 3: Python 코드로 직접 실행

```python
from sqlalchemy import create_engine, text

# 데이터베이스 URL 설정
database_url = "postgresql://user:password@host:port/database"

engine = create_engine(database_url)

with engine.connect() as conn:
    # likes_count 컬럼 추가
    conn.execute(text("""
        ALTER TABLE campaign_reel_collection_jobs 
        ADD COLUMN IF NOT EXISTS likes_count INTEGER
    """))
    
    # comments_count 컬럼 추가
    conn.execute(text("""
        ALTER TABLE campaign_reel_collection_jobs 
        ADD COLUMN IF NOT EXISTS comments_count INTEGER
    """))
    
    conn.commit()
```

### 마이그레이션 확인

마이그레이션이 성공했는지 확인:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'campaign_reel_collection_jobs' 
AND column_name IN ('likes_count', 'comments_count');
```

### 롤백 (필요한 경우)

컬럼을 제거하려면:

```sql
ALTER TABLE campaign_reel_collection_jobs DROP COLUMN IF EXISTS likes_count;
ALTER TABLE campaign_reel_collection_jobs DROP COLUMN IF EXISTS comments_count;
```

