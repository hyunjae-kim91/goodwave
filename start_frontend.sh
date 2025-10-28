#!/bin/bash

# Frontend 로컬 실행 스크립트
echo "Starting Goodwave Frontend locally..."

# frontend 디렉토리로 이동
cd frontend

# Node.js 버전 확인
echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# 의존성 설치
echo "Installing dependencies..."
npm install

# 환경변수 파일 확인
if [ -f ".env" ]; then
    echo "Loading environment variables from .env"
else
    echo "Note: No .env file found. Using default configuration."
fi

# React 개발 서버 시작
echo "Starting React development server..."
npm start