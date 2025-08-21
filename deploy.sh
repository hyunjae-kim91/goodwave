#!/usr/bin/env bash
set -euo pipefail

echo "=== Goodwave Blog API 배포 시작 ==="

# --- 사전 점검 ---
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker가 설치되어 있지 않습니다. 먼저 설치하세요."
  exit 1
fi

# docker compose(플러그인) 확인
if ! docker compose version >/dev/null 2>&1; then
  echo "❌ Docker Compose 플러그인이 없습니다. 'sudo apt install -y docker-compose-plugin' 후 다시 실행하세요."
  exit 1
fi

# 데몬 접근 가능 여부
if ! docker info >/dev/null 2>&1; then
  cat <<EOF
❌ Docker 데몬에 접근할 수 없습니다.
   - 'sudo systemctl enable --now docker' 실행
   - 'sudo usermod -aG docker $USER' 후 'newgrp docker' 또는 재로그인
EOF
  exit 1
fi

# --- Compose 파일 경고 제거 (version: 라인 삭제) ---
if [ -f docker-compose.yml ]; then
  sed -i '/^[[:space:]]*version:/d' docker-compose.yml || true
fi

# --- 기존 컨테이너 정리 ---
echo "기존 컨테이너 중지/정리..."
docker compose down --remove-orphans || true

# --- 빌드 & 기동 ---
echo "Docker 이미지 빌드..."
docker compose build

echo "컨테이너 시작..."
docker compose up -d

echo "컨테이너 상태..."
docker compose ps

# --- 헬스체크 (재시도) ---
echo "API 헬스 체크 중..."
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
TRIES=20
SLEEP=3
ok=0
for i in $(seq 1 "$TRIES"); do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep "$SLEEP"
done

if [ "$ok" -eq 1 ]; then
  echo "✅ 헬스체크 통과: $HEALTH_URL"
else
  echo "⚠️ 헬스체크 실패. 최근 로그:"
  docker compose logs --tail=100 || true
fi

echo "=== 배포 완료 ==="
echo "API:        http://localhost:8000"
echo "API 문서:   http://localhost:8000/docs"