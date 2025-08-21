#!/bin/bash

# Goodwave Blog API 배포 스크립트

echo "=== Goodwave Blog API 배포 시작 ==="

# Docker와 Docker Compose가 설치되어 있는지 확인
if ! command -v docker &> /dev/null; then
    echo "Docker가 설치되어 있지 않습니다. Docker를 먼저 설치해주세요."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose가 설치되어 있지 않습니다. Docker Compose를 먼저 설치해주세요."
    exit 1
fi

# 기존 컨테이너 중지 및 제거
echo "기존 컨테이너 중지 중..."
docker-compose down

# Docker 이미지 빌드
echo "Docker 이미지 빌드 중..."
docker-compose build

# 컨테이너 시작
echo "컨테이너 시작 중..."
docker-compose up -d

# 컨테이너 상태 확인
echo "컨테이너 상태 확인 중..."
sleep 10
docker-compose ps

# 헬스 체크
echo "API 헬스 체크 중..."
sleep 20
curl -f http://localhost:8000/health || echo "헬스 체크 실패"

echo "=== 배포 완료 ==="
echo "API가 http://localhost:8000 에서 실행 중입니다."
echo "API 문서는 http://localhost:8000/docs 에서 확인할 수 있습니다." 