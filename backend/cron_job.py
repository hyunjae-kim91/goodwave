#!/usr/bin/env python3
"""
정기 수집을 위한 Cron Job 스크립트
매일 KST 오전 9시에 실행되도록 crontab에 등록:
매 시간마다 실행되지만, KST 오전 9시일 때만 실제 수집 작업을 수행합니다.
0 * * * * /usr/bin/python3 /path/to/goodwave/report/backend/cron_job.py
또는 더 자주 확인하려면:
*/15 * * * * /usr/bin/python3 /path/to/goodwave/report/backend/cron_job.py
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from app.services.scheduler_service import scheduler_service

KST_OFFSET = timedelta(hours=9)

def now_kst() -> datetime:
    """한국 시간(KST) 기준 현재 시간 반환"""
    return datetime.utcnow() + KST_OFFSET

async def main():
    """Cron job main function - 매 시간마다 실행하여 각 스케줄의 설정된 시간에 맞는 것만 처리"""
    try:
        kst_now = now_kst()
        print(f"=== Cron Job Check at {kst_now.strftime('%Y-%m-%d %H:%M:%S')} (KST) ===")
        
        # 매 시간마다 실행 (스케줄러 내부에서 각 스케줄의 시간을 체크)
        print("=== Goodwave Data Collection Cron Job Started ===")
        await scheduler_service.run_scheduled_collection()
        print("=== Goodwave Data Collection Cron Job Completed ===")
    except Exception as e:
        print(f"=== Cron Job Error: {str(e)} ===")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())