#!/bin/bash

echo "🧹 Docker Cleanup Starting..."

# 중지된 컨테이너들 삭제
echo "Removing stopped containers..."
docker container prune -f

# 사용되지 않는 이미지들 삭제
echo "Removing unused images..."
docker image prune -a -f

# 사용되지 않는 볼륨들 삭제
echo "Removing unused volumes..."
docker volume prune -f

# 사용되지 않는 네트워크들 삭제
echo "Removing unused networks..."
docker network prune -f

# 빌드 캐시 정리
echo "Cleaning build cache..."
docker builder prune -a -f

# 전체 시스템 정리 (조심스럽게)
echo "Running system prune..."
docker system prune -a -f --volumes

echo "✅ Docker cleanup completed!"

# 정리된 공간 확인
echo ""
echo "📊 Docker space usage after cleanup:"
docker system df