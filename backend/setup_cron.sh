#!/bin/bash

# Cron 작업 설정 스크립트
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_SCRIPT="$BACKEND_DIR/cron_job.py"

# 기본적으로 백엔드 가상환경의 Python을 사용한다.
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
PYTHON_PATH="$VENV_PYTHON"

# 가상환경이 없거나 실행 권한이 없는 경우를 대비한 폴백 처리
if [ ! -x "$PYTHON_PATH" ]; then
    echo "⚠️  백엔드 가상환경을 찾을 수 없어서 시스템 Python을 사용합니다."
    PYTHON_PATH="/usr/bin/python3"
fi

# cron_job.py에 실행 권한 부여
chmod +x "$CRON_SCRIPT"

# 현재 사용자의 crontab에 작업 추가
# 매일 오전 9시에 실행
(crontab -l 2>/dev/null || echo "") | grep -v "$CRON_SCRIPT" | { cat; echo "0 9 * * * $PYTHON_PATH $CRON_SCRIPT >> /var/log/goodwave_cron.log 2>&1"; } | crontab -

echo "Cron job has been set up successfully!"
echo "The data collection will run daily at 9:00 AM"
echo "Log file: /var/log/goodwave_cron.log"
echo ""
echo "To view current crontab:"
echo "crontab -l"
echo ""
echo "To remove the cron job:"
echo "crontab -l | grep -v '$CRON_SCRIPT' | crontab -"
