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

# 1. 시스템 업데이트 및 기본 패키지 설치
log_info "시스템 업데이트 및 기본 패키지 설치..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release apt-transport-https software-properties-common

# 2. Docker 설치
log_info "Docker 설치 확인 및 설치..."
if ! command -v docker &> /dev/null; then
    log_info "Docker 설치 중..."
    
    # Docker GPG 키 추가
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Docker 저장소 추가
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Docker 설치
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # 사용자를 docker 그룹에 추가
    sudo usermod -aG docker $USER
    
    # Docker 서비스 시작
    sudo systemctl start docker
    sudo systemctl enable docker
    
    log_success "Docker 설치 완료"
else
    log_success "Docker가 이미 설치되어 있습니다."
fi

# 3. Docker Compose 설치 (별도)
log_info "Docker Compose 설치..."
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log_success "Docker Compose 설치 완료"
else
    log_success "Docker Compose가 이미 설치되어 있습니다."
fi

# 4. Node.js 설치
log_info "Node.js 설치..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    log_success "Node.js 설치 완료"
else
    log_success "Node.js가 이미 설치되어 있습니다."
fi

# 5. Python 3 설치 확인
log_info "Python 설치 확인..."
sudo apt-get install -y python3 python3-pip python3-venv

# 6. 환경 변수 파일 확인
log_info "환경 변수 파일 확인..."
if [ ! -f ".env" ]; then
    log_error ".env 파일이 없습니다. 파일을 생성하고 필요한 환경 변수를 설정하세요."
    exit 1
else
    log_success ".env 파일이 존재합니다."
fi

# 7. 필요한 디렉토리 생성
log_info "필요한 디렉토리 생성..."
mkdir -p backend/static
mkdir -p backend/logs
log_success "디렉토리 생성 완료"

# 8. Docker 권한 확인
log_info "Docker 권한 확인..."
if ! docker ps &> /dev/null; then
    log_warning "Docker 권한이 없습니다. 다음 중 하나를 실행하세요:"
    echo "  1) newgrp docker"
    echo "  2) 로그아웃 후 다시 로그인"
    echo "그 후 다시 이 스크립트를 실행하세요."
    exit 0
fi

# 9. 기존 컨테이너 정리
log_info "기존 컨테이너 정리..."
docker-compose down --remove-orphans || true
docker system prune -f || true
log_success "컨테이너 정리 완료"

# 10. Docker 이미지 빌드 및 컨테이너 시작
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

# 11. 데이터베이스 테이블 생성
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

# 12. 서비스 상태 확인
log_info "전체 서비스 상태 확인..."
docker-compose ps

# 13. API 테스트
log_info "API 엔드포인트 테스트..."
if curl -f http://localhost:8000/health &> /dev/null; then
    log_success "백엔드 API 정상 작동"
else
    log_warning "백엔드 API 응답 없음"
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
echo ""
echo -e "${BLUE}설치된 버전:${NC}"
docker --version
docker-compose --version
node --version
python3 --version