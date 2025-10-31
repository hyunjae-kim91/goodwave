#!/usr/bin/env python3
"""
수동으로 프로필 데이터를 수정하는 스크립트
BrightData에서 올바른 데이터가 반환되었으므로 이를 직접 DB에 반영
"""
import os
import sys
sys.path.append('/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import InfluencerProfile
from datetime import datetime, timedelta

def now_kst():
    return datetime.utcnow() + timedelta(hours=9)

# 데이터베이스 연결
DATABASE_URL = "postgresql://postgres:History1014!@goodwave.cccmpneqxe0q.ap-northeast-2.rds.amazonaws.com:5432/goodwave_report"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # kwakmid 프로필 찾기
    profile = session.query(InfluencerProfile).filter(
        InfluencerProfile.username == "kwakmid"
    ).first()
    
    if profile:
        # BrightData에서 받은 실제 데이터로 업데이트
        profile.full_name = "곽민선"
        profile.followers = 4210
        profile.following = 1169
        profile.bio = "Contact_DM\nkwakmid@naver.com"
        profile.posts_count = 46
        profile.is_business_account = True
        profile.is_professional_account = True
        profile.is_verified = False
        profile.avg_engagement = 0.0141
        profile.account = "business"
        profile.email_address = "kwakmid@naver.com"
        profile.profile_name = "곽민선"
        profile.updated_at = now_kst()
        
        session.commit()
        print(f"✅ kwakmid 프로필 업데이트 완료!")
        print(f"   팔로워: {profile.followers}")
        print(f"   팔로잉: {profile.following}")
        print(f"   이름: {profile.full_name}")
        print(f"   바이오: {profile.bio}")
    else:
        print("❌ kwakmid 프로필을 찾을 수 없습니다.")

except Exception as e:
    print(f"❌ 오류 발생: {str(e)}")
    session.rollback()
finally:
    session.close()