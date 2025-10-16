# Goodwave Report - 인스타그램/블로그 데이터 수집 및 보고서 시스템

## 개요
인스타그램(게시물/릴스)과 블로그 데이터를 수집하고 분석하여 캠페인 보고서를 생성하는 웹 애플리케이션입니다.

## 기술 스택
- **백엔드**: FastAPI, PostgreSQL, SQLAlchemy
- **프론트엔드**: React (TypeScript), Styled Components, Chart.js
- **데이터베이스**: PostgreSQL
- **이미지 저장소**: AWS S3
- **AI 분석**: OpenAI Vision API
- **스케줄링**: Python Cron

## 주요 기능

### 1. 데이터 수집
- 인스타그램 게시물 데이터 수집 (BrightData API 활용)
- 인스타그램 릴스 데이터 수집
- 블로그 게시물 데이터 및 네이버 검색 순위 수집

### 2. 이미지 분석
- OpenAI Vision API를 통한 썸네일 이미지 분석
- 구독 동기 및 카테고리 자동 분류
- S3를 통한 이미지 저장 및 관리

### 3. 캠페인 관리
- 캠페인 생성 및 관리
- 다중 URL 지원
- 자동 스케줄링 설정

### 4. 보고서 생성
- 인스타그램 게시물 보고서 (차트 포함)
- 인스타그램 릴스 보고서 (차트 포함)
- 블로그 순위 보고서 (날짜별 순위 테이블)

## 설치 및 실행

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd goodwave/report

# 환경 변수 설정 (.env 파일 수정)
cp .env.example .env
# .env 파일에서 API 키들 설정
```

### 2. 데이터베이스 설정
```bash
# PostgreSQL 및 Redis 실행
docker-compose up -d

# 또는 직접 PostgreSQL 설치 후
createdb goodwave_report
```

### 3. 백엔드 실행
```bash
cd backend
pip install -r requirements.txt

# 데이터베이스 테이블 생성
python -c "from app.db.models import Base; from app.db.database import engine; Base.metadata.create_all(bind=engine)"

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 프론트엔드 실행
```bash
cd frontend
npm install
npm start
```

### 5. Cron 작업 설정
```bash
cd backend
chmod +x setup_cron.sh
./setup_cron.sh
```

## API 엔드포인트

### 관리자 API
- `GET /api/admin/dashboard` - 관리자 대시보드 데이터
- `GET /api/admin/collection-schedules` - 수집 스케줄 조회
- `PUT /api/admin/collection-schedules/{id}/toggle` - 스케줄 활성화/비활성화

### 캠페인 API
- `POST /api/campaigns/` - 캠페인 생성
- `GET /api/campaigns/` - 캠페인 목록
- `GET /api/campaigns/{id}` - 캠페인 상세
- `DELETE /api/campaigns/{id}` - 캠페인 삭제

### 데이터 수집 API
- `POST /api/data-collection/instagram/posts` - 인스타그램 게시물 수집
- `POST /api/data-collection/instagram/reels` - 인스타그램 릴스 수집
- `POST /api/data-collection/blogs` - 블로그 게시물 수집

### 보고서 API
- `GET /api/reports/instagram/posts/{campaign_name}` - 인스타그램 게시물 보고서
- `GET /api/reports/instagram/reels/{campaign_name}` - 인스타그램 릴스 보고서
- `GET /api/reports/blogs/{campaign_name}` - 블로그 보고서

## URL 구조

### 관리자 페이지
- `/admin/dashboard` - 관리자 대시보드
- `/admin/campaigns` - 캠페인 관리
- `/admin/data-collection` - 데이터 수집

### 보고서 페이지 (고객용)
- `/report/instagram-post?campaign={campaign_name}` - 인스타그램 게시물 보고서
- `/report/instagram-reel?campaign={campaign_name}` - 인스타그램 릴스 보고서
- `/report/blog?campaign={campaign_name}` - 블로그 보고서

## 데이터베이스 스키마

### 주요 테이블
- `campaigns` - 캠페인 정보
- `campaign_urls` - 캠페인 URL
- `collection_schedules` - 수집 스케줄
- `instagram_posts` - 인스타그램 게시물 데이터
- `instagram_reels` - 인스타그램 릴스 데이터
- `blog_posts` - 블로그 게시물 데이터
- `blog_rankings` - 블로그 순위 데이터

### 캠페인 데이터 테이블
- `campaign_instagram_posts` - 캠페인별 인스타그램 게시물
- `campaign_instagram_reels` - 캠페인별 인스타그램 릴스
- `campaign_blogs` - 캠페인별 블로그 데이터

## 자동 데이터 수집

시스템은 매일 오전 9시에 자동으로 활성 캠페인의 데이터를 수집합니다:

1. **인스타그램 게시물**: 사용자별 최신 24개 게시물 썸네일 수집
2. **인스타그램 릴스**: 사용자별 최신 24개 릴스 썸네일 수집
3. **블로그**: 게시물 정보 및 네이버 검색 순위 수집

## 문제 해결

### 일반적인 문제
1. **데이터베이스 연결 오류**: PostgreSQL이 실행 중인지 확인
2. **API 키 오류**: `.env` 파일의 API 키 설정 확인
3. **S3 업로드 오류**: AWS 자격 증명 및 버킷 권한 확인
4. **OpenAI API 오류**: API 키 및 사용량 한도 확인

### 로그 확인
```bash
# Cron 작업 로그
tail -f /var/log/goodwave_cron.log

# 백엔드 로그
# uvicorn 실행 시 콘솔에서 확인

# 현재 cron 작업 확인
crontab -l
``

