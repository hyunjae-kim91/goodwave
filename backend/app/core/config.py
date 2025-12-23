from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

def _is_docker_environment() -> bool:
    """Docker 환경인지 확인"""
    # Docker 컨테이너 내부에는 .dockerenv 파일이 존재
    if Path("/.dockerenv").exists():
        return True
    # 또는 환경 변수로 확인
    if os.environ.get("DOCKER_CONTAINER") == "true":
        return True
    # cgroup을 통한 확인 (Linux)
    try:
        with open("/proc/self/cgroup", "r") as f:
            if "docker" in f.read():
                return True
    except (FileNotFoundError, IOError):
        pass
    return False

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/goodwave_report"
    
    # BrightData API
    brightdata_api_key: str
    brightdata_service_url: Optional[str] = None
    
    # AWS S3
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_bucket: str
    s3_region: str = "ap-northeast-2"
    
    # Naver API
    naver_client_id: str
    naver_secret_key: str
    
    # OpenAI
    openai_api_key: str
    openai_vision_model: str = "gpt-4-vision-preview"
    openai_text_model: str = "gpt-4o-mini"
    
    # FastAPI
    secret_key: str = "your-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    
    # IP Access Control
    # 허용된 IP 주소 목록 (쉼표로 구분, 빈 문자열이면 모든 IP 허용)
    # 예: "192.168.1.1,10.0.0.1" 또는 "192.168.1.0/24" (CIDR 표기법 지원)
    allowed_ips: str = ""
    # 보고서 API는 IP 제한 없이 공개 (기본값: True)
    public_report_apis: bool = True
    
    # Storage
    storage_provider: str = "s3"  # local or s3
    
    # SSH Tunnel (for local development to access RDS via EC2 bastion)
    # Docker 환경에서는 자동으로 False로 설정됨
    use_ssh_tunnel: bool = False
    ssh_host: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_port: int = 22
    ssh_pem_key_path: Optional[str] = None
    rds_host: Optional[str] = None
    rds_port: int = 5432
    local_tunnel_port: int = 5433
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Docker 환경에서는 SSH 터널을 자동으로 비활성화
        # 단, 환경 변수로 명시적으로 USE_SSH_TUNNEL=true로 설정된 경우는 예외
        if _is_docker_environment() and "USE_SSH_TUNNEL" not in os.environ:
            self.use_ssh_tunnel = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()
