#!/usr/bin/env python3
"""
CampaignReelCollectionJob 테이블에 likes_count와 comments_count 컬럼 추가 마이그레이션
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

# 프로젝트 루트를 Python 경로에 추가
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_dir)

try:
    from app.db.database import engine
    from app.core.config import settings
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    sys.exit(1)

def log_info(message):
    print(f"[INFO] {message}")

def log_success(message):
    print(f"✅ {message}")

def log_error(message):
    print(f"❌ {message}")

def check_column_exists(conn, table_name, column_name):
    """컬럼이 존재하는지 확인"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_columns():
    """likes_count와 comments_count 컬럼 추가"""
    try:
        with engine.connect() as conn:
            # 트랜잭션 시작
            trans = conn.begin()
            
            try:
                # 테이블 존재 확인
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                if 'campaign_reel_collection_jobs' not in tables:
                    log_error("campaign_reel_collection_jobs 테이블이 존재하지 않습니다.")
                    trans.rollback()
                    return False
                
                # likes_count 컬럼 추가
                if not check_column_exists(conn, 'campaign_reel_collection_jobs', 'likes_count'):
                    log_info("likes_count 컬럼 추가 중...")
                    conn.execute(text("""
                        ALTER TABLE campaign_reel_collection_jobs 
                        ADD COLUMN likes_count INTEGER
                    """))
                    log_success("likes_count 컬럼 추가 완료")
                else:
                    log_info("likes_count 컬럼이 이미 존재합니다.")
                
                # comments_count 컬럼 추가
                if not check_column_exists(conn, 'campaign_reel_collection_jobs', 'comments_count'):
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

