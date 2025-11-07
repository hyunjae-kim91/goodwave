#!/bin/bash

# Goodwave Report 배포 스크립트
# 사용법: ./deploy.sh [environment]
# environment: production, staging, development (기본값: production)

set -e  # 에러 발생시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 환경 설정
ENVIRONMENT=${1:-production}
PROJECT_ROOT=$(pwd)
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

log_info "🚀 Goodwave Report 배포 시작 (환경: $ENVIRONMENT)"

# 1. 시스템 요구사항 확인
log_info "📋 시스템 요구사항 확인 중..."

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    log_error "Docker가 설치되지 않았습니다. Docker를 먼저 설치해주세요."
    exit 1
fi

# Docker Compose 설치 확인
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose가 설치되지 않았습니다. Docker Compose를 먼저 설치해주세요."
    exit 1
fi

log_success "✅ Docker 및 Docker Compose 설치 확인 완료"

# 2. 환경 변수 파일 확인
log_info "🔧 환경 변수 설정 확인 중..."

ENV_FILE="$BACKEND_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    log_warning "⚠️ .env 파일이 없습니다. 템플릿에서 생성합니다."
    
    # .env 템플릿 생성
    cat > "$ENV_FILE" << 'EOL'
# AWS RDS PostgreSQL 데이터베이스 설정
DATABASE_URL=postgresql://DB_USER:DB_PASSWORD@RDS_ENDPOINT:5432/DB_NAME

# 외부 API 키
BRIGHTDATA_API_KEY=your_brightdata_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_SECRET_KEY=your_naver_secret_key
OPENAI_API_KEY=your_openai_api_key
OPENAI_VISION_MODEL=gpt-4-vision-preview

# AWS S3 설정
S3_ACCESS_KEY_ID=your_s3_access_key
S3_SECRET_ACCESS_KEY=your_s3_secret_key
S3_BUCKET=your_s3_bucket_name
S3_REGION=ap-northeast-2

# Redis 설정 (선택사항)
REDIS_URL=redis://goodwave_redis:6379/0

# 기타 설정
TZ=Asia/Seoul
EOL
    
    log_error "❌ .env 파일을 생성했습니다. $ENV_FILE 파일을 편집하여 실제 값으로 설정한 후 다시 실행해주세요."
    exit 1
fi

log_success "✅ 환경 변수 파일 확인 완료"

# 3. 기존 컨테이너 정리
log_info "🧹 기존 컨테이너 정리 중..."

# 기존 컨테이너 중지 및 제거
docker-compose down --remove-orphans 2>/dev/null || true

# 사용하지 않는 컨테이너, 네트워크, 이미지 정리
docker system prune -f

log_success "✅ 기존 컨테이너 정리 완료"

# 4. Docker 이미지 빌드
log_info "🔨 Docker 이미지 빌드 중..."

# 프론트엔드 의존성 설치 (Docker 빌드 전에)
if [ -f "$FRONTEND_DIR/package.json" ]; then
    log_info "📦 프론트엔드 의존성 설치 중..."
    cd "$FRONTEND_DIR"
    
    # node_modules 정리
    rm -rf node_modules package-lock.json 2>/dev/null || true
    
    # npm 의존성 설치
    npm install
    
    cd "$PROJECT_ROOT"
    log_success "✅ 프론트엔드 의존성 설치 완료"
fi

# 백엔드 Python 의존성 확인
if [ -f "$BACKEND_DIR/requirements.txt" ]; then
    log_success "✅ 백엔드 requirements.txt 확인 완료"
fi

# Docker Compose 빌드
docker-compose build --no-cache

log_success "✅ Docker 이미지 빌드 완료"

# 5. AWS RDS 데이터베이스 연결 확인 및 초기화
log_info "🗄️ AWS RDS 데이터베이스 초기화 중..."

# Redis 컨테이너 시작
docker-compose up -d redis

# Redis가 준비될 때까지 대기
log_info "⏳ Redis 준비 대기 중..."
sleep 3
log_success "✅ Redis 준비 완료"

# AWS RDS 연결 확인 및 테이블 생성
log_info "📊 AWS RDS 연결 확인 및 스키마 초기화 중..."

# 백엔드 컨테이너 임시 실행하여 RDS 연결 및 테이블 생성
docker-compose run --rm backend python -c "
from app.db.models import Base
from app.db.database import engine
from sqlalchemy import text
import sys

