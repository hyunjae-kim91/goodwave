# Node.js 18 이미지 사용
FROM node:18-alpine

# 작업 디렉토리 설정
WORKDIR /app

# package.json과 package-lock.json 복사 (캐싱 최적화)
COPY package*.json ./

# 의존성 설치 (캐시 정리 포함)
RUN npm ci --only=production --no-audit --prefer-offline && \
    npm cache clean --force

# 소스 코드 복사
COPY . .

# 포트 3000 노출
EXPOSE 3000

# 개발 서버 실행
CMD ["npm", "start"]