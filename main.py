from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from get_blog import get_blog_info
import logging

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

@app.get("/")
async def root():
    """API 상태 확인"""
    return {"message": "Goodwave Blog API가 정상적으로 실행 중입니다."}

@app.post("/blog-info", response_model=BlogInfoResponse)
async def get_blog_information(request: BlogUrlRequest):
    """
    네이버 블로그 URL을 입력받아 블로그 정보를 반환합니다.
    
    - **url**: 네이버 블로그 포스트 URL
    
    반환값:
    - **post_date**: 게시 날짜 (YYYY-MM-DD 형식)
    - **post_likes**: 좋아요 수
    - **post_comments**: 댓글 수
    - **url**: 요청한 URL
    """
    try:
        logger.info(f"블로그 정보 요청: {request.url}")
        
        # URL 유효성 검증 (네이버 블로그인지 확인)
        url_str = str(request.url)
        if "blog.naver.com" not in url_str:
            raise HTTPException(
                status_code=400, 
                detail="네이버 블로그 URL만 지원됩니다."
            )
        
        # 블로그 정보 추출
        blog_info = await get_blog_info(url_str)
        
        logger.info(f"블로그 정보 추출 완료: {blog_info}")
        
        return BlogInfoResponse(
            post_date=blog_info["post_date"],
            post_likes=blog_info["post_likes"],
            post_comments=blog_info["post_comments"],
            url=url_str
        )
        
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