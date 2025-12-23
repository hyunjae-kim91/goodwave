"""
IP 화이트리스트 미들웨어
보고서 공유 API를 제외한 모든 API에 IP 기반 접근 제어를 적용합니다.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import List, Set, Union
import ipaddress
from app.core.config import settings


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP 화이트리스트 미들웨어"""
    
    def __init__(self, app, allowed_ips: str = None, public_paths: List[str] = None):
        super().__init__(app)
        self.allowed_ips: Set[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]] = set()
        self.public_paths = public_paths or []
        
        # 허용된 IP 목록 파싱
        if allowed_ips:
            for ip_str in allowed_ips.split(','):
                ip_str = ip_str.strip()
                if not ip_str:
                    continue
                try:
                    # CIDR 표기법 지원 (예: 192.168.1.0/24)
                    if '/' in ip_str:
                        self.allowed_ips.add(ipaddress.ip_network(ip_str, strict=False))
                    else:
                        # 단일 IP 주소는 /32 또는 /128로 변환
                        ip = ipaddress.ip_address(ip_str)
                        if isinstance(ip, ipaddress.IPv4Address):
                            self.allowed_ips.add(ipaddress.ip_network(f"{ip_str}/32", strict=False))
                        else:
                            self.allowed_ips.add(ipaddress.ip_network(f"{ip_str}/128", strict=False))
                except ValueError as e:
                    print(f"⚠️ 잘못된 IP 주소 형식 무시: {ip_str} - {e}")
    
    def _is_public_path(self, path: str) -> bool:
        """경로가 공개 경로인지 확인"""
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        return False
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # X-Forwarded-For 헤더 확인 (프록시/로드밸런서 뒤에 있는 경우)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For는 여러 IP를 포함할 수 있음 (첫 번째가 원본 클라이언트)
            client_ip = forwarded_for.split(",")[0].strip()
            return client_ip
        
        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # 직접 연결인 경우
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_ip_allowed(self, client_ip: str) -> bool:
        """IP가 허용 목록에 있는지 확인"""
        # 허용 목록이 비어있으면 모든 IP 허용
        if not self.allowed_ips:
            return True
        
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            # 허용된 네트워크 중 하나에 포함되는지 확인
            for allowed_network in self.allowed_ips:
                if client_ip_obj in allowed_network:
                    return True
            return False
        except ValueError:
            # 잘못된 IP 형식
            print(f"⚠️ 잘못된 클라이언트 IP 형식: {client_ip}")
            return False
    
    async def dispatch(self, request: Request, call_next):
        """요청 처리"""
        # 공개 경로는 IP 체크 건너뛰기
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # 허용 목록이 설정되지 않았으면 모든 IP 허용
        if not self.allowed_ips:
            return await call_next(request)
        
        # 클라이언트 IP 추출
        client_ip = self._get_client_ip(request)
        
        # IP 허용 여부 확인
        if not self._is_ip_allowed(client_ip):
            print(f"🚫 접근 거부: IP {client_ip}가 {request.url.path}에 접근 시도")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Your IP address ({client_ip}) is not allowed."
            )
        
        print(f"✅ 접근 허용: IP {client_ip}가 {request.url.path}에 접근")
        return await call_next(request)
