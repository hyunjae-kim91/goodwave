#!/usr/bin/env python3
"""
CollectionSchedule 테이블에서 schedule_minute 컬럼 제거 마이그레이션
시간(시)만 사용하도록 변경
"""

import os
import sys

# backend 디렉토리를 Python 경로에 추가
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# .env 파일 로드
env_file = os.path.join(backend_dir, '.env')
if os.path.exists(env_file):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        pass

# 환경 변수에서 데이터베이스 URL 가져오기
database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("❌ DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    print("💡 .env 파일에서 DATABASE_URL을 확인하거나 환경 변수를 설정하세요.")
    sys.exit(1)

from sqlalchemy import create_engine, text

def run_migration():
    """마이그레이션 실행"""
    try:
        print("=" * 60)
        print("CollectionSchedule 테이블 schedule_minute 컬럼 제거")
        print("=" * 60)
        print(f"데이터베이스 URL: {database_url[:50]}..." if len(database_url) > 50 else f"데이터베이스 URL: {database_url}")
        print("=" * 60)
        
        # 데이터베이스 연결
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                # schedule_minute 컬럼 제거
                print("🗑️  schedule_minute 컬럼 제거 중...")
                conn.execute(text("""
                    ALTER TABLE collection_schedules 
                    DROP COLUMN IF EXISTS schedule_minute
                """))
                
                trans.commit()
                print("✅ 마이그레이션 완료!")
                
                # 결과 확인
                result = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'collection_schedules' 
                    AND column_name IN ('schedule_hour', 'schedule_minute')
                """))
                columns = result.fetchall()
                
                print("\n📊 현재 컬럼 상태:")
                for col in columns:
                    print(f"  - {col[0]}: {col[1]}")
                
                if not any(col[0] == 'schedule_minute' for col in columns):
                    print("\n✅ schedule_minute 컬럼이 성공적으로 제거되었습니다.")
                
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ 마이그레이션 실패: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    
    if success:
        print("=" * 60)
        print("✅ 모든 마이그레이션이 성공적으로 완료되었습니다!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ 마이그레이션 중 오류가 발생했습니다.")
        print("=" * 60)
        sys.exit(1)

