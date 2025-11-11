#!/usr/bin/env python3
"""
SQL 마이그레이션 파일 실행 스크립트
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
    """마이그레이션 SQL 파일 실행"""
    try:
        # SQL 파일 읽기
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file = os.path.join(script_dir, 'migration_add_likes_comments.sql')
        
        if not os.path.exists(sql_file):
            print(f"❌ SQL 파일을 찾을 수 없습니다: {sql_file}")
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("=" * 60)
        print("CampaignReelCollectionJob 테이블 마이그레이션 시작")
        print("=" * 60)
        print(f"데이터베이스 URL: {database_url[:50]}..." if len(database_url) > 50 else f"데이터베이스 URL: {database_url}")
        print("=" * 60)
        
        # 데이터베이스 연결 및 SQL 실행
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                # SQL 실행
                conn.execute(text(sql_content))
                trans.commit()
                print("✅ 마이그레이션 완료!")
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

