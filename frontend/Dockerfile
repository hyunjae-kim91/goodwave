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

# 프로덕션 빌드 생성
RUN npm run build

# serve를 전역으로 설치하여 정적 파일 서빙
RUN npm install -g serve

# 포트 3000 노출
EXPOSE 3000

# 프로덕션 빌드 서빙 (Host header 제한 없음)
CMD ["serve", "-s", "build", "-l", "3000"]