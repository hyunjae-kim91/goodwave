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

def should_run_collection() -> bool:
    """KST 오전 9시인지 확인 (9:00 ~ 9:59 사이)"""
    kst_now = now_kst()
    return kst_now.hour == 9

async def main():
    """Cron job main function"""
    try:
        kst_now = now_kst()
        print(f"=== Cron Job Check at {kst_now.strftime('%Y-%m-%d %H:%M:%S')} (KST) ===")
        
        if not should_run_collection():
            print(f"⏭️  현재 시간이 KST 오전 9시가 아니므로 스킵합니다. (현재: {kst_now.hour}시)")
            return
        
        print("=== Goodwave Data Collection Cron Job Started (KST 9:00) ===")
        await scheduler_service.run_scheduled_collection()
        print("=== Goodwave Data Collection Cron Job Completed ===")
    except Exception as e:
        print(f"=== Cron Job Error: {str(e)} ===")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())