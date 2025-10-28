"""네이버 블로그 정보 수집 모듈"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import json
import re
from urllib.parse import urlparse, parse_qs


def get_blog_info(blog_url: str) -> Optional[Dict[str, Any]]:
    """네이버 블로그 게시물 정보 수집
    
    Args:
        blog_url: 네이버 블로그 게시물 URL
        
    Returns:
        블로그 정보 딕셔너리 또는 None
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(blog_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 기본 정보 추출
        blog_info = {
            'url': blog_url,
            'title': None,
            'username': None,
            'content': None,
            'posted_at': None,
            'likes_count': 0,
            'comments_count': 0
        }
        
        # 제목 추출
        title_selectors = [
            'h3.se-component-content',
            '.se-title-text',
            '.title_post',
            'h1',
            'h2',
            'h3'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                blog_info['title'] = title_elem.get_text(strip=True)
                break
        
        # 사용자명 추출
        username_selectors = [
            '.blog_author',
            '.nickname',
            '.writer',
            '[data-blog-id]'
        ]
        
        for selector in username_selectors:
            username_elem = soup.select_one(selector)
            if username_elem:
                username = username_elem.get('data-blog-id') or username_elem.get_text(strip=True)
                if username:
                    blog_info['username'] = username
                    break
        
        # URL에서 사용자명 추출 (fallback)
        if not blog_info['username']:
            blog_info['username'] = _extract_username_from_url(blog_url)
        
        # 컨텐츠 추출
        content_selectors = [
            '.se-main-container',
            '.se-component-content',
            '.post-content',
            '.entry-content',
            '#postViewArea'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 텍스트만 추출 (이미지, 링크 등 제외)
                content_text = content_elem.get_text(separator=' ', strip=True)
                if content_text and len(content_text) > 50:  # 최소 길이 체크
                    blog_info['content'] = content_text[:1000]  # 최대 1000자
                    break
        
        # 좋아요 수 추출
        like_selectors = [
            '.like_count',
            '.cnt_like',
            '[data-like-count]'
        ]
        
        for selector in like_selectors:
            like_elem = soup.select_one(selector)
            if like_elem:
                like_text = like_elem.get('data-like-count') or like_elem.get_text(strip=True)
                like_count = _extract_number(like_text)
                if like_count is not None:
                    blog_info['likes_count'] = like_count
                    break
        
        # 댓글 수 추출
        comment_selectors = [
            '.comment_count',
            '.cnt_comment',
            '[data-comment-count]'
        ]
        
        for selector in comment_selectors:
            comment_elem = soup.select_one(selector)
            if comment_elem:
                comment_text = comment_elem.get('data-comment-count') or comment_elem.get_text(strip=True)
                comment_count = _extract_number(comment_text)
                if comment_count is not None:
                    blog_info['comments_count'] = comment_count
                    break
        
        return blog_info
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching blog info from {blog_url}: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_blog_info: {str(e)}")
        return None


def _extract_username_from_url(url: str) -> Optional[str]:
    """URL에서 사용자명 추출"""
    try:
        parsed = urlparse(url)
        
        # blog.naver.com/username 형태
        if parsed.netloc.endswith('blog.naver.com'):
            path_parts = parsed.path.strip('/').split('/')
            if path_parts and path_parts[0]:
                return path_parts[0]
        
        # m.blog.naver.com/username 형태
        if parsed.netloc.endswith('m.blog.naver.com'):
            path_parts = parsed.path.strip('/').split('/')
            if path_parts and path_parts[0]:
                return path_parts[0]
        
        # PostView.naver 형태에서 blogId 추출
        if 'PostView.naver' in url:
            query_params = parse_qs(parsed.query)
            if 'blogId' in query_params:
                return query_params['blogId'][0]
        
        return None
        
    except Exception:
        return None


def _extract_number(text: str) -> Optional[int]:
    """텍스트에서 숫자 추출"""
    if not text:
        return None
    
    # 숫자만 추출
    numbers = re.findall(r'\d+', str(text))
    if numbers:
        try:
            return int(numbers[0])
        except ValueError:
            return None
    
    return None