from contextlib import asynccontextmanager
from sqlalchemy import text

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import engine, SessionLocal
from app.db import models
from app.db.ssh_tunnel import start_ssh_tunnel, stop_ssh_tunnel
from app.api import campaigns, reports, admin, influencer_ingest, influencer_files, influencer_classification, influencer_prompt, progress_stream, unified_reports, auth
from app.services.collection_worker import start_collection_worker, stop_collection_worker
from app.services.classification_worker import start_classification_worker, stop_classification_worker
from app.services.campaign_schedule_runner import start_campaign_schedule_runner, stop_campaign_schedule_runner
from app.services.grade_service import instagram_grade_service
from app.middleware.ip_whitelist import IPWhitelistMiddleware
from app.middleware.auth_middleware import AuthMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    # SSH 터널 시작 (설정되어 있는 경우)
    if settings.use_ssh_tunnel:
        print("Starting SSH tunnel...")
        tunnel = start_ssh_tunnel()
        if tunnel:
            print(f"SSH tunnel established on localhost:{settings.local_tunnel_port}")
            # SSH 터널이 시작된 후 engine 재생성을 위해 잠시 대기
            import time
            time.sleep(1)
        else:
            print("Warning: SSH tunnel failed to start. Continuing with direct connection...")
    
    # SSH 터널이 시작된 후 테이블 생성 및 초기화
    print("Connecting to database...")
    try:
        # DB 연결 테스트
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ Database connection successful!")
        
        # 테이블 생성
        models.Base.metadata.create_all(bind=engine)
        print("✅ Database tables ready")
        
        # 세션으로 추가 테스트 및 초기화
        session = SessionLocal()
        try:
            # 간단한 쿼리로 연결 확인
            test_query = session.execute(text("SELECT COUNT(*) FROM collection_schedules"))
            schedule_count = test_query.scalar()
            print(f"✅ Database query test successful (found {schedule_count} schedules)")
            
            instagram_grade_service.ensure_default_thresholds(session)
            print("✅ Default thresholds ensured")
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    await start_collection_worker()
    await start_classification_worker()
    await start_campaign_schedule_runner()
    try:
        yield
    finally:
        print("Shutting down...")
        stop_campaign_schedule_runner()
        stop_classification_worker()
        stop_collection_worker()
        # SSH 터널 종료
        if settings.use_ssh_tunnel:
            print("Stopping SSH tunnel...")
            stop_ssh_tunnel()

app = FastAPI(
    title="Goodwave Report API",
    description="Instagram and Blog Data Collection & Reporting System",
    version="1.0.0",
    lifespan=lifespan
)

# 인증 미들웨어 (보고서 API는 공개, 나머지는 인증 필요)
# 보고서 공유 API는 전체 공개로 설정
public_paths = [
    "/api/reports",  # 보고서 API
    "/api/unified-reports",  # 통합 보고서 API
    "/api/auth",  # 인증 API (공개)
    "/health",  # 헬스 체크
    "/",  # 루트 경로
]

# 인증 미들웨어 추가 (CORS 미들웨어 전에 추가)
app.add_middleware(
    AuthMiddleware,
    public_paths=public_paths
)
print("✅ 인증 시스템 활성화 (ID/비밀번호 기반)")
print(f"🌐 공개 경로: {', '.join(public_paths)}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Nginx가 프록시하므로 모든 origin 허용
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static files for uploaded images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(unified_reports.router, prefix="/api/unified-reports", tags=["unified-reports"])

# Include influencer analysis routers
app.include_router(influencer_ingest.router, prefix="/api", tags=["influencer-ingest"])
app.include_router(influencer_files.router, prefix="/api", tags=["influencer-files"])
app.include_router(influencer_classification.router, prefix="/api", tags=["influencer-classification"])
app.include_router(influencer_prompt.router, prefix="/api", tags=["influencer-prompt"])
app.include_router(progress_stream.router, prefix="/api", tags=["progress-stream"])

@app.get("/")
async def root():
    return {"message": "Goodwave Report API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/check-ip-access")
async def check_ip_access(request: Request):
    """클라이언트 IP가 허용 목록에 있는지 확인하는 API (공개 경로)"""
    from app.middleware.ip_whitelist import IPWhitelistMiddleware
    
    # 클라이언트 IP 추출
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip.strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"
    
    # IP 허용 여부 확인
    if not settings.allowed_ips:
        # IP 제한이 설정되지 않았으면 모든 IP 허용
        return {
            "allowed": True,
            "ip": client_ip,
            "message": "IP whitelist is not configured. All IPs are allowed."
        }
    
    # IP 화이트리스트 체크
    import ipaddress
    allowed_ips_set = set()
    
    for ip_str in settings.allowed_ips.split(','):
        ip_str = ip_str.strip()
        if not ip_str:
            continue
        try:
            if '/' in ip_str:
                allowed_ips_set.add(ipaddress.ip_network(ip_str, strict=False))
            else:
                ip = ipaddress.ip_address(ip_str)
                if isinstance(ip, ipaddress.IPv4Address):
                    allowed_ips_set.add(ipaddress.ip_network(f"{ip_str}/32", strict=False))
                else:
                    allowed_ips_set.add(ipaddress.ip_network(f"{ip_str}/128", strict=False))
        except ValueError:
            continue
    
    if not allowed_ips_set:
        return {
            "allowed": True,
            "ip": client_ip,
            "message": "IP whitelist is empty. All IPs are allowed."
        }
    
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        for allowed_network in allowed_ips_set:
            if client_ip_obj in allowed_network:
                return {
                    "allowed": True,
                    "ip": client_ip,
                    "message": "IP is allowed."
                }
        return {
            "allowed": False,
            "ip": client_ip,
            "message": "IP is not in the whitelist."
        }
    except ValueError:
        return {
            "allowed": False,
            "ip": client_ip,
            "message": "Invalid IP address format."
        }
