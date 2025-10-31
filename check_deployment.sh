#!/bin/bash

# Goodwave Report 배포 상태 확인 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🔍 Goodwave Report 배포 상태 확인"
echo "=================================="

# 1. Docker 및 Docker Compose 확인
log_info "Docker 서비스 확인 중..."
if ! command -v docker &> /dev/null; then
    log_error "Docker가 설치되지 않았습니다."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose가 설치되지 않았습니다."
    exit 1
fi

log_success "✅ Docker 및 Docker Compose 확인 완료"

# 2. 컨테이너 상태 확인
log_info "컨테이너 상태 확인 중..."
echo ""
docker-compose ps

CONTAINERS=$(docker-compose ps --services)
ALL_HEALTHY=true

for service in $CONTAINERS; do
    STATUS=$(docker-compose ps -q $service | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
    if [ "$STATUS" = "running" ]; then
        log_success "✅ $service: 실행 중"
    else
        log_error "❌ $service: $STATUS"
        ALL_HEALTHY=false
    fi
done

# 3. 서비스 헬스체크
log_info "서비스 헬스체크 중..."

# 백엔드 헬스체크
if curl -s http://localhost:8000/health > /dev/null; then
    BACKEND_VERSION=$(curl -s http://localhost:8000/health | grep -o '"version":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
    log_success "✅ 백엔드 API: 정상 (버전: $BACKEND_VERSION)"
else
    log_error "❌ 백엔드 API: 응답 없음"
    ALL_HEALTHY=false
fi

# 프론트엔드 헬스체크
if curl -s http://localhost:3000 > /dev/null; then
    log_success "✅ 프론트엔드: 정상"
else
    log_error "❌ 프론트엔드: 응답 없음"
    ALL_HEALTHY=false
fi

# 데이터베이스 헬스체크
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    DB_SIZE=$(docker-compose exec -T postgres psql -U postgres -d goodwave_db -c "SELECT pg_size_pretty(pg_database_size('goodwave_db'));" -t | tr -d ' ' 2>/dev/null || echo "unknown")
    log_success "✅ PostgreSQL: 정상 (DB 크기: $DB_SIZE)"
else
    log_error "❌ PostgreSQL: 연결 실패"
    ALL_HEALTHY=false
fi

# Redis 헬스체크
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    log_success "✅ Redis: 정상"
else
    log_warning "⚠️ Redis: 연결 실패 (선택적 서비스)"
fi

# 4. 포트 확인
log_info "포트 사용 상태 확인 중..."

PORTS=(3000 8000 5432 6379)
for port in "${PORTS[@]}"; do
    if netstat -tulpn 2>/dev/null | grep ":$port " > /dev/null; then
        log_success "✅ 포트 $port: 사용 중"
    else
        log_warning "⚠️ 포트 $port: 사용되지 않음"
    fi
done

# 5. 환경 변수 확인
log_info "환경 변수 설정 확인 중..."

ENV_FILE="backend/.env"
if [ -f "$ENV_FILE" ]; then
    log_success "✅ .env 파일 존재"
    
    # 주요 환경 변수 확인
    REQUIRED_VARS=("DATABASE_URL" "BRIGHTDATA_API_KEY" "OPENAI_API_KEY" "S3_BUCKET")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" "$ENV_FILE" && ! grep -q "^$var=your_" "$ENV_FILE"; then
            log_success "✅ $var: 설정됨"
        else
            log_warning "⚠️ $var: 설정 필요"
        fi
    done
else
    log_error "❌ .env 파일이 없습니다."
    ALL_HEALTHY=false
fi

# 6. 디스크 사용량 확인
log_info "디스크 사용량 확인 중..."
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    log_success "✅ 디스크 사용량: ${DISK_USAGE}%"
else
    log_warning "⚠️ 디스크 사용량이 높습니다: ${DISK_USAGE}%"
fi

# 7. 메모리 사용량 확인
log_info "메모리 사용량 확인 중..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "$MEMORY_USAGE" -lt 80 ]; then
    log_success "✅ 메모리 사용량: ${MEMORY_USAGE}%"
else
    log_warning "⚠️ 메모리 사용량이 높습니다: ${MEMORY_USAGE}%"
fi

# 8. 최근 로그 확인
log_info "최근 에러 로그 확인 중..."
ERROR_COUNT=$(docker-compose logs --tail=100 2>/dev/null | grep -i error | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    log_success "✅ 최근 에러 로그 없음"
else
    log_warning "⚠️ 최근 에러 로그 ${ERROR_COUNT}개 발견"
fi

# 9. 데이터베이스 테이블 확인
log_info "데이터베이스 테이블 확인 중..."
TABLE_COUNT=$(docker-compose exec -T postgres psql -U postgres -d goodwave_db -c "\dt" 2>/dev/null | grep -c "public" || echo "0")
if [ "$TABLE_COUNT" -gt 0 ]; then
    log_success "✅ 데이터베이스 테이블: ${TABLE_COUNT}개"
else
    log_error "❌ 데이터베이스 테이블이 없습니다."
    ALL_HEALTHY=false
fi

# 최종 결과
echo ""
echo "=================================="
if [ "$ALL_HEALTHY" = true ]; then
    log_success "🎉 배포 상태: 정상"
    echo ""
    echo "📱 서비스 접속 정보:"
    echo "  - 메인 애플리케이션: http://localhost:3000"
    echo "  - API 문서: http://localhost:8000/docs"
    echo "  - API 헬스체크: http://localhost:8000/health"
else
    log_error "❌ 배포 상태: 문제 발견"
    echo ""
    echo "🔧 문제 해결 방법:"
    echo "  - 로그 확인: docker-compose logs -f"
    echo "  - 서비스 재시작: docker-compose restart"
    echo "  - 전체 재배포: ./deploy.sh"
fi

echo ""
echo "📊 추가 모니터링 명령어:"
echo "  - 실시간 로그: docker-compose logs -f"
echo "  - 컨테이너 상태: docker-compose ps"
echo "  - 리소스 사용량: docker stats"
echo "  - 디스크 정리: docker system prune -f"

echo "=================================="