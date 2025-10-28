"""네이버 블로그 일일 방문자 수 수집 모듈"""

import requests
import json
from typing import Optional


def get_naver_blog_visitors(api_url: str) -> Optional[str]:
    """네이버 블로그 방문자 수 API 호출
    
    Args:
        api_url: 네이버 블로그 방문자 API URL
        
    Returns:
        JSON 문자열 또는 None
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://blog.naver.com/',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 응답이 유효한 JSON인지 확인
        try:
            json.loads(response.text)
            return response.text
        except json.JSONDecodeError:
            print(f"Invalid JSON response from {api_url}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching naver blog visitors from {api_url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_naver_blog_visitors: {str(e)}")
        return None