# Goodwave Blog API

네이버 블로그 포스트 정보를 추출하는 FastAPI 기반 웹 API입니다.

## 기능

- 네이버 블로그 URL을 입력받아 다음 정보를 추출:
  - 게시 날짜
  - 좋아요 수
  - 댓글 수
- **다양한 URL 형태 자동 지원**:
  - 짧은 형태: `https://blog.naver.com/blogId/logNo`
  - PostView 형태: `https://blog.naver.com/PostView.naver?blogId=xxx&logNo=xxx`

## 지원하는 URL 형태

### 1. 짧은 형태 URL (자동 변환)
```
https://blog.naver.com/aaa2981/223951329398
↓ 자동 변환
https://blog.naver.com/PostView.naver?blogId=aaa2981&logNo=223951329398
```

### 2. PostView 형태 URL (직접 사용)
```
https://blog.naver.com/PostView.naver?blogId=aaa2981&logNo=223951329398
```

## API 엔드포인트

### POST /blog-info
네이버 블로그 포스트 정보를 가져옵니다.

**요청 예시 (짧은 형태):**
```json
{
  "url": "https://blog.naver.com/aaa2981/223951329398"
}
```

**요청 예시 (PostView 형태):**
```json
{
  "url": "https://blog.naver.com/PostView.naver?blogId=aaa2981&logNo=223951329398"
}
```

**응답 예시:**
```json
{
  "post_date": "2025-01-18",
  "post_likes": "18",
  "post_comments": "2",
  "url": "https://blog.naver.com/aaa2981/223951329398",
  "converted_url": "https://blog.naver.com/PostView.naver?blogId=aaa2981&logNo=223951329398"
}
```

**응답 필드 설명:**
- `post_date`: 게시 날짜 (YYYY-MM-DD 형식)
- `post_likes`: 좋아요 수
- `post_comments`: 댓글 수
- `url`: 요청한 원본 URL
- `converted_url`: 변환된 URL (짧은 형태를 사용했을 때만 포함)

### GET /health
API 상태를 확인합니다.

### GET /
API 정보를 확인합니다.

## 로컬 개발

### 1. 의존성 설치
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 서버 실행
```bash
uvicorn main:app --reload
```

### 3. 테스트
```bash
# 전체 API 테스트
python test_api.py

# URL 변환 기능만 테스트
python test_url_conversion.py
```

## Docker 배포

### 1. Docker 빌드 및 실행
```bash
# Docker Compose 사용
docker-compose up -d

# 또는 Dockerfile 직접 사용
docker build -t goodwave-blog-api .
docker run -p 8000:8000 goodwave-blog-api
```

### 2. 배포 스크립트 사용
```bash
chmod +x deploy.sh
./deploy.sh
```

## EC2 배포 가이드

### 1. EC2 인스턴스 준비
- Ubuntu 20.04 LTS 이상 권장
- 최소 2GB RAM, 1vCPU
- 보안 그룹에서 8000 포트 열기

### 2. EC2에 Docker 설치
```bash
# Docker 설치
sudo apt update
sudo apt install -y docker.io docker-compose-plugin

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 로그아웃 후 다시 로그인하거나 다음 명령 실행
newgrp docker
```

### 3. 프로젝트 배포
```bash
# 프로젝트 클론/업로드
scp -r goodwave_blog_api ubuntu@your-ec2-ip:/home/ubuntu/

# EC2 인스턴스에 SSH 접속
ssh ubuntu@your-ec2-ip

# 프로젝트 디렉토리로 이동
cd goodwave_blog_api

# 배포 실행
chmod +x deploy.sh
./deploy.sh
```

### 4. 방화벽 설정 (필요한 경우)
```bash
sudo ufw allow 8000
```

### 5. 접속 확인
```
http://your-ec2-ip:8000
```

## API 문서

서버 실행 후 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 주요 특징

- **URL 자동 변환**: 짧은 형태의 네이버 블로그 URL을 자동으로 PostView 형태로 변환
- **다양한 형태 지원**: 기존 PostView URL과 새로운 짧은 형태 URL 모두 지원
- **상세한 응답**: 원본 URL과 변환된 URL 정보를 모두 제공
- **Docker 최적화**: Playwright 전용 Docker 이미지 사용으로 안정성 향상

## 주의사항

- 네이버 블로그 URL만 지원됩니다
- Playwright를 사용하여 브라우저 자동화를 수행하므로 리소스 사용량이 높을 수 있습니다
- EC2에서 실행 시 충분한 메모리와 CPU를 확보해주세요

## 트러블슈팅

### Playwright 관련 오류
```bash
# 브라우저 재설치
playwright install chromium
playwright install-deps
```

### Docker 메모리 부족
```bash
# Docker 메모리 제한 증가
docker run -m 2g -p 8000:8000 goodwave-blog-api
```

### 권한 오류
```bash
# deploy.sh 실행 권한 부여
chmod +x deploy.sh
```

## 업데이트 내역

### v1.1.0
- ✨ 짧은 형태 네이버 블로그 URL 지원 추가
- 🔄 URL 자동 변환 기능 구현
- 📝 응답에 변환된 URL 정보 추가
- 🧪 URL 변환 테스트 추가 