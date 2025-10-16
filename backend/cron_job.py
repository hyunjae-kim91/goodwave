#!/usr/bin/env python3
"""
정기 수집을 위한 Cron Job 스크립트
매일 오전 9시에 실행되도록 crontab에 등록:
0 9 * * * /usr/bin/python3 /path/to/goodwave/report/backend/cron_job.py
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from app.services.scheduler_service import scheduler_service

async def main():
    """Cron job main function"""
    try:
        print("=== Goodwave Data Collection Cron Job Started ===")
        await scheduler_service.run_scheduled_collection()
        print("=== Goodwave Data Collection Cron Job Completed ===")
    except Exception as e:
        print(f"=== Cron Job Error: {str(e)} ===")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())