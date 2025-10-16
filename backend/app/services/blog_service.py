import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from app.core.config import settings

# 루트 경로에 있는 playwright 기반 스크립트들을 불러오기 위한 sys.path 보정
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from naver_blog_daily import get_naver_blog_visitors  # type: ignore  # 외부 스크립트 활용
from naverblog import get_blog_info  # type: ignore
from naverblog_api import get_naver_blog_api  # type: ignore

class BlogService:
    def __init__(self):
        self.naver_client_id = settings.naver_client_id
        self.naver_secret_key = settings.naver_secret_key

    async def collect_blog_data(self, blog_url: str) -> Optional[Dict[str, Any]]:
        """블로그 게시물 데이터 수집"""
        try:
            # 블로그 게시물 기본 정보 수집
            blog_data = await self._get_blog_post_info(blog_url)
            if not blog_data:
                return None

            if not blog_data.get('username'):
                blog_data['username'] = self._extract_blog_username(blog_url)

            # 일일 방문자 수 수집
            daily_visitors = await self._get_daily_visitors(blog_url)
            blog_data['daily_visitors'] = daily_visitors

            blog_data['rankings'] = []
            return blog_data

        except Exception as e:
            print(f"Error in collect_blog_data: {str(e)}")
            return None

    async def _get_blog_post_info(self, blog_url: str) -> Optional[Dict[str, Any]]:
        """블로그 게시물 기본 정보 수집"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # 네이버 블로그는 playwright 기반 수집으로 대체
            if 'blog.naver.com' in blog_url:
                return await self._get_naver_blog_with_playwright(blog_url)

            response = requests.get(blog_url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 티스토리 블로그 파싱
            if 'tistory.com' in blog_url:
                return await self._parse_tistory_blog(soup, blog_url)
            else:
                # 일반 블로그 파싱
                return await self._parse_general_blog(soup, blog_url)

        except Exception as e:
            print(f"Error getting blog post info: {str(e)}")
            return None

    async def _get_naver_blog_with_playwright(self, url: str) -> Dict[str, Any]:
        """네이버 블로그는 playwright 스크립트를 사용해 실제 수치를 수집"""
        loop = asyncio.get_running_loop()
        try:
            raw_info = await loop.run_in_executor(None, get_blog_info, url)
        except Exception as e:
            print(f"Error fetching Naver blog via Playwright: {str(e)}")
            return {}

        if not raw_info:
            return {}

        title = raw_info.get('post_title') or "제목 없음"
        likes_api = await self._get_like_count(url)
        likes = likes_api if likes_api else self._safe_int(raw_info.get('post_likes'))
        comments = self._safe_int(raw_info.get('post_comments'))
        posted_at = self._parse_blog_date(raw_info.get('post_date')) if raw_info.get('post_date') else None
        username = self._extract_blog_username(url)

        return {
            'url': url,
            'title': title,
            'likes_count': likes,
            'comments_count': comments,
            'posted_at': posted_at,
            'username': username,
            'collected_at': datetime.now()
        }

    async def _parse_tistory_blog(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """티스토리 블로그 파싱"""
        try:
            # 제목 추출
            title_element = soup.find('h1') or soup.find('h2') or soup.find('.title')
            title = title_element.get_text().strip() if title_element else "제목 없음"
            
            # 좋아요/댓글 수는 티스토리 API나 특별한 방법이 필요할 수 있음
            likes_count = 0
            comments_count = 0
            
            # 포스팅 날짜 추출
            date_element = soup.find('.date') or soup.find('time')
            posted_at = self._parse_blog_date(date_element.get_text()) if date_element else None
            
            return {
                'url': url,
                'title': title,
                'likes_count': likes_count,
                'comments_count': comments_count,
                'posted_at': posted_at,
                'collected_at': datetime.now()
            }
            
        except Exception as e:
            print(f"Error parsing Tistory blog: {str(e)}")
            return {}

    async def _parse_general_blog(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """일반 블로그 파싱"""
        try:
            # 제목 추출 (여러 가능성 시도)
            title_element = (soup.find('h1') or 
                           soup.find('h2') or 
                           soup.find('.title') or 
                           soup.find('#title') or
                           soup.find('title'))
            title = title_element.get_text().strip() if title_element else "제목 없음"
            
            return {
                'url': url,
                'title': title,
                'likes_count': 0,
                'comments_count': 0,
                'posted_at': None,
                'collected_at': datetime.now()
            }
            
        except Exception as e:
            print(f"Error parsing general blog: {str(e)}")
            return {}

    async def _get_daily_visitors(self, blog_url: str) -> int:
        """일일 방문자 수 수집 (네이버 블로그 전용)"""
        try:
            if 'blog.naver.com' not in blog_url:
                return 0

            api_url = self._build_naver_visitor_api_url(blog_url)
            if not api_url:
                return 0

            loop = asyncio.get_running_loop()
            raw_json = await loop.run_in_executor(None, get_naver_blog_visitors, api_url)
            if not raw_json:
                return 0

            data = json.loads(raw_json)
            if not isinstance(data, dict) or not data:
                return 0

            latest_date = max(data.keys())
            latest_value = data.get(latest_date, 0)
            return int(latest_value)

        except Exception as e:
            print(f"Error getting daily visitors: {str(e)}")
            return 0

    def _build_naver_visitor_api_url(self, blog_url: str) -> Optional[str]:
        username = self._extract_blog_username(blog_url)
        if not username:
            return None
        return f"https://blog.naver.com/NVisitorgp4Ajax.nhn?blogId={username}"

    def _extract_blog_username(self, blog_url: str) -> Optional[str]:
        try:
            parsed = urlparse(blog_url)
            if not parsed.netloc:
                return None

            if parsed.netloc.endswith('blog.naver.com'):
                path_parts = [part for part in parsed.path.split('/') if part]
                if path_parts:
                    return path_parts[0]

            if parsed.netloc.endswith('m.blog.naver.com'):
                path_parts = [part for part in parsed.path.split('/') if part]
                if path_parts:
                    return path_parts[0]

            # PostView.naver 방식 처리
            if 'blogId' in parsed.query:
                qs = parse_qs(parsed.query)
                bid = qs.get('blogId')
                if bid and bid[0]:
                    return bid[0]

            return None
        except Exception:
            return None

    def _extract_blog_log_no(self, blog_url: str) -> Optional[str]:
        try:
            parsed = urlparse(blog_url)
            path_parts = [part for part in parsed.path.split('/') if part]
            if parsed.netloc.endswith('blog.naver.com') or parsed.netloc.endswith('m.blog.naver.com'):
                if len(path_parts) >= 2:
                    return path_parts[1]

            qs = parse_qs(parsed.query)
            log_no = qs.get('logNo') or qs.get('logno')
            if log_no and log_no[0]:
                return log_no[0]

            return None
        except Exception:
            return None

    def _build_naver_entry_id(self, blog_url: str) -> Optional[str]:
        blog_id = self._extract_blog_username(blog_url)
        log_no = self._extract_blog_log_no(blog_url)
        if not blog_id or not log_no:
            return None
        return f"{blog_id}_{log_no}"

    async def _get_like_count(self, blog_url: str) -> int:
        entry_id = self._build_naver_entry_id(blog_url)
        if not entry_id:
            return 0

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._request_like_count, entry_id)

    def _request_like_count(self, entry_id: str) -> int:
        try:
            api_url = (
                "https://apis.naver.com/blogserver/like/v1/search/contents"
                "?suppress_response_codes=true&pool=blogid&isDuplication=false"
                f"&cssIds=MULTI_PC%2CBLOG_PC&displayId=BLOG&q=BLOG%5B{entry_id}%5D"
            )
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Referer': 'https://blog.naver.com/'
            }
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code != 200:
                return 0

            data = response.json()
            contents = data.get('contents') if isinstance(data, dict) else None
            if not contents:
                return 0

            for item in contents:
                if not isinstance(item, dict):
                    continue
                reactions = item.get('reactions')
                if not reactions:
                    continue
                for reaction in reactions:
                    if (
                        isinstance(reaction, dict)
                        and reaction.get('reactionType') == 'like'
                        and isinstance(reaction.get('count'), (int, float))
                    ):
                        return int(reaction['count'])

            return 0
        except Exception:
            return 0

    def _normalize_blog_url(self, blog_url: str) -> Optional[str]:
        try:
            parsed = urlparse(blog_url)
            qs = parse_qs(parsed.query)

            blog_id: Optional[str] = None
            log_no: Optional[str] = None

            path_parts = [part for part in parsed.path.split('/') if part]
            if parsed.netloc.endswith('blog.naver.com') or parsed.netloc.endswith('m.blog.naver.com'):
                if len(path_parts) >= 2:
                    blog_id = path_parts[0]
                    log_no = path_parts[1]
                elif len(path_parts) >= 1:
                    blog_id = path_parts[0]

            if 'blogId' in qs and qs['blogId']:
                blog_id = blog_id or qs['blogId'][0]
            if 'logNo' in qs and qs['logNo']:
                log_no = log_no or qs['logNo'][0]

            if blog_id and log_no:
                return f"{blog_id.strip().lower()}/{log_no.strip()}"
            if blog_id:
                return blog_id.strip().lower()

            return parsed.geturl().rstrip('/')
        except Exception:
            return None

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            if value is None:
                return 0
            if isinstance(value, int):
                result = value
            else:
                digits = re.sub(r"[^\d]", "", str(value))
                result = int(digits) if digits else 0
            # Scale down obviously malformed large numbers until within a reasonable range
            max_reasonable = 10_000
            while result > max_reasonable:
                result //= 10
                if result == 0:
                    break
            return result
        except Exception:
            return 0

    def _extract_keywords_from_title(self, title: str) -> List[str]:
        """제목에서 키워드 추출"""
        try:
            # 한글, 영어, 숫자만 추출하고 공백으로 분리
            keywords = re.findall(r'[가-힣a-zA-Z0-9]+', title)
            
            # 2글자 이상의 키워드만 선택
            keywords = [kw for kw in keywords if len(kw) >= 2]
            
            # 상위 5개 키워드만 선택
            return keywords[:5]
            
        except Exception as e:
            print(f"Error extracting keywords: {str(e)}")
            return []

    async def _check_blog_ranking(self, blog_url: str, keyword: str) -> Optional[int]:
        """네이버 블로그 검색에서 해당 URL의 순위 확인"""
        try:
            if not self.naver_client_id or not self.naver_secret_key:
                return None

            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, get_naver_blog_api, keyword)
            if not data or not isinstance(data, dict):
                print(f"Invalid response data for keyword '{keyword}'")
                return None

            items = data.get('items', [])
            if not isinstance(items, list):
                print(f"Invalid items data type for keyword '{keyword}': expected list, got {type(items)}")
                return None

            target_key = self._normalize_blog_url(blog_url)
            if not target_key:
                return None

            for i, item in enumerate(items, 1):
                if not item or not isinstance(item, dict):
                    continue
                link = item.get('link')
                if not link:
                    continue
                candidate_key = self._normalize_blog_url(link)
                if candidate_key and candidate_key == target_key:
                    return i

            return None  # 100위 안에 없음

        except Exception as e:
            print(f"Error checking blog ranking: {str(e)}")
            return None

    def _parse_blog_date(self, date_string: str) -> Optional[datetime]:
        """블로그 날짜 문자열을 datetime 객체로 변환"""
        if not date_string:
            return None
            
        try:
            # 여러 날짜 형식 시도
            date_formats = [
                '%Y.%m.%d',
                '%Y-%m-%d',
                '%Y.%m.%d.',
                '%Y년 %m월 %d일'
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_string.strip(), fmt)
                except ValueError:
                    continue
                    
            return None
        except Exception as e:
            print(f"Error parsing date: {str(e)}")
            return None

blog_service = BlogService()
