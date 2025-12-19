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
        
        # blog.naver.com/{blogId}/{logNo} 형태는 실제 포스트가 iframe(PostView.naver) 안에 있어
        # wrapper 페이지를 파싱하면 제목/댓글/게시일이 누락될 수 있음 → PostView URL로 변환
        parsed = urlparse(blog_url)
        blog_id = _extract_username_from_url(blog_url)
        log_no: Optional[str] = None
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        if parsed.netloc.endswith('blog.naver.com') and len(path_parts) >= 2:
            log_no = path_parts[1]

        # querystring 방식 logNo도 지원
        qs = parse_qs(parsed.query)
        if not log_no:
            q_log_no = qs.get('logNo') or qs.get('logno')
            if q_log_no and q_log_no[0]:
                log_no = q_log_no[0]

        # PostView.naver로 강제 접근 (가능한 경우)
        fetch_url = blog_url
        if blog_id and log_no and 'PostView.naver' not in blog_url:
            fetch_url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"

        response = requests.get(fetch_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 기본 정보 추출
        blog_info = {
            'url': blog_url,
            'title': None,
            'username': None,
            'content': None,
            'posted_at': None,   # datetime은 상위 레이어에서 파싱
            'post_date': None,   # 원문 문자열 (예: "2025. 12. 8. 12:40")
            'likes_count': 0,
            'comments_count': 0
        }
        
        # 제목 추출 - 여러 방법 시도 (실제 포스트 페이지 기준)
        title_selectors = [
            'h3.se-component-content',
            '.se-title-text',
            '.title_post',
            'h1',
            'h2',
            'h3',
            # 네이버 블로그 스마트에디터 제목
            'span.se-fs-',
            '[class*="se-fs-"]',
            # 메타 태그에서 제목 추출
            'meta[property="og:title"]',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                # 속성에서 추출 시도
                if selector.startswith('meta'):
                    title = title_elem.get('content', '')
                else:
                    # 텍스트 추출 전에 HTML 주석 제거
                    title_html = str(title_elem)
                    # HTML 주석 제거
                    title_html = re.sub(r'<!--.*?-->', '', title_html, flags=re.DOTALL)
                    # 다시 파싱하여 텍스트 추출
                    temp_soup = BeautifulSoup(title_html, 'html.parser')
                    title = temp_soup.get_text(strip=True)
                
                if title and len(title) > 0:
                    title = title.strip()
                    # HTML 엔티티 디코딩
                    title = title.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                    title = ' '.join(title.split())  # 연속된 공백 제거
                    if title and len(title) > 0:
                        blog_info['title'] = title
                        print(f"✅ Title extracted: '{title}'")
                        break
        
        # 메타 태그에서도 시도
        if not blog_info['title']:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                blog_info['title'] = og_title.get('content').strip()
        
        # title 태그에서도 시도
        if not blog_info['title']:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # "블로그명 : 게시물 제목" 형식에서 게시물 제목만 추출
                if ':' in title_text:
                    title_text = title_text.split(':', 1)[1].strip()
                blog_info['title'] = title_text

        # posted_at(게시일) 추출 (예: <span class="se_publishDate pcol2">2025. 12. 8. 12:40</span>)
        publish_elem = soup.select_one('span.se_publishDate') or soup.select_one('.se_publishDate')
        if publish_elem:
            date_text = publish_elem.get_text(strip=True)
            if date_text:
                blog_info['post_date'] = date_text

        # 댓글 수 추출 (예: <em id="commentCount" class="_commentCount">3</em>)
        comment_count_elem = soup.select_one('em#commentCount._commentCount') or soup.select_one('#commentCount')
        if comment_count_elem:
            cc = _extract_number(comment_count_elem.get_text(strip=True))
            if cc is not None:
                blog_info['comments_count'] = cc
        
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
        
        # 좋아요 수 추출 - 여러 방법 시도
        like_selectors = [
            '.like_count',
            '.cnt_like',
            '[data-like-count]',
            '.u_likeit_list_count',
            '.u_likeit_list_count_btn',
            # 네이버 블로그 좋아요 버튼
            'button[class*="like"]',
            'span[class*="like"]',
            'a[class*="like"]'
        ]
        
        for selector in like_selectors:
            like_elem = soup.select_one(selector)
            if like_elem:
                like_text = like_elem.get('data-like-count') or like_elem.get('data-count') or like_elem.get_text(strip=True)
                like_count = _extract_number(like_text)
                if like_count is not None and like_count > 0:
                    blog_info['likes_count'] = like_count
                    print(f"✅ Likes extracted: {like_count}")
                    break
        
        # 댓글 수 추출 - 여러 방법 시도
        comment_selectors = [
            # 네이버 블로그 최신 스타일 (우선순위 높음)
            '.num__OVfhz',  # 댓글 수 스팬
            '.comment_area__nxrQe .num__OVfhz',  # 댓글 영역 내 댓글 수
            'button.comment_btn__TUucZ .num__OVfhz',  # 댓글 버튼 내 댓글 수
            '.comment_btn__TUucZ .num__OVfhz',  # 댓글 버튼 내 댓글 수 (더 넓은 범위)
            # 기존 셀렉터들
            '.comment_count',
            '.cnt_comment',
            '[data-comment-count]',
            '.u_cbox_count',
            '.u_cbox_count_txt',
            # 네이버 블로그 댓글 수
            'span[class*="comment"]',
            'a[class*="comment"]',
            'button[class*="comment"]',
            # 댓글 영역 전체에서 숫자 찾기
            '.comment_area__nxrQe span.num__OVfhz',
            '.comment_area__nxrQe button span.num__OVfhz'
        ]
        
        for selector in comment_selectors:
            comment_elem = soup.select_one(selector)
            if comment_elem:
                comment_text = comment_elem.get('data-comment-count') or comment_elem.get('data-count') or comment_elem.get_text(strip=True)
                comment_count = _extract_number(comment_text)
                if comment_count is not None:
                    blog_info['comments_count'] = comment_count
                    print(f"✅ Comments extracted: {comment_count} (selector: {selector})")
                    break
        
        # 댓글 영역이 있지만 숫자를 못 찾은 경우, 댓글 영역 내 모든 숫자 시도
        if blog_info['comments_count'] == 0:
            comment_area = soup.select_one('.comment_area__nxrQe')
            if comment_area:
                # 댓글 영역 내 모든 숫자 텍스트 찾기
                all_text = comment_area.get_text(strip=True)
                numbers = re.findall(r'\d+', all_text)
                if numbers:
                    # 가장 큰 숫자를 댓글 수로 간주 (보통 댓글 수가 가장 큰 숫자)
                    try:
                        comment_count = max(int(n) for n in numbers if int(n) < 10000)  # 비정상적으로 큰 숫자 제외
                        blog_info['comments_count'] = comment_count
                        print(f"✅ Comments extracted from area: {comment_count}")
                    except (ValueError, TypeError):
                        pass
        
        # 최종 결과 로깅
        if blog_info.get('title'):
            print(f"✅ Blog info collected: title='{blog_info['title']}', likes={blog_info.get('likes_count', 0)}, comments={blog_info.get('comments_count', 0)}")
        else:
            print(f"⚠️ Title not found for {blog_url}")
        
        return blog_info
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching blog info from {blog_url}: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error in get_blog_info: {str(e)}")
        import traceback
        traceback.print_exc()
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