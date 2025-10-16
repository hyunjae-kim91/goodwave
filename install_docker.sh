#!/bin/bash

set -e  # 오류 발생시 스크립트 중단

echo "🐳 Docker 설치 스크립트 시작..."

# 시스템 업데이트
echo "📦 시스템 패키지 업데이트..."
sudo apt-get update

# 필요한 패키지 설치
echo "📦 필요한 패키지 설치..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    apt-transport-https \
    software-properties-common

# Docker의 공식 GPG 키 추가
echo "🔑 Docker GPG 키 추가..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Docker 저장소 추가
echo "📋 Docker 저장소 추가..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 패키지 목록 업데이트
sudo apt-get update

# Docker Engine 설치
echo "🐳 Docker Engine 설치..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 현재 사용자를 docker 그룹에 추가
echo "👤 사용자를 docker 그룹에 추가..."
sudo usermod -aG docker $USER

# Docker 서비스 시작 및 활성화
echo "🔄 Docker 서비스 시작..."
sudo systemctl start docker
sudo systemctl enable docker

# Docker Compose 설치 (별도 설치)
echo "🐙 Docker Compose 설치..."
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Node.js 설치 (프론트엔드용)
echo "📦 Node.js 설치..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python 3 및 pip 설치 확인
echo "🐍 Python 및 pip 설치 확인..."
sudo apt-get install -y python3 python3-pip python3-venv

# Docker 설치 확인
echo "✅ Docker 설치 확인..."
sudo docker --version
docker-compose --version
node --version
npm --version
python3 --version

echo ""
echo "🎉 Docker 설치 완료!"
echo ""
echo "⚠️  중요: 현재 사용자가 docker 그룹에 추가되었습니다."
echo "   변경사항을 적용하려면 다음 중 하나를 실행하세요:"
echo "   1) newgrp docker"
echo "   2) 로그아웃 후 다시 로그인"
echo ""
echo "📝 설치된 버전:"
sudo docker --version
docker-compose --version
echo ""
echo "🚀 이제 ./setup_and_run.sh 를 실행하여 전체 시스템을 시작할 수 있습니다!"