"""
인증 미들웨어
보고서 API를 제외한 모든 API에 인증을 요구합니다.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import List
from jose import JWTError, jwt
from app.core.config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    """인증 미들웨어 - 보고서 API는 공개, 나머지는 인증 필요"""
    
    def __init__(self, app, public_paths: List[str] = None):
        super().__init__(app)
        self.public_paths = public_paths or []
    
    def _is_public_path(self, path: str) -> bool:
        """경로가 공개 경로인지 확인"""
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        return False
    
    def _verify_token(self, token: str) -> bool:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return payload.get("sub") is not None
        except JWTError:
            return False
    
    async def dispatch(self, request: Request, call_next):
        """요청 처리"""
        # 공개 경로는 인증 체크 건너뛰기
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # OPTIONS 요청은 CORS preflight이므로 허용
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Authorization 헤더 확인
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Bearer 토큰 추출
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 토큰 검증
        if not self._verify_token(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return await call_next(request)
