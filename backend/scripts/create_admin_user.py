"""
초기 관리자 사용자 생성 스크립트
"""
import sys
import os

# backend 디렉토리를 Python 경로에 추가
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

# 환경 변수가 없어도 작동하도록 최소한의 환경 변수 설정
# 필수 환경 변수가 없으면 더미 값으로 설정 (DB 연결만 필요)
required_env_vars = [
    'BRIGHTDATA_API_KEY',
    'S3_ACCESS_KEY_ID',
    'S3_SECRET_ACCESS_KEY',
    'S3_BUCKET',
    'NAVER_CLIENT_ID',
    'NAVER_SECRET_KEY',
    'OPENAI_API_KEY'
]

for var in required_env_vars:
    if var not in os.environ:
        os.environ[var] = 'dummy_value_for_script'

# SSH 터널 관련 모듈을 임시로 모킹하여 import 에러 방지
class MockSSHTunnel:
    @staticmethod
    def get_tunnel_status():
        return {"enabled": False, "active": False}
    
    @staticmethod
    def start_ssh_tunnel():
        return None

# ssh_tunnel 모듈을 모킹
import types
mock_module = types.ModuleType('app.db.ssh_tunnel')
mock_module.get_tunnel_status = MockSSHTunnel.get_tunnel_status
mock_module.start_ssh_tunnel = MockSSHTunnel.start_ssh_tunnel
sys.modules['app.db.ssh_tunnel'] = mock_module

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from app.db import models
from app.core.config import settings

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)

# DB 연결 직접 생성 (SSH 터널 없이)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_admin_user(username: str = "admin", password: str = "admin123"):
    """초기 관리자 사용자 생성"""
    db = SessionLocal()
    try:
        # 기존 사용자 확인
        existing_user = db.query(models.User).filter(models.User.username == username).first()
        if existing_user:
            print(f"⚠️ 사용자 '{username}'가 이미 존재합니다.")
            return
        
        # 새 사용자 생성
        hashed_password = get_password_hash(password)
        new_user = models.User(
            username=username,
            hashed_password=hashed_password,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        print(f"✅ 관리자 사용자 '{username}'가 생성되었습니다.")
        print(f"   아이디: {username}")
        print(f"   비밀번호: {password}")
        print(f"   ⚠️ 보안을 위해 첫 로그인 후 비밀번호를 변경하세요!")
    except Exception as e:
        db.rollback()
        print(f"❌ 사용자 생성 실패: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='초기 관리자 사용자 생성')
    parser.add_argument('--username', default='admin', help='사용자명 (기본값: admin)')
    parser.add_argument('--password', default='admin123', help='비밀번호 (기본값: admin123)')
    
    args = parser.parse_args()
    
    create_admin_user(args.username, args.password)
