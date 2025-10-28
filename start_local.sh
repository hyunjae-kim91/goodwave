#!/bin/bash

# Goodwave 로컬 개발 환경 통합 실행 스크립트
echo "Starting Goodwave local development environment..."

# 필요한 환경 확인
echo "Checking environment..."

# Node.js 확인
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed. Please install Python3 first."
    exit 1
fi

# pip 확인
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "Error: pip is not installed. Please install pip first."
    exit 1
fi

echo "Environment check passed!"

# 사용자에게 실행 옵션 선택
echo ""
echo "Choose an option:"
echo "1) Start backend only"
echo "2) Start frontend only"
echo "3) Start both (backend in background, frontend in foreground)"
echo "4) Exit"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "Starting backend only..."
        ./start_backend.sh
        ;;
    2)
        echo "Starting frontend only..."
        ./start_frontend.sh
        ;;
    3)
        echo "Starting both backend and frontend..."
        echo "Backend will run in background, frontend in foreground"
        echo "To stop backend, use: pkill -f 'uvicorn app.main:app'"
        echo ""
        
        # Backend를 백그라운드에서 실행
        echo "Starting backend in background..."
        nohup ./start_backend.sh > backend.log 2>&1 &
        BACKEND_PID=$!
        
        # 백엔드가 시작될 시간을 줌
        echo "Waiting for backend to start..."
        sleep 5
        
        # 백엔드가 실행 중인지 확인
        if ps -p $BACKEND_PID > /dev/null; then
            echo "Backend started successfully (PID: $BACKEND_PID)"
            echo "Backend logs: tail -f backend.log"
        else
            echo "Failed to start backend. Check backend.log for errors."
            exit 1
        fi
        
        echo ""
        echo "Starting frontend..."
        ./start_frontend.sh
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        exit 1
        ;;
esac