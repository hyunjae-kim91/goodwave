# Node.js 18 이미지 사용
FROM node:18-alpine

# 작업 디렉토리 설정
WORKDIR /app

# package.json과 package-lock.json 복사 (캐싱 최적화)
COPY package*.json ./

# 의존성 설치 (dev dependencies 포함, 빌드용)
RUN npm ci --no-audit --prefer-offline && \
    npm cache clean --force

# 소스 코드 복사
COPY . .

# 빌드 디렉토리 생성 (볼륨 마운트를 위해)
RUN mkdir -p /app/build

# 기본 명령어 (docker-compose에서 오버라이드됨)
CMD ["npm", "run", "build"]