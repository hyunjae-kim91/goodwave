#!/bin/bash

# Backend 로컬 실행 스크립트
echo "Starting Goodwave Backend locally..."

# backend 디렉토리로 이동
cd backend

# Python 가상환경 활성화 (있다면)
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "Activating virtual environment..."
    source ../venv/bin/activate
fi

# 의존성 설치
echo "Installing dependencies..."
pip install -r requirements.txt

# 환경변수 파일 확인
if [ -f ".env" ]; then
    echo "Loading environment variables from .env"
else
    echo "Warning: .env file not found. Please create one with required variables."
fi

# FastAPI 서버 시작
echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload