#!/bin/bash

set -e  # 오류 발생시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 헤더 출력
echo -e "${BLUE}"
echo "🌊 ======================================"
echo "   Goodwave Report 시스템 설정 및 실행"
echo "======================================${NC}"
echo ""

# 1. Docker 설치 확인
log_info "Docker 설치 상태 확인..."
if ! command -v docker &> /dev/null; then
    log_warning "Docker가 설치되어 있지 않습니다. 설치를 진행합니다..."
    chmod +x install_docker.sh
    ./install_docker.sh
    
    log_warning "Docker 설치가 완료되었습니다. 권한 적용을 위해 다음을 실행하세요:"
    echo "newgrp docker"
    echo "그 후 다시 이 스크립트를 실행하세요: ./setup_and_run.sh"
    exit 0
else
    log_success "Docker가 이미 설치되어 있습니다."
fi

# Docker Compose 설치 확인
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose가 설치되어 있지 않습니다. install_docker.sh를 먼저 실행하세요."
    exit 1
else
    log_success "Docker Compose가 설치되어 있습니다."
fi

# 2. 환경 변수 파일 확인
log_info "환경 변수 파일 확인..."
if [ ! -f ".env" ]; then
    log_error ".env 파일이 없습니다. 파일을 생성하고 필요한 환경 변수를 설정하세요."
    exit 1
else
    log_success ".env 파일이 존재합니다."
fi

# 3. 필요한 디렉토리 생성
log_info "필요한 디렉토리 생성..."
mkdir -p backend/static
mkdir -p backend/logs
log_success "디렉토리 생성 완료"

# 4. 기존 컨테이너 정리
log_info "기존 컨테이너 정리..."
docker-compose down --remove-orphans || true
docker system prune -f || true
log_success "컨테이너 정리 완료"

# 5. Docker 이미지 빌드 및 컨테이너 시작
log_info "Docker 이미지 빌드 및 컨테이너 시작..."
log_info "이 과정은 몇 분이 소요될 수 있습니다..."

# 단계별로 서비스 시작
log_info "1단계: 데이터베이스 서비스 시작..."
docker-compose up -d postgres redis

log_info "데이터베이스 서비스 준비 대기..."
sleep 10

# PostgreSQL 준비 상태 확인
log_info "PostgreSQL 연결 확인..."
max_attempts=30
attempt=1
while ! docker-compose exec -T postgres pg_isready -U postgres &> /dev/null; do
    if [ $attempt -eq $max_attempts ]; then
        log_error "PostgreSQL 연결에 실패했습니다."
        docker-compose logs postgres
        exit 1
    fi
    log_info "PostgreSQL 연결 대기 중... (시도 $attempt/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done
log_success "PostgreSQL 연결 성공!"

log_info "2단계: 백엔드 서비스 빌드 및 시작..."
docker-compose up -d --build backend

log_info "백엔드 서비스 준비 대기..."
sleep 15

# 백엔드 헬스체크
log_info "백엔드 서비스 상태 확인..."
max_attempts=30
attempt=1
while ! curl -f http://localhost:8000/health &> /dev/null; do
    if [ $attempt -eq $max_attempts ]; then
        log_error "백엔드 서비스 시작에 실패했습니다."
        docker-compose logs backend
        exit 1
    fi
    log_info "백엔드 서비스 대기 중... (시도 $attempt/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done
log_success "백엔드 서비스 시작 성공!"

log_info "3단계: 프론트엔드 서비스 빌드 및 시작..."
docker-compose up -d --build frontend

log_info "프론트엔드 서비스 준비 대기..."
sleep 15

# 프론트엔드 상태 확인
log_info "프론트엔드 서비스 상태 확인..."
max_attempts=20
attempt=1
while ! curl -f http://localhost:3000 &> /dev/null; do
    if [ $attempt -eq $max_attempts ]; then
        log_error "프론트엔드 서비스 시작에 실패했습니다."
        docker-compose logs frontend
        exit 1
    fi
    log_info "프론트엔드 서비스 대기 중... (시도 $attempt/$max_attempts)"
    sleep 3
    attempt=$((attempt + 1))
done
log_success "프론트엔드 서비스 시작 성공!"

# 6. 서비스 상태 확인
log_info "전체 서비스 상태 확인..."
docker-compose ps

# 7. 데이터베이스 테이블 생성
log_info "데이터베이스 테이블 생성..."
docker-compose exec -T backend python -c "
from app.db.models import Base
from app.db.database import engine
try:
    Base.metadata.create_all(bind=engine)
    print('✅ 데이터베이스 테이블 생성 완료!')
except Exception as e:
    print(f'❌ 테이블 생성 실패: {e}')
    exit(1)
"

# 8. 간단한 API 테스트
log_info "API 엔드포인트 테스트..."
if curl -f http://localhost:8000/health &> /dev/null; then
    log_success "백엔드 API 정상 작동"
else
    log_warning "백엔드 API 응답 없음"
fi

if curl -f http://localhost:8000/api/campaigns/ &> /dev/null; then
    log_success "캠페인 API 정상 작동"
else
    log_warning "캠페인 API 응답 없음 (정상 - 빈 데이터)"
fi

# 9. Cron 작업 설정 (선택사항)
log_info "자동 데이터 수집 스케줄 설정..."
if [ -f "backend/setup_cron.sh" ]; then
    cd backend
    chmod +x setup_cron.sh
    ./setup_cron.sh
    cd ..
    log_success "Cron 작업 설정 완료"
else
    log_warning "Cron 설정 파일을 찾을 수 없습니다."
fi

# 성공 메시지 출력
echo ""
echo -e "${GREEN}🎉 ======================================"
echo "   Goodwave Report 시스템 시작 완료!"
echo "======================================${NC}"
echo ""
echo -e "${BLUE}📋 접속 정보:${NC}"
echo "🌐 프론트엔드:     http://localhost:3000"
echo "🔧 관리자 페이지:   http://localhost:3000/admin"
echo "🔌 백엔드 API:     http://localhost:8000"
echo "📊 API 문서:       http://localhost:8000/docs"
echo "🗄️  데이터베이스:   localhost:5432 (postgres/password)"
echo ""
echo -e "${BLUE}📖 보고서 페이지 (예시):${NC}"
echo "📱 인스타그램 게시물: http://localhost:3000/report/instagram-post?campaign=테스트캠페인"
echo "🎥 인스타그램 릴스:   http://localhost:3000/report/instagram-reel?campaign=테스트캠페인"
echo "📝 블로그:          http://localhost:3000/report/blog?campaign=테스트캠페인"
echo ""
echo -e "${YELLOW}💡 유용한 명령어:${NC}"
echo "📋 컨테이너 상태 확인: docker-compose ps"
echo "📜 로그 확인:        docker-compose logs [서비스명]"
echo "🛑 서비스 종료:      docker-compose down"
echo "🔄 서비스 재시작:    docker-compose restart [서비스명]"
echo ""
echo -e "${GREEN}✨ 시스템이 성공적으로 시작되었습니다!${NC}"