# Goodwave Report 배포 가이드

## 개요

Goodwave Report는 인스타그램 및 블로그 데이터 수집 및 분석 시스템입니다. 이 가이드를 따라 새로운 서버에 전체 시스템을 배포할 수 있습니다.

## 🚀 빠른 배포

```bash
# 1. 레포지토리 클론
git clone <repository-url>
cd goodwave/report

# 2. 환경 변수 설정
cp .env.example backend/.env
# backend/.env 파일을 편집하여 실제 값 입력

# 3. 배포 실행
./deploy.sh
```

## 📋 시스템 요구사항

### 필수 소프트웨어
- **Docker**: 24.0+ 버전
- **Docker Compose**: 2.0+ 버전
- **운영체제**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: 최소 4GB, 권장 8GB+
- **디스크**: 최소 20GB 여유 공간

### 포트 요구사항
- **3000**: 프론트엔드 (React)
- **8000**: 백엔드 API (FastAPI)
- **5432**: PostgreSQL (내부 통신용)
- **6379**: Redis (내부 통신용)

## 🔧 상세 배포 과정

### 1. 서버 준비

```bash
# Docker 설치 (Ubuntu 기준)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 재로그인 또는 newgrp docker 실행
newgrp docker
```

### 2. 프로젝트 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd goodwave/report

# 환경 변수 파일 생성
cp .env.example backend/.env
```

### 3. 환경 변수 설정

`backend/.env` 파일을 편집하여 다음 값들을 설정하세요:

#### 필수 설정

```bash
# 데이터베이스 (PostgreSQL 비밀번호 변경 권장)
DATABASE_URL=postgresql://postgres:your_secure_password@goodwave_postgres:5432/goodwave_db

# BrightData API (인스타그램 데이터 수집)
BRIGHTDATA_API_KEY=your_brightdata_api_key

# 네이버 검색 API (블로그 데이터 수집)
NAVER_CLIENT_ID=your_naver_client_id
NAVER_SECRET_KEY=your_naver_secret_key

# OpenAI API (이미지 분석)
OPENAI_API_KEY=your_openai_api_key

# AWS S3 (이미지 저장)
S3_ACCESS_KEY_ID=your_s3_access_key
S3_SECRET_ACCESS_KEY=your_s3_secret_key
S3_BUCKET=your_s3_bucket_name
S3_REGION=ap-northeast-2
```

#### API 키 발급 가이드

**BrightData API**
1. [BrightData](https://brightdata.com) 회원가입
2. Instagram 데이터셋 구독
3. API 키 발급

**네이버 검색 API**
1. [네이버 개발자 센터](https://developers.naver.com) 접속
2. 애플리케이션 등록
3. 검색 API 선택
4. Client ID/Secret 발급

**OpenAI API**
1. [OpenAI](https://platform.openai.com) 계정 생성
2. API 키 발급
3. GPT-4 Vision 접근 권한 확인

**AWS S3**
1. AWS 계정 생성
2. IAM 사용자 생성 (S3 권한)
3. Access Key/Secret Key 발급
4. S3 버킷 생성

### 4. 배포 실행

```bash
# 배포 스크립트 실행
./deploy.sh

# 또는 단계별 수동 배포
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d
```

### 5. 배포 확인

```bash
# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f

# 헬스체크
curl http://localhost:8000/health
curl http://localhost:3000
```

## 🌐 서비스 접속

배포 완료 후 다음 URL로 접속 가능합니다:

- **메인 애플리케이션**: http://localhost:3000
- **API 문서**: http://localhost:8000/docs
- **API 헬스체크**: http://localhost:8000/health

## ⚙️ 운영 관리

### 로그 모니터링

```bash
# 전체 로그 실시간 모니터링
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### 서비스 재시작

```bash
# 전체 서비스 재시작
docker-compose restart

# 특정 서비스 재시작
docker-compose restart backend
docker-compose restart frontend
```

### 데이터베이스 백업

```bash
# PostgreSQL 데이터베이스 백업
docker-compose exec postgres pg_dump -U postgres goodwave_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 백업 복원
docker-compose exec -T postgres psql -U postgres goodwave_db < backup_file.sql
```

### 크론 작업 관리

```bash
# 크론 작업 설정 확인
docker-compose exec backend crontab -l

# 크론 작업 재설정
docker-compose exec backend ./setup_cron.sh

# 수동 데이터 수집 실행
docker-compose exec backend python -c "
from app.services.scheduler_service import SchedulerService
scheduler = SchedulerService()
scheduler.collect_campaign_data()
"
```

## 🔒 보안 설정

### 프로덕션 환경 추가 설정

```bash
# 방화벽 설정 (Ubuntu)
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw allow 3000  # 프론트엔드
sudo ufw allow 8000  # 백엔드
sudo ufw enable

# HTTPS 설정 (Let's Encrypt 사용 권장)
# Nginx 리버스 프록시 설정 권장
```

### 환경 변수 보안

```bash
# .env 파일 권한 설정
chmod 600 backend/.env

# 민감한 정보가 Git에 커밋되지 않도록 확인
git status
# .env 파일이 tracked 되지 않는지 확인
```

## 🔄 업데이트

### 코드 업데이트

```bash
# 최신 코드 가져오기
git pull origin main

# 서비스 재빌드 및 재시작
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 데이터베이스 마이그레이션

```bash
# 새로운 테이블/컬럼 추가시
docker-compose exec backend python scripts/init_database.py
```

## 🚨 문제 해결

### 일반적인 문제

#### 1. 포트 충돌
```bash
# 포트 사용 확인
sudo netstat -tulpn | grep :3000
sudo netstat -tulpn | grep :8000

# 기존 프로세스 종료
sudo kill -9 <PID>
```

#### 2. Docker 이미지 빌드 실패
```bash
# Docker 캐시 정리
docker system prune -a -f

# 개별 컨테이너 재빌드
docker-compose build --no-cache backend
docker-compose build --no-cache frontend
```

#### 3. 데이터베이스 연결 실패
```bash
# PostgreSQL 로그 확인
docker-compose logs postgres

# 데이터베이스 재시작
docker-compose restart postgres

# 연결 테스트
docker-compose exec postgres psql -U postgres -c "SELECT version();"
```

#### 4. API 키 관련 오류
```bash
# 환경 변수 로드 확인
docker-compose exec backend python -c "import os; print(os.getenv('OPENAI_API_KEY')[:10] + '...' if os.getenv('OPENAI_API_KEY') else 'Not set')"

# .env 파일 다시 로드
docker-compose down
docker-compose up -d
```

### 로그 수집

문제 발생시 다음 정보를 수집하세요:

```bash
# 시스템 정보
docker --version
docker-compose --version
uname -a

# 컨테이너 상태
docker-compose ps

# 로그 수집
docker-compose logs --tail=100 > debug_logs.txt
```

## 📚 추가 자료

- **API 문서**: http://localhost:8000/docs
- **프로젝트 README**: [README.md](./README.md)
- **CLAUDE 가이드**: [CLAUDE.md](./CLAUDE.md)

## 🆘 지원

문제 발생시 다음 정보와 함께 문의하세요:

1. 운영체제 및 버전
2. Docker/Docker Compose 버전
3. 에러 로그 (docker-compose logs)
4. 환경 변수 설정 상태 (민감 정보 제외)
5. 브라우저 개발자 도구 콘솔 로그

---

> 💡 **팁**: 프로덕션 환경에서는 HTTPS 설정, 정기 백업, 모니터링 시스템 구축을 권장합니다.