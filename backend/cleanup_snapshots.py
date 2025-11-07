#!/usr/bin/env python3
"""
data_snapshots 폴더의 오래된 파일을 정리하는 스크립트
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
backend_root = Path(__file__).parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.services.brightdata_service import BrightDataService

def cleanup_snapshots(retention_days: int = 7, max_files: int = 200):
    """스냅샷 파일 정리"""
    print(f"🧹 스냅샷 파일 정리 시작...")
    print(f"   보관 기간: {retention_days}일")
    print(f"   최대 파일 개수: {max_files}개")
    
    try:
        service = BrightDataService()
        service.snapshot_retention_days = retention_days
        service.snapshot_max_files = max_files
        service._cleanup_old_snapshots()
        print("✅ 정리 완료!")
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="스냅샷 파일 정리")
    parser.add_argument("--days", type=int, default=7, help="보관 기간 (일, 기본값: 7)")
    parser.add_argument("--max-files", type=int, default=200, help="최대 파일 개수 (기본값: 200)")
    
    args = parser.parse_args()
    cleanup_snapshots(args.days, args.max_files)

