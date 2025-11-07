#!/usr/bin/env python3
"""
캠페인 이름에서 탭 문자, 줄바꿈 문자 등을 제거하는 스크립트
"""

import sys
from app.db.database import SessionLocal
from app.db import models

def fix_campaign_names():
    """모든 캠페인 이름에서 불필요한 공백 문자 제거"""
    db = SessionLocal()
    
    try:
        campaigns = db.query(models.Campaign).all()
        fixed_count = 0
        
        print(f"📋 총 {len(campaigns)}개 캠페인 확인 중...")
        
        for campaign in campaigns:
            original_name = campaign.name
            # 탭, 줄바꿈, 캐리지 리턴 제거 후 양쪽 공백 제거
            cleaned_name = original_name.strip().replace('\t', '').replace('\n', '').replace('\r', '')
            
            if original_name != cleaned_name:
                print(f"🔧 수정: '{original_name}' → '{cleaned_name}'")
                print(f"   원본 길이: {len(original_name)}, 수정 길이: {len(cleaned_name)}")
                print(f"   원본 바이트: {original_name.encode('utf-8')}")
                print(f"   수정 바이트: {cleaned_name.encode('utf-8')}")
                
                campaign.name = cleaned_name
                fixed_count += 1
            else:
                print(f"✅ 정상: '{original_name}'")
        
        if fixed_count > 0:
            db.commit()
            print(f"\n✅ {fixed_count}개 캠페인 이름 수정 완료!")
        else:
            print(f"\n✅ 수정할 캠페인이 없습니다.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    fix_campaign_names()

