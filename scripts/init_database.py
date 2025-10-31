#!/usr/bin/env python3
"""
Goodwave Report 데이터베이스 초기화 스크립트
새로운 서버 배포시 데이터베이스 스키마와 초기 데이터를 설정합니다.
"""

import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append('/app')

try:
    from app.db.models import Base
    from app.db.database import engine
    from app import models
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    sys.exit(1)

def log_info(message):
    print(f"[INFO] {message}")

def log_success(message):
    print(f"✅ {message}")

def log_error(message):
    print(f"❌ {message}")

def create_tables():
    """데이터베이스 테이블 생성"""
    log_info("데이터베이스 테이블 생성 중...")
    
    try:
        Base.metadata.create_all(bind=engine)
        log_success("데이터베이스 테이블 생성 완료")
        return True
    except Exception as e:
        log_error(f"테이블 생성 실패: {e}")
        return False

def insert_grade_thresholds():
    """Instagram 등급 임계값 초기 데이터 삽입"""
    log_info("Instagram 등급 임계값 데이터 삽입 중...")
    
    try:
        with engine.connect() as conn:
            # 기존 데이터 확인
            existing = conn.execute(text(
                "SELECT COUNT(*) FROM instagram_grade_thresholds"
            )).fetchone()[0]
            
            if existing > 0:
                log_info(f"기존 등급 임계값 데이터 {existing}개 발견, 건너뜁니다.")
                return True
            
            # 등급 임계값 데이터 삽입
            grade_data = [
                ('프리미엄', 100001, None),
                ('골드', 30001, 100000),
                ('블루', 5001, 30000),
                ('레드', 1000, 5000)
            ]
            
            for grade_name, min_count, max_count in grade_data:
                conn.execute(text("""
                    INSERT INTO instagram_grade_thresholds 
                    (grade_name, min_view_count, max_view_count, created_at, updated_at)
                    VALUES (:grade_name, :min_count, :max_count, :now, :now)
                """), {
                    'grade_name': grade_name,
                    'min_count': min_count,
                    'max_count': max_count,
                    'now': datetime.now()
                })
            
            conn.commit()
            log_success(f"Instagram 등급 임계값 {len(grade_data)}개 삽입 완료")
            return True
            
    except Exception as e:
        log_error(f"등급 임계값 삽입 실패: {e}")
        return False

def insert_system_prompts():
    """시스템 프롬프트 초기 데이터 삽입"""
    log_info("시스템 프롬프트 데이터 삽입 중...")
    
    try:
        with engine.connect() as conn:
            # 기존 데이터 확인
            existing = conn.execute(text(
                "SELECT COUNT(*) FROM system_prompts"
            )).fetchone()[0]
            
            if existing > 0:
                log_info(f"기존 시스템 프롬프트 데이터 {existing}개 발견, 건너뜁니다.")
                return True
            
            # 구독동기 분류 프롬프트
            motivation_prompt = """
게시물의 설명과 해시태그(텍스트)와 사진(이미지)을 함께 분석하여, 구독동기정의 9개 중 하나로 분류합니다.

구독동기정의:
1. 실용정보: 실생활에 도움이 되는 정보, 팁, 노하우
2. 리뷰: 제품/서비스 사용 후기, 평가, 비교
3. 스토리: 개인적인 경험, 일상 이야기, 감정 공유
4. 자기계발: 성장, 학습, 동기부여 관련 콘텐츠
5. 웰니스: 건강, 운동, 정신건강, 라이프스타일
6. 프리미엄: 고급스러운 라이프스타일, 럭셔리 제품
7. 감성: 감정적 공감, 위로, 치유, 영감
8. 유머: 재미, 오락, 웃음, 엔터테인먼트
9. 비주얼: 시각적 아름다움, 미적 감각, 예술성

반드시 위 9개 중 하나로 분류하고, JSON 형식으로 응답하세요.
"""
            
            # 카테고리 분류 프롬프트
            category_prompt = """
게시물의 설명과 해시태그(텍스트)와 사진(이미지)을 함께 분석하여, 카테고리 9개 중 하나로 분류합니다.

카테고리:
1. 리빙: 홈 데코, 인테리어, 생활용품
2. 맛집: 음식점, 카페, 레스토랑 정보
3. 뷰티: 화장품, 스킨케어, 메이크업
4. 여행: 여행지, 숙박, 관광 정보
5. 운동/레저: 헬스, 스포츠, 야외활동
6. 육아/가족: 육아 정보, 가족 생활
7. 일상: 개인적인 일상, 라이프스타일
8. 패션: 의류, 액세서리, 스타일링
9. 푸드: 요리, 레시피, 식품 정보

반드시 위 9개 중 하나로 분류하고, JSON 형식으로 응답하세요.
"""
            
            prompts = [
                ('motivation_classification', 'OpenAI 구독동기 분류', motivation_prompt),
                ('category_classification', 'OpenAI 카테고리 분류', category_prompt)
            ]
            
            for prompt_key, name, content in prompts:
                conn.execute(text("""
                    INSERT INTO system_prompts 
                    (prompt_key, name, content, created_at, updated_at)
                    VALUES (:key, :name, :content, :now, :now)
                """), {
                    'key': prompt_key,
                    'name': name,
                    'content': content,
                    'now': datetime.now()
                })
            
            conn.commit()
            log_success(f"시스템 프롬프트 {len(prompts)}개 삽입 완료")
            return True
            
    except Exception as e:
        log_error(f"시스템 프롬프트 삽입 실패: {e}")
        return False

def verify_database():
    """데이터베이스 초기화 검증"""
    log_info("데이터베이스 초기화 검증 중...")
    
    try:
        with engine.connect() as conn:
            # 주요 테이블 존재 확인
            tables = [
                'campaigns', 'campaign_urls', 'influencer_profiles',
                'influencer_reels', 'campaign_instagram_reels',
                'instagram_grade_thresholds', 'system_prompts'
            ]
            
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
                log_info(f"테이블 '{table}': {result}개 레코드")
            
            log_success("데이터베이스 검증 완료")
            return True
            
    except Exception as e:
        log_error(f"데이터베이스 검증 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🗄️  Goodwave Report 데이터베이스 초기화")
    print("=" * 60)
    
    success = True
    
    # 1. 테이블 생성
    if not create_tables():
        success = False
    
    # 2. 등급 임계값 데이터 삽입
    if success and not insert_grade_thresholds():
        success = False
    
    # 3. 시스템 프롬프트 데이터 삽입
    if success and not insert_system_prompts():
        success = False
    
    # 4. 데이터베이스 검증
    if success and not verify_database():
        success = False
    
    print("=" * 60)
    if success:
        log_success("🎉 데이터베이스 초기화 완료!")
        print("\n다음 단계:")
        print("1. 환경 변수(.env) 설정 확인")
        print("2. 전체 서비스 시작: docker-compose up -d")
        print("3. 크론 작업 설정: docker-compose exec backend ./setup_cron.sh")
    else:
        log_error("❌ 데이터베이스 초기화 실패")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()