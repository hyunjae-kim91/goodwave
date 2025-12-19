from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse, urlunparse
from app.core.config import settings
from app.db.ssh_tunnel import get_tunnel_status, start_ssh_tunnel

def get_database_url() -> str:
    """
    Get database URL, using local tunnel port if SSH tunnel is active.
    """
    tunnel_status = get_tunnel_status()
    
    if tunnel_status.get("enabled") and tunnel_status.get("active"):
        # SSH 터널이 활성화되어 있으면 로컬 포트로 연결
        parsed = urlparse(settings.database_url)
        # localhost와 터널 포트로 변경
        new_netloc = f"{parsed.username}:{parsed.password}@127.0.0.1:{settings.local_tunnel_port}"
        tunnel_url = urlunparse((
            parsed.scheme,
            new_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        return tunnel_url
    
    return settings.database_url

def _ensure_ssh_tunnel():
    """SSH 터널이 활성화되어 있으면 시작하고 완전히 시작될 때까지 기다림"""
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    
    if settings.use_ssh_tunnel:
        tunnel_status = get_tunnel_status()
        if not tunnel_status.get("active"):
            # 터널이 활성화되어 있지만 시작되지 않은 경우 시작 시도
            logger.info("SSH tunnel is enabled but not active. Starting tunnel...")
            tunnel = start_ssh_tunnel()
            if tunnel:
                # 터널이 완전히 시작될 때까지 최대 10초 대기
                max_wait = 10
                wait_time = 0
                while wait_time < max_wait:
                    if tunnel.is_active:
                        logger.info("SSH tunnel is now active")
                        break
                    time.sleep(0.5)
                    wait_time += 0.5
                
                if not tunnel.is_active:
                    logger.warning("SSH tunnel failed to start within timeout period. Continuing with direct connection...")
                    # 직접 연결을 시도하도록 함 (터널 없이)
            else:
                logger.warning("Failed to start SSH tunnel. Continuing with direct connection...")

# SSH 터널이 활성화되어 있으면 시작 (모듈 import 시점)
# 주의: 이 시점에 터널이 시작되지 않아도 에러를 발생시키지 않음
# 실제 연결 시도 시 터널이 필요하면 main.py의 lifespan에서 시작됨
_ensure_ssh_tunnel()

# 연결 풀 설정 증가 (기본값: pool_size=5, max_overflow=10)
# 워커와 API 요청이 동시에 많이 발생할 수 있으므로 충분한 크기로 설정
engine = create_engine(
    get_database_url(),
    pool_size=20,  # 기본 연결 풀 크기 증가
    max_overflow=30,  # 오버플로우 연결 수 증가
    pool_pre_ping=True,  # 연결 유효성 검사 (연결 끊김 방지)
    pool_recycle=3600,  # 1시간마다 연결 재사용
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()