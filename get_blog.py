import asyncio
from playwright.async_api import async_playwright
import re

def format_date(date_raw):
    """
    날짜 형식 변환: "2025. 7. 18. 16:21" -> "2025-07-18"
    """
    date_match = re.match(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*\d{2}:\d{2}', date_raw)
    if date_match:
        year, month, day = date_match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    else:
        return date_raw  # 변환 실패시 원본 유지

async def get_blog_info(post_url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # 디버깅 시 False로 유지
        page = await browser.new_page()

        await page.goto(post_url, wait_until="networkidle", timeout=120000)
        await page.wait_for_timeout(5000) # 로딩 안정화를 위한 추가 대기

        # --- 좋아요 수 ---
        try:
            # `strict mode violation` 해결 시도 1: get_by_role 사용 (더 견고할 수 있음)
            # "공감 18" 버튼을 찾아서 거기서 텍스트를 가져오거나, 그 안의 숫자를 찾습니다.
            # 이 글에 공감한 블로거 열고 닫기" 텍스트를 포함하는 버튼을 찾음
            # `filter(has_text="공감")`을 추가하여 '공감' 텍스트를 포함하는 버튼으로 필터링
            like_locator_attempt1 = page.get_by_role("button", name="공감").locator("em._count").first
            likes = await like_locator_attempt1.inner_text(timeout=10000) # 최대 10초 대기

        except Exception as e:
            print(f"좋아요 수 가져오기 실패 (시도 1): {e}")
            try:
                # `strict mode violation` 해결 시도 2: 첫 번째 매칭 요소만 선택
                # 여전히 `em.u_cnt._count`가 여러 개라면, 첫 번째만 가져옵니다.
                # 하지만 이 경우 원하지 않는 '18'이 선택될 수도 있으니 주의해야 합니다.
                like_locator_attempt2 = page.locator("em.u_cnt._count").first
                likes = await like_locator_attempt2.inner_text(timeout=10000)
            except Exception as e_retry:
                print(f"좋아요 수 가져오기 실패 (시도 2): {e_retry}")
                likes = "좋아요 없음"

        try:
            # <span class="se_publishDate pcol2">2025. 7. 18. 16:21</span>
            date_locator = page.locator("span.se_publishDate.pcol2")
            await date_locator.wait_for(timeout=30000)
            date_raw = await date_locator.inner_text()
            
            # 날짜 형식 변환
            date = format_date(date_raw)
        except Exception as e:
            print(f"날짜 가져오기 실패: {e}")
            date = "날짜 없음"

        # --- 댓글 수 ---
        try:
            # <em id="commentCount" class="_commentCount">2</em>
            comment_locator = page.locator("#commentCount")
            await comment_locator.wait_for(timeout=30000)
            comments = await comment_locator.inner_text()
        except Exception as e:
            print(f"댓글 수 가져오기 실패: {e}")
            comments = "댓글 없음"

        await browser.close()
        
        # 딕셔너리 형태로 반환
        return {
            "post_date": date,
            "post_likes": likes,
            "post_comments": comments
        }

async def main():
    post_url = "https://blog.naver.com/PostView.naver?blogId=1suhyeon&logNo=223938502707"
    blog_info = await get_blog_info(post_url)
    
    print(f"날짜: {blog_info['post_date']}")
    print(f"좋아요 수: {blog_info['post_likes']}")
    print(f"댓글 수: {blog_info['post_comments']}")

if __name__ == "__main__":
    asyncio.run(main())