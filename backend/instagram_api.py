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
    
    def trigger_snapshot_request(self, dataset_id, params, data):
        """스냅샷 수집 요청"""
        url = "https://api.brightdata.com/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        full_params = {"dataset_id": dataset_id, **params}
        response = requests.post(url, headers=headers, params=full_params, json=data)
        
        print(f"📡 BrightData API 응답 상태: {response.status_code}")
        print(f"📋 응답 헤더: {dict(response.headers)}")
        print(f"📄 응답 내용: {response.text[:500]}...")  # 첫 500자만 출력
        
        # 상태 코드 확인
        if response.status_code != 200:
            raise Exception(f"BrightData API 요청 실패: HTTP {response.status_code} - {response.text}")

        try:
            result = response.json()
            snapshot_id = result.get("snapshot_id")
            if not snapshot_id:
                raise ValueError(f"snapshot_id not found in response: {result}")
            return snapshot_id
        except requests.exceptions.JSONDecodeError as e:
            raise Exception(f"Failed to parse trigger response as JSON. Response: {response.text[:200]}... Error: {str(e)}")

    def wait_for_snapshot(self, snapshot_id, data_type="profile", session_id=None):
        """스냅샷 수집 완료 대기 및 데이터 위치 확인"""
        url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"format": "json"}

        # 데이터 타입별 최소 대기 시간 설정
        if data_type in ["posts", "reels"]:
            min_wait_time = 120  # 게시물/릴스는 최소 2분
            max_wait_time = 1800 # 최대 30분 (무제한에 가깝게)
            check_interval = 30   # 30초 간격
        else:
            min_wait_time = 30   # 프로필은 최소 30초
            max_wait_time = 600  # 최대 10분
            check_interval = 15  # 15초 간격
        
        wait_count = 0
        
        # 최소 대기 시간 확보
        print(f"📊 {data_type.upper()} 데이터 수집 중... 최소 {min_wait_time}초 대기")
        if session_id:
            from app.services.progress_service import progress_service
            progress_service.update_progress(session_id, f"{data_type}_collection", 10, f"{data_type.title()} 데이터 처리 시작")
        
        time.sleep(min_wait_time)
        wait_count += min_wait_time
        
        if session_id:
            from app.services.progress_service import progress_service
            progress_service.update_progress(session_id, f"{data_type}_collection", 30, f"{data_type.title()} 데이터 처리 중... ({wait_count}초 경과)")
        
        while wait_count < max_wait_time:
            try:
                response = requests.get(url, headers=headers, params=params)
                print(f"📡 {data_type.upper()} 상태 확인: {response.status_code} ({wait_count}초 경과)")

                if response.status_code == 202:
                    remaining_time = max_wait_time - wait_count
                    progress_percent = min(90, 30 + (wait_count - min_wait_time) * 60 / (max_wait_time - min_wait_time))
                    print(f"⏳ {data_type.title()} 처리 중... {check_interval}초 후 재확인 (남은 시간: {remaining_time}초)")
                    if session_id:
                        from app.services.progress_service import progress_service
                        progress_service.update_progress(session_id, f"{data_type}_collection", int(progress_percent), 
                                                       f"{data_type.title()} 데이터 처리 중... ({wait_count}초 경과)")
                    time.sleep(check_interval)
                    wait_count += check_interval
                    continue

                if response.status_code != 200:
                    print(f"⚠️ {data_type.title()} 예상치 못한 상태 코드: {response.status_code}")
                    time.sleep(check_interval)
                    wait_count += check_interval
                    continue

                result = response.json()
                print(f"🔍 {data_type.upper()} 응답 구조: {type(result)}")
                if isinstance(result, dict):
                    print(f"🔍 {data_type.upper()} 응답 키: {list(result.keys())}")
                    if "file_urls" in result:
                        print(f"🔍 file_urls 타입: {type(result['file_urls'])}, 내용: {result['file_urls']}")

                if isinstance(result, list):
                    print(f"✅ {data_type.title()} 데이터 직접 반환 완료")
                    if session_id:
                        from app.services.progress_service import progress_service
                        progress_service.update_progress(session_id, f"{data_type}_collection", 100, f"{data_type.title()} 데이터 수집 완료")
                    return {"type": "direct_data", "data": result}

                if result.get("status") == "done":
                    file_urls = result.get("file_urls", [])
                    if not file_urls:
                        raise Exception(f"{data_type.title()} 스냅샷 완료되었지만 파일 URL이 없음")
                    print(f"✅ {data_type.title()} 스냅샷 완료. {len(file_urls)}개 파일 사용 가능")
                    if session_id:
                        from app.services.progress_service import progress_service
                        progress_service.update_progress(session_id, f"{data_type}_collection", 100, f"{data_type.title()} 데이터 수집 완료")
                    return {"type": "file_urls", "urls": file_urls}

                remaining_time = max_wait_time - wait_count
                progress_percent = min(90, 30 + (wait_count - min_wait_time) * 60 / (max_wait_time - min_wait_time))
                print(f"⏳ {data_type.title()} 처리 중... {check_interval}초 후 재확인 (남은 시간: {remaining_time}초)")
                if session_id:
                    from app.services.progress_service import progress_service
                    progress_service.update_progress(session_id, f"{data_type}_collection", int(progress_percent), 
                                                   f"{data_type.title()} 데이터 처리 중... ({wait_count}초 경과)")
                time.sleep(check_interval)
                wait_count += check_interval
                
            except Exception as e:
                print(f"❌ {data_type.title()} 상태 확인 오류: {e}")
                time.sleep(check_interval)
                wait_count += check_interval
        
        raise Exception(f"{data_type.title()} 스냅샷 타임아웃: {max_wait_time}초 후")

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
            
            config_path = Path(__file__).parent / "brightdata.json"
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
            
            config_path = Path(__file__).parent / "brightdata.json"
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
