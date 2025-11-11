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

시스템은 **매일 KST 오전 9시**에 자동으로 활성 캠페인의 데이터를 수집합니다.

### 실행 방식

자동 수집은 두 가지 방식으로 동작합니다:

1. **외부 Cron Job** (`backend/cron_job.py`)
   - 시스템 crontab에 등록되어 매 시간마다 실행
   - 스크립트 내부에서 KST 시간을 확인하여 KST 오전 9시일 때만 실제 수집 작업 수행
   - 서버 시간대와 무관하게 KST 기준으로 동작

2. **내부 백그라운드 스케줄러** (`CampaignScheduleRunner`)
   - FastAPI 애플리케이션 시작 시 백그라운드 스레드로 실행
   - 1시간마다 확인하며, KST 오전 9시일 때만 실행
   - 서버 재시작 없이도 동작 가능

### 실행 흐름

```
1. Cron Job 실행 또는 백그라운드 스케줄러 트리거
   ↓
2. KST 시간 확인 (오전 9시인지 체크)
   ↓
3. SchedulerService.run_scheduled_collection() 호출
   ↓
4. 활성 스케줄 조회
   - is_active == True
   - 오늘 날짜(KST 기준)가 start_date ~ end_date 범위 내
   ↓
5. 각 스케줄에 대해 _process_schedule() 실행
   ↓
6. 중복 수집 방지 체크
   - 오늘 날짜에 이미 수집된 데이터가 있는지 확인
   - 있으면 스킵
   ↓
7. 채널별 수집 실행
   - Instagram Reel: _collect_campaign_instagram_reels()
   - Instagram Post: _collect_campaign_instagram_posts()
   - Blog: _collect_campaign_blogs()
```

### 수집 항목

1. **인스타그램 게시물**: 사용자별 최신 24개 게시물 썸네일 수집
2. **인스타그램 릴스**: 사용자별 최신 24개 릴스 썸네일 수집
3. **블로그**: 게시물 정보 및 네이버 검색 순위 수집

### 릴스 수집 상세 과정

#### 특정 릴스 URL인 경우 (`/reel/` 포함):
1. **신규 수집 작업 생성**: `CampaignReelCollectionService`를 통해 `campaign_reel_collection_jobs` 테이블에 작업 생성
2. **BrightData로 전송**: 대기 중인 작업을 BrightData API로 전송
3. **수집 완료 대기 및 처리**: 30초 대기 후 `CollectionWorker`가 BrightData 응답 처리 및 데이터 저장
4. **캠페인 테이블 동기화**: 완료된 작업을 `campaign_instagram_reels` 테이블로 동기화 (등급, 분류 결과 포함)

#### 사용자 프로필 URL인 경우:
1. **프로필 조회**: `InfluencerProfile`에서 사용자 정보 조회
2. **최신 릴스 가져오기**: `InfluencerReel`에서 최신 10개 릴스 조회
3. **캠페인 테이블에 추가**: 기존 데이터가 없으면 `campaign_instagram_reels`에 추가

### 중복 방지 로직

- 각 스케줄 처리 시 오늘 날짜(`collection_date`, KST 기준)에 이미 수집된 데이터가 있는지 확인
- 이미 수집된 데이터가 있으면 스킵하여 중복 수집 방지
- 모든 시간은 KST(UTC+9) 기준으로 처리

### 데이터베이스 구조

#### `collection_schedules` 테이블
- `campaign_id`: 캠페인 ID
- `channel`: 채널 타입 (instagram_reel, instagram_post, blog)
- `campaign_url`: 수집 대상 URL
- `start_date`, `end_date`: 수집 기간
- `is_active`: 활성화 여부

#### 수집 결과 저장
- Instagram Reel → `campaign_instagram_reels`
- Instagram Post → `campaign_instagram_posts`
- Blog → `campaign_blogs`

### Cron Job 설정

```bash
# Cron job 설정 스크립트 실행
cd backend
chmod +x setup_cron.sh
./setup_cron.sh
```

이 스크립트는 다음을 수행합니다:
- 매 시간마다 `cron_job.py`를 실행하도록 crontab에 등록
- 스크립트 내부에서 KST 오전 9시인지 확인하여 실제 수집 작업 수행
- 서버 시간대와 무관하게 KST 기준으로 동작

### 특징

- **시간대 독립적**: 모든 시간은 KST(UTC+9) 기준으로 처리되며, 서버 시간대와 무관하게 동작
- **에러 처리**: 개별 스케줄 실패 시에도 다음 스케줄 계속 처리
- **자동 등급 계산**: 릴스 수집 시 인플루언서 등급 자동 계산
- **분류 결과 연동**: `influencer_reels`의 분류 결과를 캠페인 데이터에 포함

## 문제 해결

### 일반적인 문제
1. **데이터베이스 연결 오류**: PostgreSQL이 실행 중인지 확인
2. **API 키 오류**: `.env` 파일의 API 키 설정 확인
3. **S3 업로드 오류**: AWS 자격 증명 및 버킷 권한 확인
4. **OpenAI API 오류**: API 키 및 사용량 한도 확인

### 스케줄 상태 확인

#### 1. API를 통한 확인

```bash
# 캠페인 스케줄러 상태 확인
curl http://localhost:8000/api/admin/campaign-schedule-runner-status

# 수집 워커 상태 확인
curl http://localhost:8000/api/admin/collection-worker-status
```

#### 2. 컨테이너 내에서 직접 확인

```bash
# 컨테이너 접속
docker exec -it <container_name> /bin/bash

# Cron job이 등록되어 있는지 확인
crontab -l

# Cron job 로그 확인
tail -f /var/log/goodwave_cron.log

# 또는 최근 로그 확인
tail -n 100 /var/log/goodwave_cron.log

# Python 프로세스 확인 (백그라운드 스케줄러)
ps aux | grep python | grep campaign-schedule-runner

# 현재 KST 시간 확인 (스크립트 내부에서 사용하는 방식)
python3 -c "from datetime import datetime, timedelta; kst = datetime.utcnow() + timedelta(hours=9); print(f'Current KST: {kst.strftime(\"%Y-%m-%d %H:%M:%S\")}')"

# Cron job이 실행되는지 테스트
# (KST 오전 9시가 아닐 때는 스킵 메시지가 출력됨)
python3 /path/to/backend/cron_job.py
```

#### 3. 로그 확인

```bash
# Cron 작업 로그
tail -f /var/log/goodwave_cron.log

# 백엔드 애플리케이션 로그
# uvicorn 실행 시 콘솔에서 확인하거나
docker logs <container_name> -f

# 현재 cron 작업 확인
crontab -l
```

#### 4. 수집 스케줄 확인

```bash
# API를 통해 활성 스케줄 확인
curl http://localhost:8000/api/admin/collection-schedules

# 또는 컨테이너 내에서 직접 DB 확인
docker exec -it <container_name> psql -U <db_user> -d <db_name> -c "SELECT * FROM collection_schedules WHERE is_active = true;"
```