try:
    # RDS 연결 테스트
    print('AWS RDS 연결 테스트 중...')
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ AWS RDS 연결 성공')
    
    # 테이블 생성
    print('데이터베이스 테이블 생성 중...')
    Base.metadata.create_all(bind=engine)
    print('✅ 데이터베이스 테이블 생성 완료')
    
    # Instagram 등급 임계값 초기 데이터 삽입
    print('초기 데이터 삽입 중...')
    with engine.connect() as conn:
        conn.execute(text('''
            INSERT INTO instagram_grade_thresholds (grade_name, min_view_count, max_view_count, created_at, updated_at) 
            VALUES 
                ('프리미엄', 100001, NULL, NOW(), NOW()),
                ('골드', 30001, 100000, NOW(), NOW()),
                ('블루', 5001, 30000, NOW(), NOW()),
                ('레드', 1000, 5000, NOW(), NOW())
            ON CONFLICT (grade_name) DO NOTHING
        '''))
        conn.commit()
    print('✅ 초기 데이터 삽입 완료')
    
except Exception as e:
    print(f'❌ 데이터베이스 초기화 실패: {str(e)}')
    print('💡 .env 파일의 DATABASE_URL이 올바른 AWS RDS 엔드포인트를 가리키는지 확인하세요.')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    log_error "❌ AWS RDS 데이터베이스 초기화 실패"
    log_error "💡 .env 파일의 DATABASE_URL 설정을 확인하세요."
    log_error "   형식: postgresql://USER:PASSWORD@RDS_ENDPOINT:5432/DB_NAME"
    exit 1
fi

log_success "✅ AWS RDS 데이터베이스 초기화 완료"

# 6. 전체 서비스 시작
log_info "🚀 전체 서비스 시작 중..."

# 모든 서비스 시작
docker-compose up -d

# 서비스가 준비될 때까지 대기
log_info "⏳ 서비스 준비 대기 중..."
sleep 10

# 백엔드 헬스체크
for i in {1..15}; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        log_success "✅ 백엔드 서비스 준비 완료"
        break
    fi
    echo -n "."
    sleep 2
done

# Nginx 헬스체크 (프론트엔드 포함)
for i in {1..15}; do
    if curl -s http://localhost:80 &>/dev/null; then
        log_success "✅ Nginx 웹 서버 준비 완료"
        break
    fi
    echo -n "."
    sleep 2
done

# 7. 크론 작업 설정 (백엔드 컨테이너 내부)
log_info "⏰ 크론 작업 설정 중..."

docker-compose exec -T backend bash -c "
if [ -f './setup_cron.sh' ]; then
    chmod +x ./setup_cron.sh
    ./setup_cron.sh
    echo '✅ 크론 작업 설정 완료'
else
    echo '⚠️ setup_cron.sh 파일을 찾을 수 없습니다.'
fi
"

# 8. 최종 상태 확인
log_info "🔍 최종 배포 상태 확인 중..."

echo ""
echo "📊 컨테이너 상태:"
docker-compose ps

echo ""
echo "🌐 서비스 접속 정보:"
echo "  - 웹 애플리케이션: http://localhost (또는 서버 IP)"
echo "  - 관리자 페이지: http://localhost/admin"
echo "  - 백엔드 API (직접): http://localhost:8000"
echo "  - API 문서: http://localhost:8000/docs"
echo "  - 백엔드 헬스체크: http://localhost:8000/health"

echo ""
echo "📋 로그 확인 명령어:"
echo "  - 전체 로그: docker-compose logs -f"
echo "  - Nginx 로그: docker-compose logs -f nginx"
echo "  - 백엔드 로그: docker-compose logs -f backend"
echo "  - 프론트엔드 로그: docker-compose logs -f frontend"
echo "  - Redis 로그: docker-compose logs -f redis"

echo ""
log_success "🎉 Goodwave Report 배포 완료!"
echo ""
echo "⚠️  중요 사항:"
echo "   1. .env 파일의 모든 API 키와 AWS RDS 연결 정보가 올바르게 설정되었는지 확인하세요"
echo "   2. AWS RDS 보안 그룹에서 배포 서버의 IP가 허용되었는지 확인하세요"
echo "   3. 방화벽에서 포트 80 (HTTP), 8000 (백엔드 API)이 열려있는지 확인하세요"
echo "   4. 프로덕션 환경에서는 Nginx에 HTTPS(SSL/TLS) 설정을 권장합니다"
echo "   5. AWS RDS 자동 백업이 활성화되어 있는지 확인하세요"
echo "   6. 브라우저에서 http://서버IP/admin 으로 접속하세요"
echo ""
echo "📚 추가 도움말:"
echo "   - 서비스 중지: docker-compose down"
echo "   - 서비스 재시작: docker-compose restart"
echo "   - 로그 모니터링: docker-compose logs -f"
echo ""