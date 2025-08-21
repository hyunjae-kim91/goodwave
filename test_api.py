import asyncio
import requests
import json
import time

# API 서버 URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """헬스 체크 테스트"""
    print("=== 헬스 체크 테스트 ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"상태 코드: {response.status_code}")
        print(f"응답: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"헬스 체크 실패: {e}")
        return False

def test_root_endpoint():
    """루트 엔드포인트 테스트"""
    print("\n=== 루트 엔드포인트 테스트 ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"상태 코드: {response.status_code}")
        print(f"응답: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"루트 엔드포인트 테스트 실패: {e}")
        return False

def test_blog_info_api():
    """블로그 정보 API 테스트"""
    print("\n=== 블로그 정보 API 테스트 ===")
    
    # 테스트할 네이버 블로그 URL
    test_url = "https://blog.naver.com/PostView.naver?blogId=1suhyeon&logNo=223938502707"
    
    payload = {
        "url": test_url
    }
    
    try:
        print(f"요청 URL: {test_url}")
        print("API 호출 중... (시간이 걸릴 수 있습니다)")
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/blog-info",
            json=payload,
            timeout=180  # 3분 타임아웃
        )
        end_time = time.time()
        
        print(f"소요 시간: {end_time - start_time:.2f}초")
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("=== 블로그 정보 ===")
            print(f"게시 날짜: {result['post_date']}")
            print(f"좋아요 수: {result['post_likes']}")
            print(f"댓글 수: {result['post_comments']}")
            print(f"요청 URL: {result['url']}")
            return True
        else:
            print(f"오류 응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"블로그 정보 API 테스트 실패: {e}")
        return False

def test_invalid_url():
    """잘못된 URL 테스트"""
    print("\n=== 잘못된 URL 테스트 ===")
    
    payload = {
        "url": "https://google.com"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/blog-info",
            json=payload,
            timeout=30
        )
        print(f"상태 코드: {response.status_code}")
        print(f"응답: {response.text}")
        
        # 400 에러가 나와야 정상
        return response.status_code == 400
        
    except Exception as e:
        print(f"잘못된 URL 테스트 실패: {e}")
        return False

def main():
    """모든 테스트 실행"""
    print("FastAPI 서버 테스트를 시작합니다...")
    print("주의: 먼저 'uvicorn main:app --reload' 명령으로 서버를 시작해주세요.\n")
    
    tests = [
        ("헬스 체크", test_health_check),
        ("루트 엔드포인트", test_root_endpoint),
        ("잘못된 URL", test_invalid_url),
        ("블로그 정보 API", test_blog_info_api),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
        if not result:
            print(f"❌ {test_name} 테스트 실패")
        else:
            print(f"✅ {test_name} 테스트 성공")
    
    print("\n=== 테스트 결과 요약 ===")
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for test_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{test_name}: {status}")
    
    print(f"\n전체 테스트: {success_count}/{total_count} 성공")

if __name__ == "__main__":
    main() 