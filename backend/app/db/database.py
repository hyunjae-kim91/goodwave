from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 연결 풀 설정 증가 (기본값: pool_size=5, max_overflow=10)
# 워커와 API 요청이 동시에 많이 발생할 수 있으므로 충분한 크기로 설정
engine = create_engine(
    settings.database_url,
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