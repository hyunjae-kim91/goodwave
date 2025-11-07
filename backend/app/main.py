from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import engine, SessionLocal
from app.db import models
from app.api import campaigns, reports, admin, influencer_ingest, influencer_files, influencer_classification, influencer_prompt, progress_stream, unified_reports
from app.services.collection_worker import start_collection_worker, stop_collection_worker
from app.services.classification_worker import start_classification_worker, stop_classification_worker
from app.services.campaign_schedule_runner import start_campaign_schedule_runner, stop_campaign_schedule_runner
from app.services.grade_service import instagram_grade_service

models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    session = SessionLocal()
    try:
        instagram_grade_service.ensure_default_thresholds(session)
    finally:
        session.close()
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

app = FastAPI(
    title="Goodwave Report API",
    description="Instagram and Blog Data Collection & Reporting System",
    version="1.0.0",
    lifespan=lifespan
)

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
