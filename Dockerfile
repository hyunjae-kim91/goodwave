# Playwright 의존성이 포함된 공식 이미지 사용 (Ubuntu 22.04 기반)
FROM mcr.microsoft.com/playwright/python:v1.45.1-jammy

# 작업 디렉토리
WORKDIR /app

# 파이썬 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# (옵션) 이미 브라우저가 포함되어 있으나, 확실히 chromium만 보장하려면 아래 줄 유지
# RUN playwright install chromium

# 포트 노출
EXPOSE 8000

# 헬스체크 (Playwright 베이스에 curl 포함)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]