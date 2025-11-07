"""
PostgreSQL 시퀀스 리셋 스크립트
ID 중복 오류를 해결하기 위해 모든 테이블의 시퀀스를 현재 최대 ID + 1로 리셋합니다.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# 데이터베이스 연결
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
    exit(1)

engine = create_engine(DATABASE_URL)

# 시퀀스를 리셋할 테이블 목록
TABLES_TO_FIX = [
    'influencer_analysis',
    'influencer_profiles',
    'influencer_reels',
    'influencer_posts',
    'influencer_classification_summaries',
    'classification_jobs',
    'collection_jobs',
    'campaigns',
    'campaign_urls',
    'campaign_instagram_reels',
    'campaign_blogs',
]

def fix_sequence(table_name: str):
    """특정 테이블의 시퀀스를 리셋합니다."""
    try:
        with engine.connect() as conn:
            # 현재 최대 ID 조회
            result = conn.execute(text(f"SELECT MAX(id) FROM {table_name}"))
            max_id = result.scalar()
            
            if max_id is None:
                print(f"⚠️  {table_name}: 테이블이 비어있습니다 (스킵)")
                return
            
            # 시퀀스 이름 (일반적으로 tablename_id_seq)
            sequence_name = f"{table_name}_id_seq"
            
            # 시퀀스를 최대 ID + 1로 설정
            new_value = max_id + 1
            conn.execute(text(f"SELECT setval('{sequence_name}', {new_value}, false)"))
            conn.commit()
            
            print(f"✅ {table_name}: 시퀀스를 {new_value}로 리셋했습니다 (현재 최대 ID: {max_id})")
            
    except Exception as e:
        print(f"❌ {table_name}: 오류 발생 - {str(e)}")

def main():
    print("=" * 60)
    print("PostgreSQL 시퀀스 리셋 시작")
    print("=" * 60)
    print()
    
    for table_name in TABLES_TO_FIX:
        fix_sequence(table_name)
    
    print()
    print("=" * 60)
    print("✅ 모든 시퀀스 리셋 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()

