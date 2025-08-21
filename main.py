from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from get_blog import get_blog_info
import logging
import re

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Goodwave Blog API",
    description="네이버 블로그 정보를 추출하는 API",
    version="1.0.0"
)

class BlogUrlRequest(BaseModel):
    url: HttpUrl

class BlogInfoResponse(BaseModel):
    post_date: str
    post_likes: str
    post_comments: str
    url: str
    converted_url: str = None  # 변환된 URL 정보 추가

def convert_blog_url(url: str) -> str:
    """
    네이버 블로그 URL을 PostView 형태로 변환합니다.
    
    지원하는 형태:
    1. https://blog.naver.com/aaa2981/223951329398 -> PostView 형태로 변환
    2. https://blog.naver.com/PostView.naver?blogId=xxx&logNo=xxx -> 그대로 사용
    """
    # 이미 PostView 형태인 경우 그대로 반환
    if "PostView.naver" in url:
        return url
    
    # 짧은 형태의 URL 패턴: https://blog.naver.com/{blogId}/{logNo}
    short_pattern = r'https://blog\.naver\.com/([^/]+)/(\d+)'
    match = re.match(short_pattern, url)
    
    if match:
        blog_id = match.group(1)
        log_no = match.group(2)
        converted_url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
        logger.info(f"URL 변환: {url} -> {converted_url}")
        return converted_url
    
    # 변환할 수 없는 경우 원본 URL 반환
    logger.warning(f"URL 변환 실패, 원본 사용: {url}")
    return url

@app.get("/")
async def root():
    """API 상태 확인"""
    return {"message": "Goodwave Blog API가 정상적으로 실행 중입니다."}

@app.post("/blog-info", response_model=BlogInfoResponse)
async def get_blog_information(request: BlogUrlRequest):
    """
    네이버 블로그 URL을 입력받아 블로그 정보를 반환합니다.
    
    지원하는 URL 형태:
    - https://blog.naver.com/blogId/logNo (자동으로 PostView 형태로 변환)
    - https://blog.naver.com/PostView.naver?blogId=xxx&logNo=xxx
    
    반환값:
    - **post_date**: 게시 날짜 (YYYY-MM-DD 형식)
    - **post_likes**: 좋아요 수
    - **post_comments**: 댓글 수
    - **url**: 요청한 원본 URL
    - **converted_url**: 변환된 URL (변환이 있었던 경우)
    """
    try:
        original_url = str(request.url)
        logger.info(f"블로그 정보 요청: {original_url}")
        
        # URL 유효성 검증 (네이버 블로그인지 확인)
        if "blog.naver.com" not in original_url:
            raise HTTPException(
                status_code=400, 
                detail="네이버 블로그 URL만 지원됩니다."
            )
        
        # URL 변환
        converted_url = convert_blog_url(original_url)
        
        # 블로그 정보 추출
        blog_info = await get_blog_info(converted_url)
        
        logger.info(f"블로그 정보 추출 완료: {blog_info}")
        
        response = BlogInfoResponse(
            post_date=blog_info["post_date"],
            post_likes=blog_info["post_likes"],
            post_comments=blog_info["post_comments"],
            url=original_url
        )
        
        # URL이 변환되었다면 변환된 URL도 포함
        if converted_url != original_url:
            response.converted_url = converted_url
        
        return response
        
    except Exception as e:
        logger.error(f"블로그 정보 추출 실패: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"블로그 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "message": "API가 정상적으로 동작하고 있습니다."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 