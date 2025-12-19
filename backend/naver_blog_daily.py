"""네이버 블로그 일일 방문자 수 수집 모듈"""

import requests
import json
from typing import Optional, Dict
from xml.etree import ElementTree as ET


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
        
        # 응답이 XML인지 JSON인지 확인
        content_type = response.headers.get('content-type', '').lower()
        
        # XML 응답인 경우 (네이버 블로그 방문자 API는 XML 반환)
        if 'xml' in content_type or response.text.strip().startswith('<?xml'):
            try:
                # XML을 파싱하여 JSON 형식으로 변환
                root = ET.fromstring(response.text)
                visitor_data = {}
                
                # visitorcnt 요소들을 찾아서 날짜별 방문자 수 추출
                for visitorcnt in root.findall('.//visitorcnt'):
                    date_id = visitorcnt.get('id')
                    count = visitorcnt.get('cnt')
                    if date_id and count:
                        visitor_data[date_id] = count
                
                # JSON 문자열로 변환하여 반환
                return json.dumps(visitor_data)
            except ET.ParseError as e:
                print(f"❌ XML parse error from {api_url}: {str(e)}")
                print(f"   Response text (first 500 chars): {response.text[:500]}")
                return None
        
        # JSON 응답인 경우
        try:
            json.loads(response.text)
            return response.text
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response from {api_url}")
            print(f"   Response status: {response.status_code}")
            print(f"   Response headers: {dict(response.headers)}")
            print(f"   Response text (first 500 chars): {response.text[:500]}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching naver blog visitors from {api_url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_naver_blog_visitors: {str(e)}")
        return None