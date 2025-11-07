"""
PostgreSQL 시퀀스 자동 복구 유틸리티
UniqueViolation 에러 발생 시 자동으로 시퀀스를 리셋합니다.
"""
import logging
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def fix_table_sequence(db: Session, table_name: str) -> bool:
    """
    특정 테이블의 시퀀스를 현재 최대 ID + 1로 리셋합니다.
    
    Args:
        db: SQLAlchemy 세션
        table_name: 리셋할 테이블 이름
    
    Returns:
        성공 여부
    """
    try:
        # 현재 최대 ID 조회
        result = db.execute(text(f"SELECT MAX(id) FROM {table_name}"))
        max_id = result.scalar()
        
        if max_id is None:
            logger.warning(f"테이블 '{table_name}'이 비어있습니다")
            return False
        
        # 시퀀스 이름 (일반적으로 tablename_id_seq)
        sequence_name = f"{table_name}_id_seq"
        
        # 시퀀스를 최대 ID + 1로 설정
        new_value = max_id + 1
        db.execute(text(f"SELECT setval('{sequence_name}', {new_value}, false)"))
        db.commit()
        
        logger.info(f"✅ '{table_name}' 시퀀스를 {new_value}로 리셋했습니다 (최대 ID: {max_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ '{table_name}' 시퀀스 리셋 실패: {str(e)}")
        db.rollback()
        return False


def auto_fix_sequence_on_error(db: Session, error: Exception, table_name: str) -> bool:
    """
    UniqueViolation 에러 발생 시 자동으로 시퀀스를 리셋합니다.
    
    Args:
        db: SQLAlchemy 세션
        error: 발생한 에러
        table_name: 에러가 발생한 테이블 이름
    
    Returns:
        시퀀스 리셋 성공 여부
    """
    error_str = str(error)
    
    # UniqueViolation 에러인지 확인
    if "UniqueViolation" in error_str or "duplicate key" in error_str:
        # Primary key constraint 에러인지 확인
        if f"{table_name}_pkey" in error_str or "Key (id)=" in error_str:
            logger.warning(f"⚠️ '{table_name}'에서 ID 중복 에러 감지 - 시퀀스 자동 리셋 시도")
            
            # 세션 롤백
            db.rollback()
            
            # 시퀀스 리셋 시도
            if fix_table_sequence(db, table_name):
                logger.info(f"✅ '{table_name}' 시퀀스 자동 리셋 완료")
                return True
            else:
                logger.error(f"❌ '{table_name}' 시퀀스 자동 리셋 실패")
                return False
    
    return False


def safe_db_operation(db: Session, operation_func, table_name: str, max_retries: int = 2):
    """
    DB 작업을 안전하게 수행하고, UniqueViolation 에러 발생 시 자동으로 복구합니다.
    
    Args:
        db: SQLAlchemy 세션
        operation_func: 실행할 DB 작업 함수
        table_name: 작업 대상 테이블 이름
        max_retries: 최대 재시도 횟수
    
    Returns:
        작업 결과
    
    Raises:
        마지막 시도에서 발생한 에러
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            result = operation_func()
            return result
            
        except IntegrityError as e:
            last_error = e
            
            # 첫 번째 시도가 아니면 더 이상 재시도하지 않음
            if attempt >= max_retries:
                logger.error(f"❌ '{table_name}' 작업 최종 실패 (재시도 {max_retries}회)")
                raise
            
            # UniqueViolation 자동 복구 시도
            if auto_fix_sequence_on_error(db, e, table_name):
                logger.info(f"🔄 '{table_name}' 작업 재시도 중 (시도 {attempt + 2}/{max_retries + 1})")
                continue
            else:
                # 복구 실패하면 바로 예외 발생
                raise
        
        except Exception as e:
            # IntegrityError가 아닌 다른 에러는 바로 발생
            logger.error(f"❌ '{table_name}' 작업 중 예상치 못한 에러: {str(e)}")
            raise
    
    # 모든 재시도 실패
    if last_error:
        raise last_error


# 자주 사용하는 테이블들의 시퀀스를 한 번에 리셋
def fix_all_sequences(db: Session) -> dict:
    """
    모든 주요 테이블의 시퀀스를 리셋합니다.
    
    Returns:
        {table_name: success_bool} 형태의 딕셔너리
    """
    tables = [
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
    
    results = {}
    for table in tables:
        results[table] = fix_table_sequence(db, table)
    
    success_count = sum(1 for v in results.values() if v)
    logger.info(f"✅ 시퀀스 리셋 완료: {success_count}/{len(tables)} 테이블")
    
    return results

