#!/bin/bash

echo "Starting Goodwave Report Development Environment with Docker..."

# Docker 정리 실행
echo "Cleaning up Docker resources..."
./cleanup-docker.sh

# 환경 변수 파일 확인
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create .env file with required environment variables."
    exit 1
fi

echo "Loading environment variables from .env file..."
set -a
source .env
set +a

# 모든 서비스를 Docker로 시작
echo "Building and starting all services with Docker..."
docker-compose up --build -d

# 서비스 상태 확인
echo ""
echo "Checking service health..."
sleep 10

# 컨테이너 상태 확인
echo "Container status:"
docker-compose ps

# 로그 확인 (에러가 있는지 체크)
echo ""
echo "Checking for any startup errors..."
docker-compose logs --tail=20

echo ""
echo "🚀 Development environment is starting up!"
echo ""
echo "📊 Backend API: http://localhost:8000"
echo "🌐 Frontend: http://localhost:3000"
echo "📝 Admin Panel: http://localhost:3000/admin"
echo ""
echo "📄 View logs with:"
echo "  - All services: docker-compose logs -f"
echo "  - Backend only: docker-compose logs -f backend"
echo "  - Frontend only: docker-compose logs -f frontend"
echo ""
echo "🛑 To stop all services: docker-compose down"
echo ""

# 실시간 로그 출력 (선택사항)
echo "Following logs... (Press Ctrl+C to stop watching logs)"
docker-compose logs -f
