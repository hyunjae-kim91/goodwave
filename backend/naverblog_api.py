"""네이버 블로그 검색 API 모듈"""

import requests
import json
from typing import Dict, Any, Optional, List
import urllib.parse


def get_naver_blog_api(keyword: str, client_id: str = None, client_secret: str = None, display: int = 100) -> Optional[Dict[str, Any]]:
    """네이버 블로그 검색 API 호출
    
    Args:
        keyword: 검색 키워드
        client_id: 네이버 API 클라이언트 ID
        client_secret: 네이버 API 클라이언트 시크릿
        display: 검색 결과 개수 (최대 100)
        
    Returns:
        검색 결과 딕셔너리 또는 None
    """
    try:
        # 환경변수에서 API 키 가져오기
        if not client_id or not client_secret:
            import os
            client_id = os.getenv('NAVER_CLIENT_ID')
            client_secret = os.getenv('NAVER_SECRET_KEY')
        
        if not client_id or not client_secret:
            print("Naver API credentials not found")
            return None
        
        # API 엔드포인트
        url = "https://openapi.naver.com/v1/search/blog.json"
        
        # 검색 파라미터
        params = {
            'query': keyword,
            'display': min(display, 100),  # 최대 100개
            'start': 1,
            'sort': 'sim'  # 정확도순
        }
        
        # 헤더 설정
        headers = {
            'X-Naver-Client-Id': client_id,
            'X-Naver-Client-Secret': client_secret,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # API 호출
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 응답 파싱
        data = response.json()
        
        # 응답 데이터 검증
        if not isinstance(data, dict):
            print(f"Invalid response format for keyword '{keyword}'")
            return None
        
        # 에러 체크
        if 'errorMessage' in data:
            print(f"Naver API error for keyword '{keyword}': {data['errorMessage']}")
            return None
        
        # 결과 정리
        result = {
            'total': data.get('total', 0),
            'start': data.get('start', 1),
            'display': data.get('display', 0),
            'items': []
        }
        
        # 아이템 정리
        items = data.get('items', [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    cleaned_item = {
                        'title': _clean_html_tags(item.get('title', '')),
                        'link': item.get('link', ''),
                        'description': _clean_html_tags(item.get('description', '')),
                        'bloggername': item.get('bloggername', ''),
                        'bloggerlink': item.get('bloggerlink', ''),
                        'postdate': item.get('postdate', '')
                    }
                    result['items'].append(cleaned_item)
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Naver API for keyword '{keyword}': {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing Naver API response for keyword '{keyword}': {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_naver_blog_api: {str(e)}")
        return None


def search_blog_ranking(blog_url: str, keyword: str, client_id: str = None, client_secret: str = None) -> Optional[int]:
    """특정 블로그 URL의 검색 순위 확인
    
    Args:
        blog_url: 찾을 블로그 URL
        keyword: 검색 키워드
        client_id: 네이버 API 클라이언트 ID
        client_secret: 네이버 API 클라이언트 시크릿
        
    Returns:
        순위 (1-100) 또는 None (100위 밖)
    """
    try:
        # 검색 결과 가져오기
        data = get_naver_blog_api(keyword, client_id, client_secret)
        if not data:
            return None
        
        items = data.get('items', [])
        if not isinstance(items, list):
            return None
        
        # URL 정규화
        target_url = _normalize_blog_url(blog_url)
        if not target_url:
            return None
        
        # 순위 찾기
        for i, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            
            item_url = item.get('link', '')
            normalized_item_url = _normalize_blog_url(item_url)
            
            if normalized_item_url and normalized_item_url == target_url:
                return i
        
        return None  # 100위 안에 없음
        
    except Exception as e:
        print(f"Error searching blog ranking: {str(e)}")
        return None


def _clean_html_tags(text: str) -> str:
    """HTML 태그 제거"""
    if not text:
        return ""
    
    import re
    # HTML 태그 제거
    clean_text = re.sub(r'<[^>]+>', '', text)
    # HTML 엔티티 디코딩
    clean_text = clean_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    clean_text = clean_text.replace('&quot;', '"').replace('&#39;', "'")
    
    return clean_text.strip()


def _normalize_blog_url(url: str) -> Optional[str]:
    """블로그 URL 정규화 (비교용)"""
    if not url:
        return None
    
    try:
        # URL 파싱
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        
        # 네이버 블로그 URL 처리
        if 'blog.naver.com' in parsed.netloc:
            # PostView.naver 형태
            if 'PostView.naver' in url:
                query_params = parse_qs(parsed.query)
                blog_id = query_params.get('blogId', [None])[0]
                log_no = query_params.get('logNo', [None])[0]
                if blog_id and log_no:
                    return f"blog.naver.com/{blog_id}/{log_no}"
            
            # 일반 형태: blog.naver.com/username/postno
            else:
                path_parts = parsed.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    return f"blog.naver.com/{path_parts[0]}/{path_parts[1]}"
        
        # 기타 블로그는 도메인+경로로 정규화
        return f"{parsed.netloc}{parsed.path}"
        
    except Exception:
        return None