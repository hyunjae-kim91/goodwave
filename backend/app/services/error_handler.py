import logging
import traceback
from typing import Any, Dict, List, Optional, Union
from functools import wraps

logger = logging.getLogger(__name__)

class DataValidationError(Exception):
    """데이터 검증 오류"""
    pass

class APIResponseError(Exception):
    """API 응답 오류"""
    pass

def safe_get_list(data: Any, key: str, default: Optional[List] = None) -> List:
    """
    안전하게 리스트를 가져오는 함수
    
    Args:
        data: 데이터 딕셔너리
        key: 키
        default: 기본값 (None이면 빈 리스트)
    
    Returns:
        List: 안전한 리스트
    """
    if default is None:
        default = []
    
    if not isinstance(data, dict):
        logger.warning(f"Expected dict for safe_get_list, got {type(data)}")
        return default
    
    value = data.get(key, default)
    if not isinstance(value, list):
        logger.warning(f"Expected list for key '{key}', got {type(value)}: {value}")
        return default
    
    return value

def safe_get_dict(data: Any, key: str, default: Optional[Dict] = None) -> Dict:
    """
    안전하게 딕셔너리를 가져오는 함수
    
    Args:
        data: 데이터 딕셔너리
        key: 키
        default: 기본값 (None이면 빈 딕셔너리)
    
    Returns:
        Dict: 안전한 딕셔너리
    """
    if default is None:
        default = {}
    
    if not isinstance(data, dict):
        logger.warning(f"Expected dict for safe_get_dict, got {type(data)}")
        return default
    
    value = data.get(key, default)
    if not isinstance(value, dict):
        logger.warning(f"Expected dict for key '{key}', got {type(value)}: {value}")
        return default
    
    return value

def validate_response_data(data: Any, expected_type: type = dict) -> bool:
    """
    API 응답 데이터 검증
    
    Args:
        data: 검증할 데이터
        expected_type: 예상 타입
    
    Returns:
        bool: 유효하면 True
    """
    if data is None:
        logger.error("Response data is None")
        return False
    
    if not isinstance(data, expected_type):
        logger.error(f"Invalid response data type: expected {expected_type}, got {type(data)}")
        return False
    
    return True

def handle_api_errors(func):
    """
    API 함수의 오류를 처리하는 데코레이터
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            func_name = func.__name__
            logger.error(f"Error in {func_name}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # 함수가 리스트를 반환해야 하는 경우
            if 'collect' in func_name or 'process' in func_name:
                return []
            # 함수가 딕셔너리를 반환해야 하는 경우
            elif 'get' in func_name or 'fetch' in func_name:
                return {}
            # 기본적으로 None 반환
            else:
                return None
    
    return wrapper

def log_collection_progress(username: str, data_type: str, status: str, message: str = ""):
    """
    수집 진행상황 로깅
    
    Args:
        username: 사용자명
        data_type: 데이터 타입 (profile, posts, reels)
        status: 상태 (pending, processing, completed, failed)
        message: 추가 메시지
    """
    emoji_map = {
        'pending': '⏳',
        'processing': '🔄', 
        'completed': '✅',
        'failed': '❌'
    }
    
    emoji = emoji_map.get(status, '📝')
    log_message = f"{emoji} [{username}] {data_type}: {status}"
    if message:
        log_message += f" - {message}"
    
    if status == 'failed':
        logger.error(log_message)
    elif status == 'completed':
        logger.info(log_message)
    else:
        logger.debug(log_message)

def validate_instagram_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    인스타그램 데이터 검증 및 정제
    
    Args:
        data: 원본 데이터
    
    Returns:
        Dict: 검증된 데이터
    """
    validated = {}
    
    # 필수 필드 검증
    validated['post_id'] = data.get('id', '')
    validated['username'] = data.get('username', '')
    validated['display_name'] = data.get('display_name', '')
    
    # 숫자 필드 안전 처리
    try:
        validated['follower_count'] = int(data.get('follower_count', 0))
    except (ValueError, TypeError):
        validated['follower_count'] = 0
    
    try:
        validated['likes_count'] = int(data.get('likes_count', 0))
    except (ValueError, TypeError):
        validated['likes_count'] = 0
    
    try:
        validated['comments_count'] = int(data.get('comments_count', 0))
    except (ValueError, TypeError):
        validated['comments_count'] = 0
    
    # URL 필드
    validated['thumbnail_url'] = data.get('thumbnail_url', '')
    
    # 날짜 필드
    validated['posted_at'] = data.get('posted_at')
    
    return validated

def validate_blog_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    블로그 데이터 검증 및 정제
    
    Args:
        data: 원본 데이터
    
    Returns:
        Dict: 검증된 데이터
    """
    validated = {}
    
    # 필수 필드
    validated['url'] = data.get('url', '')
    validated['title'] = data.get('title', '')
    
    # 숫자 필드 안전 처리
    try:
        validated['likes_count'] = int(data.get('likes_count', 0))
    except (ValueError, TypeError):
        validated['likes_count'] = 0
    
    try:
        validated['comments_count'] = int(data.get('comments_count', 0))
    except (ValueError, TypeError):
        validated['comments_count'] = 0
    
    try:
        validated['daily_visitors'] = int(data.get('daily_visitors', 0))
    except (ValueError, TypeError):
        validated['daily_visitors'] = 0
    
    # 날짜 필드
    validated['posted_at'] = data.get('posted_at')
    validated['collected_at'] = data.get('collected_at')
    
    return validated

class CollectionErrorTracker:
    """수집 과정에서 발생하는 오류를 추적"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def add_error(self, error: str, context: str = ""):
        """오류 추가"""
        error_entry = {
            'error': error,
            'context': context,
            'timestamp': str(logger)
        }
        self.errors.append(error_entry)
        logger.error(f"Collection Error [{context}]: {error}")
    
    def add_warning(self, warning: str, context: str = ""):
        """경고 추가"""
        warning_entry = {
            'warning': warning,
            'context': context,
            'timestamp': str(logger)
        }
        self.warnings.append(warning_entry)
        logger.warning(f"Collection Warning [{context}]: {warning}")
    
    def get_summary(self) -> Dict[str, Any]:
        """오류 요약 반환"""
        return {
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def has_errors(self) -> bool:
        """오류가 있는지 확인"""
        return len(self.errors) > 0