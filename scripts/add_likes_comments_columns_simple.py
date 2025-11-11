#!/usr/bin/env python3
"""
CampaignReelCollectionJob 테이블에 likes_count와 comments_count 컬럼 추가 마이그레이션
간단한 SQL 실행 버전
"""

import os
import sys

# backend 디렉토리를 Python 경로에 추가
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# .env 파일 경로 설정 (backend 디렉토리 기준)
env_file = os.path.join(backend_dir, '.env')
if os.path.exists(env_file):
    from dotenv import load_dotenv
    load_dotenv(env_file)

from sqlalchemy import create_engine, text

# config에서 데이터베이스 URL 가져오기
try:
    from app.core.config import settings
    database_url = settings.database_url
except Exception as e:
    print(f"⚠️ config에서 데이터베이스 URL을 가져오는 중 오류: {e}")
    # config를 import할 수 없으면 환경 변수에서 가져오기
    database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("❌ DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    print("💡 .env 파일에서 DATABASE_URL을 확인하거나 환경 변수를 설정하세요.")
    sys.exit(1)

def log_info(message):
    print(f"[INFO] {message}")

def log_success(message):
    print(f"✅ {message}")

def log_error(message):
    print(f"❌ {message}")

def add_columns():
    """likes_count와 comments_count 컬럼 추가"""
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # 트랜잭션 시작
            trans = conn.begin()
            
            try:
                # 테이블 존재 확인
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'campaign_reel_collection_jobs'
                    )
                """))
                table_exists = result.fetchone()[0]
                
                if not table_exists:
                    log_error("campaign_reel_collection_jobs 테이블이 존재하지 않습니다.")
                    trans.rollback()
                    return False
                
                # likes_count 컬럼 존재 확인 및 추가
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'campaign_reel_collection_jobs' 
                        AND column_name = 'likes_count'
                    )
                """))
                likes_exists = result.fetchone()[0]
                
                if not likes_exists:
                    log_info("likes_count 컬럼 추가 중...")
                    conn.execute(text("""
                        ALTER TABLE campaign_reel_collection_jobs 
                        ADD COLUMN likes_count INTEGER
                    """))
                    log_success("likes_count 컬럼 추가 완료")
                else:
                    log_info("likes_count 컬럼이 이미 존재합니다.")
                
                # comments_count 컬럼 존재 확인 및 추가
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'campaign_reel_collection_jobs' 
                        AND column_name = 'comments_count'
                    )
                """))
                comments_exists = result.fetchone()[0]
                
                if not comments_exists:
                    log_info("comments_count 컬럼 추가 중...")
                    conn.execute(text("""
                        ALTER TABLE campaign_reel_collection_jobs 
                        ADD COLUMN comments_count INTEGER
                    """))
                    log_success("comments_count 컬럼 추가 완료")
                else:
                    log_info("comments_count 컬럼이 이미 존재합니다.")
                
                # 커밋
                trans.commit()
                log_success("마이그레이션 완료!")
                return True
                
            except Exception as e:
                trans.rollback()
                log_error(f"마이그레이션 실패: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        log_error(f"데이터베이스 연결 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("CampaignReelCollectionJob 테이블 마이그레이션 시작")
    print("=" * 60)
    print(f"데이터베이스 URL: {database_url[:50]}..." if len(database_url) > 50 else f"데이터베이스 URL: {database_url}")
    print("=" * 60)
    
    success = add_columns()
    
    if success:
        print("=" * 60)
        log_success("모든 마이그레이션이 성공적으로 완료되었습니다!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        log_error("마이그레이션 중 오류가 발생했습니다.")
        print("=" * 60)
        sys.exit(1)

