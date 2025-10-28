import time
import requests
from dotenv import load_dotenv
import os

load_dotenv()

class Instagram:
    def __init__(self):
        """Instagram 데이터 수집 클래스 초기화"""
        self.api_key = os.getenv("BRIGHTDATA_API_KEY")
        if not self.api_key:
            raise ValueError("BRIGHTDATA_API_KEY 환경변수가 설정되지 않았습니다.")
    
    def trigger_snapshot_request(self, dataset_id, params, data, max_retries=3):
        """스냅샷 수집 요청 (재시도 로직 포함)"""
        url = "https://api.brightdata.com/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        full_params = {"dataset_id": dataset_id, **params}
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 API 요청 시도 {attempt + 1}/{max_retries}")
                response = requests.post(url, headers=headers, params=full_params, json=data, timeout=30)

                print(f"🔍 API 응답 상태 코드: {response.status_code}")
                print(f"🔍 API 응답 헤더: {dict(response.headers)}")
                print(f"🔍 API 응답 텍스트: {response.text[:500]}...")  # 처음 500자만 출력

                # 502 Bad Gateway 오류 처리
                if response.status_code == 502:
                    print(f"❌ 502 Bad Gateway 오류 (시도 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10  # 10초, 20초, 30초 대기
                        print(f"⏳ {wait_time}초 후 재시도...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"502 Bad Gateway 오류가 {max_retries}번 연속 발생했습니다. BrightData 서버에 문제가 있을 수 있습니다.")
                
                # 5xx 서버 오류 처리
                if response.status_code >= 500:
                    print(f"❌ 서버 오류 {response.status_code} (시도 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        print(f"⏳ {wait_time}초 후 재시도...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"서버 오류 {response.status_code}가 {max_retries}번 연속 발생했습니다.")
                
                # 4xx 클라이언트 오류는 재시도하지 않음
                if response.status_code >= 400:
                    raise Exception(f"클라이언트 오류 {response.status_code}: {response.text}")

                try:
                    result = response.json()
                    snapshot_id = result.get("snapshot_id")
                    if not snapshot_id:
                        print(f"❌ snapshot_id가 응답에 없음. 전체 응답: {result}")
                        raise ValueError("snapshot_id not found in response.")
                    print(f"✅ 스냅샷 ID 획득: {snapshot_id}")
                    return snapshot_id
                except requests.exceptions.JSONDecodeError as e:
                    print(f"❌ JSON 파싱 실패: {e}")
                    print(f"❌ 응답 텍스트: {response.text}")
                    if attempt < max_retries - 1:
                        print(f"⏳ 5초 후 재시도...")
                        time.sleep(5)
                        continue
                    else:
                        raise Exception(f"Failed to parse trigger response as JSON. Status: {response.status_code}, Response: {response.text}")
                        
            except requests.exceptions.Timeout:
                print(f"❌ 요청 타임아웃 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"⏳ {wait_time}초 후 재시도...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"요청이 {max_retries}번 연속 타임아웃되었습니다.")
            
            except requests.exceptions.RequestException as e:
                print(f"❌ 네트워크 오류: {e} (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"⏳ {wait_time}초 후 재시도...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"네트워크 오류가 {max_retries}번 연속 발생했습니다: {e}")
        
        raise Exception(f"모든 재시도가 실패했습니다 ({max_retries}번 시도)")

    def wait_for_snapshot(self, snapshot_id, account_count=1, data_type="profile"):
        """스냅샷 수집 완료 대기 및 데이터 위치 확인"""
        url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"format": "json"}

        # 기본 1분 + 계정 수에 따른 추가 대기 시간
        base_wait_time = 60  # 기본 1분
        
        if data_type in ["post", "reel"]:
            # 게시글과 릴스: 계정 1개당 30초씩 추가
            additional_wait_time = account_count * 30
        else:
            # 프로필: 계정 1개당 1초씩 추가
            additional_wait_time = account_count
        
        initial_wait_time = base_wait_time + additional_wait_time
        
        # 최대 대기 시간 설정
        if data_type in ["post", "reel"]:
            # 게시글과 릴스: 기본 5분 + 계정 수만큼 30초씩 추가
            max_wait_time = 300 + (account_count * 30)
        else:
            # 프로필: 기본 5분 + 계정 수만큼 1초씩 추가
            max_wait_time = 300 + account_count
        
        print(f"⏰ 스냅샷 대기 시작: 초기 대기 {initial_wait_time}초, 최대 대기 {max_wait_time}초")
        
        # 초기 대기 시간
        print(f"⏳ 초기 대기 중... ({initial_wait_time}초)")
        time.sleep(initial_wait_time)
        
        wait_count = initial_wait_time
        consecutive_202_count = 0  # 연속 202 응답 카운트
        
        while wait_count < max_wait_time:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                print("Status Code:", response.status_code)

                if response.status_code == 202:
                    consecutive_202_count += 1
                    print(f"Still processing. Waiting 30 seconds... (연속 {consecutive_202_count}번)")
                    time.sleep(30)
                    wait_count += 30
                    continue

                if response.status_code != 200:
                    print(f"Unexpected status code: {response.status_code}")
                    if response.status_code >= 500:
                        print("서버 오류로 인한 대기 시간 연장...")
                        time.sleep(60)  # 서버 오류 시 더 오래 대기
                        wait_count += 60
                    else:
                        time.sleep(30)
                        wait_count += 30
                    continue

                result = response.json()
                print(f"🔍 Snapshot 응답 구조: {type(result)}")
                if isinstance(result, dict):
                    print(f"🔍 Snapshot 응답 키: {list(result.keys())}")
                    if "file_urls" in result:
                        print(f"🔍 file_urls 타입: {type(result['file_urls'])}, 내용: {result['file_urls']}")

                if isinstance(result, list):
                    print("Snapshot returned data directly.")
                    return {"type": "direct_data", "data": result}

                if result.get("status") == "done":
                    file_urls = result.get("file_urls", [])
                    if not file_urls:
                        raise Exception("Snapshot completed but no file URLs found.")
                    print(f"Snapshot complete. {len(file_urls)} file(s) available.")
                    print(f"🔍 file_urls 상세: {file_urls}")
                    return {"type": "file_urls", "urls": file_urls}

                print("Still processing. Waiting 30 seconds...")
                time.sleep(30)
                wait_count += 30
                
            except requests.exceptions.Timeout:
                print("요청 타임아웃, 30초 후 재시도...")
                time.sleep(30)
                wait_count += 30
                continue
                
            except Exception as e:
                print(f"Error while waiting for snapshot: {e}")
                time.sleep(30)
                wait_count += 30
        
        # 타임아웃 시에도 부분적으로 완료된 데이터가 있는지 확인
        try:
            print("⏰ 최대 대기 시간 초과, 마지막 상태 확인 중...")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "done":
                    file_urls = result.get("file_urls", [])
                    if file_urls:
                        print(f"✅ 타임아웃 후에도 데이터 발견: {len(file_urls)}개 파일")
                        return {"type": "file_urls", "urls": file_urls}
        except:
            pass
        
        raise Exception(f"Snapshot timeout after {max_wait_time} seconds")

    def download_snapshot_data(self, file_urls):
        """URL 리스트에서 JSON 데이터 다운로드"""
        all_data = []
        
        # URL 유효성 검사 및 필터링
        valid_urls = []
        for url in file_urls:
            if isinstance(url, str) and url.startswith(('http://', 'https://')):
                valid_urls.append(url)
            else:
                print(f"⚠️ 유효하지 않은 URL 건너뛰기: {url} (타입: {type(url)})")
        
        if not valid_urls:
            print("❌ 유효한 URL이 없습니다.")
            return all_data
        
        print(f"📥 {len(valid_urls)}개의 유효한 URL에서 데이터 다운로드 시작")
        
        for file_url in valid_urls:
            try:
                print(f"⬇️ Downloading from: {file_url}")
                res = requests.get(file_url)
                res.raise_for_status()  # HTTP 오류 체크
                
                data = res.json()
                if isinstance(data, list):
                    all_data.extend(data)
                else:
                    all_data.append(data)
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ HTTP 요청 실패 {file_url}: {e}")
            except ValueError as e:
                print(f"❌ JSON 파싱 실패 {file_url}: {e}")
            except Exception as e:
                print(f"❌ 예상치 못한 오류 {file_url}: {e}")
        
        print(f"✅ 데이터 다운로드 완료: {len(all_data)}개 항목")
        return all_data

    async def get_reel_data(self, reel_url: str, config: dict) -> dict:
        """인스타그램 릴스 URL에서 데이터를 수집합니다. (캠페인용)"""
        try:
            print(f"🎬 릴스 데이터 수집 시작: {reel_url}")
            
            # brightdata.json에서 설정 로드
            import json
            from pathlib import Path
            
            config_path = Path(__file__).parent / "backend" / "brightdata.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                brightdata_config = json.load(f)
            
            # 릴스 설정에서 params 가져오기
            reel_config = brightdata_config.get("instagram", {}).get("reel", {})
            campaign_params = reel_config.get("params", {}).copy()
            
            # 캠페인용으로 type과 discover_by 제거
            campaign_params.pop("type", None)
            campaign_params.pop("discover_by", None)
            
            # config에서 include_errors 설정 적용
            if "include_errors" in config:
                campaign_params["include_errors"] = config["include_errors"]
            
            print(f"캠페인 릴스 설정: {campaign_params}")
            
            # 릴스 데이터 수집
            dataset_id = reel_config.get("dataset_id")
            if not dataset_id:
                raise ValueError("reel dataset_id가 설정되지 않았습니다.")
            
            # 스냅샷 요청
            snapshot_id = self.trigger_snapshot_request(
                dataset_id=dataset_id,
                params=campaign_params,
                data={"url": reel_url}
            )
            
            # 스냅샷 완료 대기
            result = self.wait_for_snapshot(snapshot_id)
            
            # 데이터 다운로드
            if result["type"] == "direct_data":
                reel_data = result["data"]
                print(f"📊 직접 반환된 릴스 데이터: {len(reel_data)}개 항목")
                if reel_data and len(reel_data) > 0:
                    print(f"📋 첫 번째 항목 키: {list(reel_data[0].keys()) if isinstance(reel_data[0], dict) else 'Not a dict'}")
            else: # result["type"] == "file_urls"
                file_urls = result["urls"]
                reel_data = self.download_snapshot_data(file_urls)
                print(f"📊 파일에서 다운로드된 릴스 데이터: {len(reel_data)}개 항목")
            
            print(f"✅ 릴스 데이터 수집 완료: {reel_url}")
            return reel_data
            
        except Exception as e:
            print(f"❌ 릴스 데이터 수집 실패: {str(e)}")
            raise

    async def get_post_data(self, post_url: str, config: dict) -> dict:
        """인스타그램 게시물 URL에서 데이터를 수집합니다. (캠페인용)"""
        try:
            print(f"📸 게시물 데이터 수집 시작: {post_url}")
            
            # brightdata.json에서 설정 로드
            import json
            from pathlib import Path
            
            config_path = Path(__file__).parent / "backend" / "brightdata.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                brightdata_config = json.load(f)
            
            # 게시물 설정에서 params 가져오기
            post_config = brightdata_config.get("instagram", {}).get("post", {})
            campaign_params = post_config.get("params", {}).copy()
            
            # 캠페인용으로 type과 discover_by 제거
            campaign_params.pop("type", None)
            campaign_params.pop("discover_by", None)
            
            # config에서 include_errors 설정 적용
            if "include_errors" in config:
                campaign_params["include_errors"] = config["include_errors"]
            
            print(f"캠페인 게시물 설정: {campaign_params}")
            
            # 게시물 데이터 수집
            dataset_id = post_config.get("dataset_id")
            if not dataset_id:
                raise ValueError("post dataset_id가 설정되지 않았습니다.")
            
            # 스냅샷 요청
            snapshot_id = self.trigger_snapshot_request(
                dataset_id=dataset_id,
                params=campaign_params,
                data={"url": post_url}
            )
            
            # 스냅샷 완료 대기
            result = self.wait_for_snapshot(snapshot_id)
            
            # 데이터 다운로드
            if result["type"] == "direct_data":
                post_data = result["data"]
                print(f"📊 직접 반환된 게시물 데이터: {len(post_data)}개 항목")
                if post_data and len(post_data) > 0:
                    print(f"📋 첫 번째 항목 키: {list(post_data[0].keys()) if isinstance(post_data[0], dict) else 'Not a dict'}")
            else: # result["type"] == "file_urls"
                file_urls = result["urls"]
                post_data = self.download_snapshot_data(file_urls)
                print(f"📊 파일에서 다운로드된 게시물 데이터: {len(post_data)}개 항목")
            
            print(f"✅ 게시물 데이터 수집 완료: {post_url}")
            return post_data
            
        except Exception as e:
            print(f"❌ 게시물 데이터 수집 실패: {str(e)}")
            raise