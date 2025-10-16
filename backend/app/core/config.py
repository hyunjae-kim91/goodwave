from pydantic_settings import BaseSettings
from typing import Optional

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
    
    # Storage
    storage_provider: str = "s3"  # local or s3
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()
