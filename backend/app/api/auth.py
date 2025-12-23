"""
인증 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
import bcrypt

from app.db.database import get_db
from app.db import models
from app.core.config import settings

router = APIRouter()

# 비밀번호 해싱
# passlib과 최신 bcrypt 버전의 호환성 문제로 인해, bcrypt를 직접 사용
# bcrypt는 72바이트 제한이 있으므로, 명시적으로 처리
# passlib은 완전히 우회하고 bcrypt를 직접 사용
pwd_context = None

# Pydantic 모델
class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="사용자명")
    password: str = Field(..., min_length=6, max_length=72, description="비밀번호 (최대 72자)")

# OAuth2 스키마
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증 (bcrypt 직접 사용)"""
    # bcrypt 직접 사용 (passlib 호환성 문제로 인해 완전히 우회)
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """비밀번호 해싱 (bcrypt는 72바이트 제한이 있으므로 자동으로 처리)"""
    # bcrypt는 72바이트를 초과하면 에러가 발생하므로, 명시적으로 제한
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # 72바이트를 초과하면 자동으로 잘라냄
        # UTF-8 인코딩을 고려하여 안전하게 잘라냄
        truncated_bytes = password_bytes[:72]
        # 마지막 바이트가 잘린 멀티바이트 문자일 수 있으므로, 안전하게 디코딩
        try:
            password = truncated_bytes.decode('utf-8')
            password_bytes = password.encode('utf-8')
        except UnicodeDecodeError:
            # 잘린 바이트로 인해 디코딩 실패 시, 마지막 바이트 제거 후 재시도
            password = truncated_bytes[:-1].decode('utf-8', errors='ignore')
            password_bytes = password.encode('utf-8')
    
    # bcrypt 직접 사용 (passlib 호환성 문제로 인해 완전히 우회)
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def authenticate_user(db: Session, username: str, password: str):
    """사용자 인증"""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return False
    if not user.is_active:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """현재 로그인한 사용자 조회"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    return user

@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """로그인"""
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username
    }

@router.get("/me")
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    """현재 사용자 정보 조회"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "is_active": current_user.is_active
    }

@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """모든 사용자 목록 조회 (관리자만 가능)"""
    users = db.query(models.User).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        }
        for user in users
    ]

@router.post("/create-initial-admin")
async def create_initial_admin(
    request: Optional[UserCreateRequest] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """초기 관리자 계정 생성 (인증 불필요, 사용자가 없을 때만 가능)
    
    쿼리 파라미터 또는 JSON body로 전달 가능:
    - 쿼리 파라미터: ?username=goodwave&password=goodwave123
    - JSON body: {"username": "goodwave", "password": "goodwave123"}
    """
    # 요청 데이터 추출 (쿼리 파라미터 또는 JSON body)
    if request:
        user_name = request.username
        user_password = request.password
    elif username and password:
        user_name = username
        user_password = password
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required (either as query parameters or in JSON body)"
        )
    
    # 입력 검증
    if not user_name or len(user_name) < 3 or len(user_name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3 and 100 characters"
        )
    
    if not user_password or len(user_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    # 기존 사용자가 있는지 확인
    existing_users = db.query(models.User).count()
    if existing_users > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Initial admin can only be created when no users exist"
        )
    
    # 기존 사용자 확인 (중복 체크)
    existing_user = db.query(models.User).filter(models.User.username == user_name).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # 비밀번호 길이 검증 (UTF-8 바이트 기준)
    password_bytes = user_password.encode('utf-8')
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot exceed 72 bytes when encoded in UTF-8"
        )
    
    # 새 사용자 생성
    hashed_password = get_password_hash(user_password)
    new_user = models.User(
        username=user_name,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "is_active": new_user.is_active,
        "message": "Initial admin user created successfully"
    }

@router.post("/create-user")
async def create_user(
    request: Optional[UserCreateRequest] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """새 사용자 생성 (관리자만 가능)
    
    쿼리 파라미터 또는 JSON body로 전달 가능:
    - 쿼리 파라미터: ?username=user&password=password123
    - JSON body: {"username": "user", "password": "password123"}
    """
    # 요청 데이터 추출 (쿼리 파라미터 또는 JSON body)
    if request:
        user_name = request.username
        user_password = request.password
    elif username and password:
        user_name = username
        user_password = password
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required (either as query parameters or in JSON body)"
        )
    
    # 입력 검증
    if not user_name or len(user_name) < 3 or len(user_name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3 and 100 characters"
        )
    
    if not user_password or len(user_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    # 기존 사용자 확인
    existing_user = db.query(models.User).filter(models.User.username == user_name).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # 비밀번호 길이 검증 (UTF-8 바이트 기준)
    password_bytes = user_password.encode('utf-8')
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot exceed 72 bytes when encoded in UTF-8"
        )
    
    # 새 사용자 생성
    hashed_password = get_password_hash(user_password)
    new_user = models.User(
        username=user_name,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "is_active": new_user.is_active,
        "message": "User created successfully"
    }

@router.put("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """현재 사용자의 비밀번호 변경"""
    # 기존 비밀번호 확인
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    
    # 새 비밀번호로 업데이트
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {
        "message": "Password changed successfully"
    }

@router.put("/users/{user_id}/password")
async def change_user_password(
    user_id: int,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """다른 사용자의 비밀번호 변경 (관리자만 가능)"""
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 비밀번호 변경
    target_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {
        "message": f"Password changed successfully for user {target_user.username}"
    }

@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """사용자 활성화/비활성화 (관리자만 가능)"""
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 자기 자신은 비활성화할 수 없음
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    target_user.is_active = not target_user.is_active
    db.commit()
    
    return {
        "id": target_user.id,
        "username": target_user.username,
        "is_active": target_user.is_active,
        "message": f"User {'activated' if target_user.is_active else 'deactivated'} successfully"
    }

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """사용자 삭제 (관리자만 가능)"""
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 자기 자신은 삭제할 수 없음
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    db.delete(target_user)
    db.commit()
    
    return {
        "message": f"User {target_user.username} deleted successfully"
    }
