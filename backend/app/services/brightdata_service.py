import os
import json
import aiohttp
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .progress_service import progress_service

# instagram_api.py 임포트 (백엔드 루트 디렉토리에 복사됨)
backend_root = str(Path(__file__).parent.parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
from instagram_api import Instagram

logger = logging.getLogger(__name__)

KST_OFFSET = timedelta(hours=9)


def now_kst() -> datetime:
    return datetime.utcnow() + KST_OFFSET

class BrightDataService:
    def __init__(self):
        self.api_key = os.getenv("BRIGHTDATA_API_KEY")
        if not self.api_key:
            raise Exception("BRIGHTDATA_API_KEY가 환경 변수에 설정되지 않았습니다")
        
        # 실제 Instagram API 클래스 사용
        self.instagram_api = Instagram()
        
        logger.info("BrightData Service initialized with real Instagram API")
        
    async def collect_instagram_data_batch(self, urls: List[str], options: Dict[str, bool] = None, session_id: str = None) -> List[Dict[str, Any]]:
        """배치로 인스타그램 데이터를 수집합니다."""
        logger.info(f"🚀 BrightData 배치 수집 시작: {len(urls)}개 URL")
        
        # session_id를 인스턴스 변수로 저장 (하위 메서드에서 사용)
        self._current_session_id = session_id
        
        results = []
        for i, url in enumerate(urls):
            try:
                logger.info(f"📍 [{i+1}/{len(urls)}] URL 수집 시작: {url}")
                
                username = self._extract_username_from_url(url)
                logger.info(f"🎯 추출된 사용자명: {username}")
                
                if username == "unknown_user":
                    logger.warning(f"⚠️ 사용자명 추출 실패: {url}")
                    results.append(self._create_empty_result(url))
                    continue
                
                # 실제 BrightData API 스냅샷 방식 사용
                try:
                    # URL이 게시물/릴스 URL인지 프로필 URL인지 판단
                    if "/p/" in url or "/reel/" in url:
                        # 게시물 또는 릴스 URL
                        config = {"include_errors": True}
                        if "/reel/" in url:
                            data = await self.instagram_api.get_reel_data(url, config)
                        else:
                            data = await self.instagram_api.get_post_data(url, config)
                        
                        if data and len(data) > 0:
                            # 첫 번째 데이터 항목을 프로필 정보로 사용
                            first_item = data[0] if isinstance(data, list) else data
                            result = {
                                "profile": {
                                    "username": first_item.get("user_posted", username),
                                    "full_name": first_item.get("user_posted", username),
                                    "followers": 0,
                                    "following": 0,
                                    "bio": "",
                                    "profile_pic_url": first_item.get("profile_url", ""),
                                    "account": "personal",
                                    "posts_count": 1
                                },
                                "posts": data if "/p/" in url else [],
                                "reels": data if "/reel/" in url else []
                            }
                        else:
                            result = self._create_empty_result(url)
                    else:
                        # 프로필 URL - 실제 프로필 수집 구현
                        logger.info(f"프로필 URL 수집 시작: {url}")
                        
                        # 실제 BrightData API 사용으로 프로필 수집  
                        # session_id가 있으면 전달
                        if hasattr(self, '_current_session_id'):
                            result = await self._collect_profile_with_brightdata(url, username, options, self._current_session_id)
                        else:
                            result = await self._collect_profile_with_brightdata(url, username, options)
                    
                    results.append(result)
                    logger.info(f"✅ [{i+1}/{len(urls)}] URL 수집 완료")
                    
                except Exception as api_error:
                    logger.error(f"🔥 BrightData API 호출 실패 {url}: {str(api_error)}")
                    # API 실패 시 에러 정보와 함께 결과 반환
                    error_result = {
                        "profile": None,
                        "posts": [],
                        "reels": [],
                        "error": f"데이터 수집 실패: {str(api_error)}",
                        "status": "api_error",
                        "url": url
                    }
                    results.append(error_result)
                
            except Exception as e:
                logger.error(f"❌ [{i+1}/{len(urls)}] URL 수집 실패 {url}: {str(e)}")
                error_result = {
                    "profile": None,
                    "posts": [],
                    "reels": [],
                    "error": f"처리 중 오류 발생: {str(e)}",
                    "status": "processing_error",
                    "url": url
                }
                results.append(error_result)
        
        logger.info(f"🎉 배치 수집 완료: {len(results)}개 결과")
        return results
    
    async def _collect_single_data_type(self, url: str, username: str, data_type: str, max_retries: int = 2) -> Dict[str, Any]:
        """단일 데이터 타입(profile 또는 reels)을 개별적으로 수집합니다. 재시도 로직 포함."""
        logger.info(f"🌐 BrightData API {data_type} 수집: {username} ({url})")
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"🔄 {data_type} 수집 재시도 {attempt}/{max_retries}: {username}")
                    # 재시도 시 잠시 대기
                    await asyncio.sleep(5)
                
                # brightdata.json에서 설정 로드
                import json
                from pathlib import Path
                
                config_path = Path(__file__).parent.parent.parent / "brightdata.json"
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        brightdata_config = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logger.error(f"❌ 설정 파일 로드 실패: {str(e)}")
                    if attempt == max_retries:
                        return {}
                    continue
                
                instagram_config = brightdata_config.get("instagram", {})
                
                if data_type == "profile":
                    config = instagram_config.get("profile", {})
                    input_data = [{"url": url}]
                elif data_type == "reels":
                    config = instagram_config.get("reel", {})
                    input_data = [{
                        "url": url,
                        "num_of_posts": 24,
                        "start_date": "",
                        "end_date": now_kst().strftime("%m-%d-%Y")
                    }]
                else:
                    logger.error(f"지원하지 않는 데이터 타입: {data_type}")
                    return {}
                
                dataset_id = config.get("dataset_id")
                params = config.get("params", {})
                
                if not dataset_id:
                    logger.error(f"{data_type} 데이터셋 ID가 설정되지 않음")
                    return {}
                
                # 스냅샷 요청 (재시도 시 더 강력한 오류 처리)
                try:
                    snapshot_id = self.instagram_api.trigger_snapshot_request(
                        dataset_id=dataset_id,
                        params=params,
                        data=input_data
                    )
                except Exception as snapshot_error:
                    logger.error(f"❌ 스냅샷 요청 실패 ({attempt+1}/{max_retries+1}): {str(snapshot_error)}")
                    if attempt == max_retries:
                        return {}
                    continue
                
                if not snapshot_id:
                    logger.error(f"❌ {data_type} 스냅샷 ID를 받지 못함 ({attempt+1}/{max_retries+1})")
                    if attempt == max_retries:
                        return {}
                    continue
                    
                logger.info(f"✅ {data_type} 스냅샷 ID: {snapshot_id}")
                
                # 스냅샷 완료 대기 (타임아웃 처리)
                try:
                    raw_data = self.instagram_api.wait_for_snapshot(snapshot_id, data_type)
                except Exception as wait_error:
                    logger.error(f"❌ 스냅샷 대기 실패 ({attempt+1}/{max_retries+1}): {str(wait_error)}")
                    if attempt == max_retries:
                        return {}
                    continue
                
                if not raw_data:
                    logger.error(f"❌ {data_type} 스냅샷 데이터가 비어있음 ({attempt+1}/{max_retries+1})")
                    if attempt == max_retries:
                        # 마지막 재시도에서도 실패하면 기본 데이터 반환
                        if data_type == "profile":
                            profile_data = self._create_default_profile(username)
                            return {"profile": profile_data}
                        return {}
                    continue
                
                # 원시 데이터 상태 로깅
                logger.info(f"🔍 {data_type} 원시 데이터 타입: {type(raw_data)}")
                
                # raw_data가 리스트인지 확인
                if isinstance(raw_data, list):
                    logger.info(f"🔍 {data_type} 원시 데이터 분석: 총 {len(raw_data)}개 항목")
                    # 처음 3개만 로깅 (안전하게)
                    for i in range(min(3, len(raw_data))):
                        item = raw_data[i]
                        logger.info(f"  [{i}] 타입: {type(item)}, 내용: {str(item)[:200]}")
                    
                    # 유효한 딕셔너리 데이터가 있는지 확인
                    valid_items = [item for item in raw_data if isinstance(item, dict)]
                    logger.info(f"📊 유효한 딕셔너리 데이터: {len(valid_items)}/{len(raw_data)}개")
                else:
                    logger.info(f"🔍 {data_type} 원시 데이터가 리스트가 아님: {str(raw_data)[:200]}")
                    # raw_data가 딕셔너리인 경우 리스트로 변환
                    if isinstance(raw_data, dict):
                        raw_data = [raw_data]
                        logger.info(f"🔄 딕셔너리를 리스트로 변환: {len(raw_data)}개 항목")
                    else:
                        logger.error(f"❌ 예상하지 못한 데이터 타입: {type(raw_data)}")
                        if attempt == max_retries:
                            return {}
                        continue
                
                # 데이터 파싱
                if data_type == "profile":
                    profile_data = None
                    for item in raw_data:
                        # 타입 검증 추가
                        if not isinstance(item, dict):
                            logger.warning(f"⚠️ 프로필 데이터 타입 스킵: {type(item)} - {str(item)[:100]}")
                            continue
                        profile_data = self._extract_profile_from_item(item, username)
                        if profile_data:
                            break
                    
                    # 프로필 데이터가 없으면 기본 프로필 생성
                    if not profile_data:
                        logger.warning(f"⚠️ {username} 프로필 데이터 추출 실패 - 기본 프로필 생성")
                        profile_data = self._create_default_profile(username)
                    
                    logger.info(f"✅ {data_type} 수집 성공: {username}")
                    return {"profile": profile_data}
                
                elif data_type == "reels":
                    reels_data = []
                    processed_items = 0
                    
                    for item in raw_data:
                        # 타입 검증 추가
                        if not isinstance(item, dict):
                            logger.warning(f"⚠️ 릴스 데이터 타입 스킵: {type(item)} - {str(item)[:100]}")
                            continue
                        
                        processed_items += 1
                        try:
                            if self._is_reel_item(item):
                                reel = self._extract_reel_from_item(item, username)
                                if reel:
                                    reels_data.append(reel)
                        except Exception as item_error:
                            logger.warning(f"⚠️ 릴스 아이템 처리 오류: {str(item_error)}")
                            continue
                    
                    logger.info(f"📊 {data_type} 처리 완료: 처리된 아이템 {processed_items}개, 릴스 {len(reels_data)}개")
                    
                    # 절대로 테스트 데이터를 생성하지 않음 (명시적 금지)
                    if not reels_data:
                        logger.warning(f"⚠️ {username} 실제 릴스 데이터가 없음 - 테스트 데이터 생성하지 않음")
                        reels_data = []
                    
                    logger.info(f"✅ {data_type} 수집 성공: {username} - {len(reels_data)}개 릴스")
                    return {"reels": reels_data}
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ {data_type} 수집 타임아웃 ({attempt+1}/{max_retries+1}): {username}")
                if attempt == max_retries:
                    # 타임아웃이지만 기본 데이터라도 반환
                    if data_type == "profile":
                        profile_data = self._create_default_profile(username)
                        return {"profile": profile_data}
                    return {}
                continue
                
            except Exception as e:
                import traceback
                logger.error(f"❌ {data_type} 수집 실패 ({attempt+1}/{max_retries+1}): {str(e)}")
                logger.error(f"❌ 스택 트레이스: {traceback.format_exc()}")
                if attempt == max_retries:
                    # 모든 재시도 실패 시 기본 데이터 반환
                    if data_type == "profile":
                        profile_data = self._create_default_profile(username)
                        return {"profile": profile_data}
                    return {}
                continue
        
        # 이 지점에 도달하면 모든 재시도 실패
        logger.error(f"💥 {data_type} 수집 완전 실패: {username}")
        if data_type == "profile":
            profile_data = self._create_default_profile(username)
            return {"profile": profile_data}
        return {}

    async def _collect_profile_with_brightdata(self, url: str, username: str, options: Dict[str, bool] = None, session_id: str = None) -> Dict[str, Any]:
        """실제 BrightData API를 사용하여 프로필, 게시물, 릴스를 모두 수집합니다."""
        logger.info(f"🌐 BrightData API 프로필 + 게시물 + 릴스 수집: {username} ({url})")
        
        try:
            # brightdata.json에서 설정 로드
            import json
            from pathlib import Path
            
            config_path = Path(__file__).parent.parent.parent / "brightdata.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                brightdata_config = json.load(f)
            
            instagram_config = brightdata_config.get("instagram", {})
            
            # 수집할 데이터 유형들
            collection_tasks = []
            
            # 1. 프로필 데이터 수집
            if options is None or options.get("collectProfile", True):
                profile_config = instagram_config.get("profile", {})
                if profile_config.get("dataset_id"):
                    profile_data = [{"url": url}]
                    collection_tasks.append(("profile", profile_config, profile_data))
            
            # 게시물 수집 비활성화됨
            
            # 3. 릴스 데이터 수집 (프로필 URL을 사용하여 최신 릴스들 수집)  
            if options is None or options.get("collectReels", True):
                reel_config = instagram_config.get("reel", {})
                if reel_config.get("dataset_id"):
                    # BrightData API 요구 형식에 맞춰 릴스 수집 파라미터 구성
                    reels_data = [{
                        "url": url,
                        "num_of_posts": 24,
                        "start_date": "",
                        "end_date": now_kst().strftime("%m-%d-%Y")
                    }]
                    collection_tasks.append(("reels", reel_config, reels_data))
            
            if not collection_tasks:
                logger.warning("수집할 데이터 유형이 설정되지 않음")
                return self._create_empty_result_with_error(url, "수집 설정이 올바르지 않음")
            
            # 각 데이터 유형별로 수집 실행
            collected_data = {"profile": None, "posts": [], "reels": []}
            
            for data_type, config, input_params in collection_tasks:
                try:
                    logger.info(f"📡 {data_type.upper()} 데이터 수집 시작...")
                    
                    # 세부 진행률 초기화
                    current_session_id = getattr(self, '_current_session_id', None)
                    if current_session_id:
                        await progress_service.send_detail_progress(
                            current_session_id, 
                            data_type, 
                            "running", 
                            0, 
                            1, 
                            f"{data_type.title()} 데이터 수집 요청 시작"
                        )
                    
                    dataset_id = config.get("dataset_id")
                    params = config.get("params", {})
                    
                    # 스냅샷 요청
                    snapshot_id = self.instagram_api.trigger_snapshot_request(
                        dataset_id=dataset_id,
                        params=params,
                        data=input_params
                    )
                    
                    if not snapshot_id:
                        logger.error(f"{data_type} 스냅샷 ID를 받지 못함")
                        continue
                        
                    logger.info(f"✅ {data_type} 스냅샷 ID: {snapshot_id}")
                    
                    # 스냅샷 완료 대기 (데이터 타입과 세션 ID 전달)
                    current_session_id = getattr(self, '_current_session_id', None)
                    snapshot_result = self.instagram_api.wait_for_snapshot(snapshot_id, data_type, current_session_id)
                    
                    if not snapshot_result:
                        logger.error(f"{data_type} 스냅샷 데이터를 받지 못함")
                        continue
                    
                    # 데이터 다운로드
                    if snapshot_result["type"] == "direct_data":
                        data = snapshot_result["data"]
                        logger.info(f"📊 {data_type} 직접 데이터 수신: {len(data)}개 항목")
                    elif snapshot_result["type"] == "file_urls":
                        data = self.instagram_api.download_snapshot_data(snapshot_result["urls"])
                        logger.info(f"📥 {data_type} 파일 다운로드 완료: {len(data)}개 항목")
                    else:
                        logger.error(f"{data_type} 알 수 없는 스냅샷 결과 타입")
                        continue
                    
                    if data and len(data) > 0:
                        # 데이터 유형별 처리
                        if data_type == "profile":
                            profile_data = self._extract_profile_from_brightdata(data, username)
                            if profile_data:
                                collected_data["profile"] = profile_data
                                logger.info(f"✅ 프로필 데이터 추출 완료")
                                # 세부 진행상황 업데이트
                                if current_session_id:
                                    await progress_service.send_detail_progress(
                                        current_session_id, "profile", "completed", 1, 1, "프로필 데이터 수집 완료"
                                    )
                        
                        elif data_type == "posts":
                            posts_data = self._extract_posts_from_brightdata(data, username)
                            collected_data["posts"].extend(posts_data)
                            logger.info(f"✅ 게시물 데이터 추출 완료: {len(posts_data)}개")
                            # 세부 진행상황 업데이트
                            if current_session_id:
                                await progress_service.send_detail_progress(
                                    current_session_id, "posts", "completed", 1, 1, f"게시물 {len(posts_data)}개 수집 완료"
                                )
                        
                        elif data_type == "reels":
                            reels_data = self._extract_reels_from_brightdata(data, username)
                            collected_data["reels"].extend(reels_data)
                            logger.info(f"✅ 릴스 데이터 추출 완료: {len(reels_data)}개")
                            # 세부 진행상황 업데이트
                            if current_session_id:
                                await progress_service.send_detail_progress(
                                    current_session_id, "reels", "completed", 1, 1, f"릴스 {len(reels_data)}개 수집 완료"
                                )
                    else:
                        logger.warning(f"⚠️ {data_type} 데이터가 비어있음")
                        # 세부 진행상황 업데이트 (실패)
                        if current_session_id:
                            await progress_service.send_detail_progress(
                                current_session_id, data_type, "completed", 1, 1, f"{data_type.title()} 데이터 없음"
                            )
                    
                except Exception as e:
                    logger.error(f"🔥 {data_type} 수집 실패: {str(e)}")
                    # 세부 진행상황 업데이트 (실패)
                    if current_session_id:
                        await progress_service.send_detail_progress(
                            current_session_id, data_type, "failed", 0, 1, f"{data_type.title()} 수집 실패: {str(e)}"
                        )
                    continue
            
            # 기본 프로필이 없으면 생성
            if not collected_data["profile"]:
                collected_data["profile"] = self._create_default_profile(username)
            
            # 절대로 테스트 데이터를 생성하지 않음 (명시적 금지)
            if len(collected_data["reels"]) == 0:
                logger.info(f"⚠️ 실제 릴스 데이터가 없음 - 테스트 데이터 생성하지 않음")
                collected_data["reels"] = []
            
            logger.info(f"🎉 통합 수집 완료: 프로필={1 if collected_data['profile'] else 0}, 릴스={len(collected_data['reels'])}")
            return collected_data
            
        except Exception as e:
            logger.error(f"🔥 BrightData API 통합 수집 실패 {username}: {str(e)}")
            return self._create_empty_result_with_error(url, f"BrightData API 오류: {str(e)}")
    
    def _process_brightdata_response(self, raw_data: List[Dict], username: str, options: Dict[str, bool] = None) -> Dict[str, Any]:
        """BrightData 원시 데이터를 처리하여 표준 형식으로 변환합니다."""
        logger.info(f"🔄 BrightData 데이터 처리 시작: {len(raw_data)}개 항목")
        
        if not options:
            options = {"collectProfile": True, "collectPosts": True, "collectReels": True}
        
        profile_data = None
        posts_data = []
        reels_data = []
        
        # BrightData Instagram 데이터 파싱
        for idx, item in enumerate(raw_data):
            try:
                # 데이터 타입 검증 - 문자열인 경우 스킵
                if not isinstance(item, dict):
                    logger.warning(f"⚠️ [{idx+1}/{len(raw_data)}] 잘못된 데이터 타입 스킵: {type(item)} - {str(item)[:100]}")
                    continue
                
                logger.info(f"🔍 [{idx+1}/{len(raw_data)}] 아이템 처리: {list(item.keys())}")
                
                # 프로필 정보 추출 (보통 첫 번째 아이템에 있음)
                if not profile_data and options.get("collectProfile", True):
                    profile_data = self._extract_profile_from_item(item, username)
                
                # 게시물/릴스 데이터 추출
                if self._is_post_item(item):
                    if options.get("collectPosts", True):
                        post = self._extract_post_from_item(item, username)
                        if post:
                            posts_data.append(post)
                elif self._is_reel_item(item):
                    if options.get("collectReels", True):
                        reel = self._extract_reel_from_item(item, username)
                        if reel:
                            reels_data.append(reel)
                
            except Exception as e:
                logger.warning(f"⚠️ 아이템 처리 오류 [{idx}]: {str(e)}")
                continue
        
        # 기본 프로필 생성 (데이터가 없으면)
        if not profile_data and options.get("collectProfile", True):
            profile_data = self._create_default_profile(username)
        
        result = {
            "profile": profile_data,
            "posts": posts_data,
            "reels": reels_data
        }
        
        logger.info(f"✅ BrightData 데이터 처리 완료: 프로필={1 if profile_data else 0}, 게시물={len(posts_data)}, 릴스={len(reels_data)}")
        return result
    
    def _extract_profile_from_item(self, item: Dict, username: str) -> Optional[Dict]:
        """아이템에서 프로필 정보를 추출합니다."""
        try:
            # 데이터 타입 검증
            if not isinstance(item, dict):
                logger.warning(f"⚠️ 프로필 추출 스킵: 딕셔너리가 아닌 데이터 타입 {type(item)}")
                return None
                
                
            # BrightData Instagram 데이터 구조에 맞춰 프로필 정보 추출
            profile = {
                "username": item.get("user_posted") or item.get("username") or username,
                "full_name": item.get("full_name") or item.get("user_posted") or username,
                "followers": self._safe_int(item.get("followers_count") or item.get("followers")),
                "following": self._safe_int(item.get("following_count") or item.get("following")),
                "bio": item.get("bio") or item.get("biography", ""),
                "profile_pic_url": item.get("profile_pic_url") or item.get("avatar_url") or "",
                "account": item.get("account_type", "personal"),
                "posts_count": self._safe_int(item.get("posts_count") or item.get("media_count")),
                "avg_engagement": self._safe_float(item.get("avg_engagement", 0)),
                "category_name": item.get("category") or "",
                "profile_name": item.get("profile_name") or username,
                "email_address": item.get("email"),
                "is_business_account": item.get("is_business", False),
                "is_professional_account": item.get("is_professional", False),
                "is_verified": item.get("is_verified", False)
            }
            
            # 유효한 데이터가 있는지 확인 (더 관대한 검증)
            # username이 있거나, 최소한 full_name이 있으면 유효한 프로필로 간주
            if profile["username"] or profile["full_name"]:
                # username이 없으면 URL에서 추출한 username 사용
                if not profile["username"]:
                    profile["username"] = username
                    
                logger.info(f"👤 프로필 추출 성공: {profile['username']} (팔로워: {profile['followers']})")
                return profile
            else:
                logger.info(f"⚠️ 프로필 데이터 불완전: {profile}")
                return None
                
        except Exception as e:
            logger.error(f"프로필 추출 오류: {str(e)}")
            return None
    
    def _is_post_item(self, item: Dict) -> bool:
        """아이템이 일반 게시물인지 확인합니다."""
        if not isinstance(item, dict):
            return False
        media_type = item.get("media_type", "").lower()
        content_type = item.get("content_type", "").lower()
        return media_type in ["image", "photo", "carousel"] or content_type == "post" or "post" in str(item.get("url", ""))
    
    def _is_reel_item(self, item: Dict) -> bool:
        """아이템이 릴스인지 확인합니다."""
        if not isinstance(item, dict):
            return False
        media_type = item.get("media_type", "").lower()
        content_type = item.get("content_type", "").lower()
        return media_type == "video" or content_type == "reel" or "reel" in str(item.get("url", ""))
    
    def _extract_post_from_item(self, item: Dict, username: str) -> Optional[Dict]:
        """아이템에서 게시물 정보를 추출합니다."""
        try:
            # 데이터 타입 검증
            if not isinstance(item, dict):
                logger.warning(f"⚠️ 게시물 추출 스킵: 딕셔너리가 아닌 데이터 타입 {type(item)}")
                return None
            # 더 포괄적인 필드 매핑을 위한 헬퍼 함수
            def get_field_value(item, *field_names):
                for field in field_names:
                    if field in item and item[field]:
                        return item[field]
                return None
            
            post_id = get_field_value(item, "id", "shortcode", "post_id", "pk") or f"{username}_post_{hash(str(item))}"
            caption = get_field_value(item, "caption", "text", "description", "edge_media_to_caption")
            
            # edge_media_to_caption 구조 처리 (Instagram Graph API 형식)
            if isinstance(caption, dict) and "edges" in caption:
                if caption["edges"] and len(caption["edges"]) > 0:
                    caption = caption["edges"][0].get("node", {}).get("text", "")
                else:
                    caption = ""
            
            post = {
                "post_id": post_id,
                "id": post_id,  # API 호환성을 위해 추가
                "media_type": get_field_value(item, "media_type", "__typename") or "IMAGE",
                "media_urls": self._extract_media_urls(item),
                "caption": caption or "",
                "timestamp": get_field_value(item, "timestamp", "taken_at", "taken_at_timestamp", "date_posted"),
                "user_posted": get_field_value(item, "user_posted", "username", "owner") or username,
                "profile_url": get_field_value(item, "profile_url") or f"https://instagram.com/{username}",
                "date_posted": get_field_value(item, "date_posted", "date", "taken_at"),
                "num_comments": self._safe_int(get_field_value(item, "comment_count", "comments_count", "num_comments", "edge_media_to_comment")),
                "likes": self._safe_int(get_field_value(item, "like_count", "likes_count", "likes", "edge_liked_by")),
                "photos": self._extract_media_urls(item),
                "content_type": "post",
                "description": caption or "",
                "hashtags": self._extract_hashtags(caption or "")
            }
            
            # edge_media_to_comment, edge_liked_by 구조 처리 (Instagram Graph API)
            if isinstance(post["num_comments"], dict) and "count" in post["num_comments"]:
                post["num_comments"] = post["num_comments"]["count"]
            if isinstance(post["likes"], dict) and "count" in post["likes"]:
                post["likes"] = post["likes"]["count"]
            
            logger.debug(f"게시물 추출: {post_id} - {post.get('media_type', 'UNKNOWN')}")
            return post
                
        except Exception as e:
            logger.error(f"게시물 추출 오류: {str(e)} - Item keys: {list(item.keys()) if item else 'None'}")
            return None
    
    def _extract_reel_from_item(self, item: Dict, username: str) -> Optional[Dict]:
        """아이템에서 릴스 정보를 추출합니다."""
        try:
            # 데이터 타입 검증
            if not isinstance(item, dict):
                logger.warning(f"⚠️ 릴스 추출 스킵: 딕셔너리가 아닌 데이터 타입 {type(item)}")
                return None
                
            # 더 포괄적인 필드 매핑을 위한 헬퍼 함수
            def get_field_value(item, *field_names):
                for field in field_names:
                    if field in item and item[field]:
                        return item[field]
                return None
            
            reel_id = get_field_value(item, "id", "shortcode", "reel_id", "pk") or f"{username}_reel_{hash(str(item))}"
            caption = get_field_value(item, "caption", "text", "description", "edge_media_to_caption")
            
            # edge_media_to_caption 구조 처리 (Instagram Graph API 형식)
            if isinstance(caption, dict) and "edges" in caption:
                if caption["edges"] and len(caption["edges"]) > 0:
                    caption = caption["edges"][0].get("node", {}).get("text", "")
                else:
                    caption = ""
            
            thumbnail_url = get_field_value(
                item,
                "thumbnail_url",
                "thumbnail",
                "thumbnailUrl",
                "display_url",
                "cover",
                "cover_image"
            )

            media_urls = self._extract_media_urls(item)
            if thumbnail_url:
                media_urls = [thumbnail_url]

            reel = {
                "reel_id": reel_id,
                "id": reel_id,  # API 호환성을 위해 추가
                "media_type": "VIDEO",
                "media_urls": media_urls,
                "caption": caption or "",
                "timestamp": get_field_value(item, "timestamp", "taken_at", "taken_at_timestamp", "date_posted"),
                "user_posted": get_field_value(item, "user_posted", "username", "owner") or username,
                "profile_url": get_field_value(item, "profile_url") or f"https://instagram.com/{username}",
                "date_posted": get_field_value(item, "date_posted", "date", "taken_at"),
                "num_comments": self._safe_int(get_field_value(item, "comment_count", "comments_count", "num_comments", "edge_media_to_comment")),
                "likes": self._safe_int(get_field_value(item, "like_count", "likes_count", "likes", "edge_liked_by")),
                "photos": [],
                "content_type": "reel",
                "description": caption or "",
                "hashtags": self._extract_hashtags(caption or ""),
                "url": get_field_value(item, "url", "permalink") or f"https://instagram.com/reel/{item.get('shortcode', reel_id)}",
                "views": self._safe_int(get_field_value(item, "view_count", "views_count", "views", "play_count", "video_view_count")),
                "video_play_count": self._safe_int(get_field_value(item, "play_count", "video_play_count", "views", "view_count")),
                "thumbnail_url": thumbnail_url or (media_urls[0] if media_urls else None)
            }
            
            # edge_media_to_comment, edge_liked_by 구조 처리 (Instagram Graph API)
            if isinstance(reel["num_comments"], dict) and "count" in reel["num_comments"]:
                reel["num_comments"] = reel["num_comments"]["count"]
            if isinstance(reel["likes"], dict) and "count" in reel["likes"]:
                reel["likes"] = reel["likes"]["count"]
            
            logger.debug(f"릴스 추출: {reel_id} - Views: {reel.get('views', 0)}")
            return reel
                
        except Exception as e:
            logger.error(f"릴스 추출 오류: {str(e)} - Item keys: {list(item.keys()) if item else 'None'}")
            return None
    
    def _create_default_profile(self, username: str) -> Dict:
        """기본 프로필을 생성합니다."""
        return {
            "username": username,
            "full_name": f"{username.title()}",
            "followers": 0,
            "following": 0,
            "bio": "",
            "profile_pic_url": "",
            "account": "personal",
            "posts_count": 0,
            "avg_engagement": 0.0,
            "category_name": "",
            "profile_name": username,
            "email_address": None,
            "is_business_account": False,
            "is_professional_account": False,
            "is_verified": False
        }
    
    def _create_empty_result_with_error(self, url: str, error_msg: str) -> Dict[str, Any]:
        """에러 정보와 함께 빈 결과를 생성합니다."""
        username = self._extract_username_from_url(url)
        return {
            "profile": None,
            "posts": [],
            "reels": [],
            "error": error_msg,
            "status": "collection_failed",
            "url": url
        }
    
    async def _collect_single_instagram_profile(self, session: aiohttp.ClientSession, url: str, options: Dict[str, bool] = None) -> Dict[str, Any]:
        """단일 Instagram 프로필에서 데이터를 수집합니다."""
        username = self._extract_username_from_url(url)
        logger.info(f"🎯 Instagram 프로필 수집 시작: {username}")
        
        # 1단계: 데이터셋 수집 작업 트리거
        trigger_id = await self._trigger_dataset_collection(session, url, options)
        if not trigger_id:
            logger.error(f"데이터셋 트리거 실패: {url}")
            return self._create_empty_result(url)
        
        logger.info(f"📡 데이터셋 트리거 성공: {trigger_id}")
        
        # 2단계: 스냅샷 완료까지 대기 (폴링)
        # 릴스 수집은 더 짧은 대기 시간 사용
        max_wait = 5 if 'reel' in str(options) else 10
        snapshot_data = await self._wait_for_snapshot_completion(session, trigger_id, max_wait)
        if not snapshot_data:
            logger.error(f"스냅샷 완료 대기 실패: {trigger_id}")
            return self._create_empty_result(url)
        
        logger.info(f"📊 스냅샷 완료: {len(snapshot_data)} 개 레코드")
        
        # 3단계: 데이터 파싱 및 구조화
        processed_data = self._process_instagram_snapshot(snapshot_data, username)
        
        return processed_data
    
    async def _trigger_dataset_collection(self, session: aiohttp.ClientSession, url: str, options: Dict[str, bool] = None) -> Optional[str]:
        """BrightData Dataset 수집 작업을 트리거합니다."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # brightdata.json에서 프로필 설정 로드
        import json
        from pathlib import Path
        
        config_path = Path(__file__).parent.parent.parent / "brightdata.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            brightdata_config = json.load(f)
        
        # 프로필 설정에서 params 가져오기
        profile_config = brightdata_config.get("instagram", {}).get("profile", {})
        dataset_id = profile_config.get("dataset_id")
        if not dataset_id:
            raise ValueError("profile dataset_id가 설정되지 않았습니다.")
        
        # Instagram 프로필 데이터 수집을 위한 입력 파라미터
        payload = {
            "dataset_id": dataset_id,
            "include_errors": True,
            "format": "json",
            "notify": [],
            "input": [
                {
                    "url": url,
                    "limit_per_input": 50  # 프로필당 최대 50개 게시물
                }
            ]
        }
        
        # BrightData API URLs
        trigger_url = "https://api.brightdata.com/datasets/v3/trigger"
        
        logger.info(f"📡 Dataset 트리거 요청: {trigger_url}")
        logger.info(f"📦 요청 페이로드: {payload}")
        
        try:
            async with session.post(trigger_url, headers=headers, json=payload, timeout=30) as response:
                response_text = await response.text()
                logger.info(f"📨 트리거 응답 상태: {response.status}")
                logger.info(f"📨 트리거 응답: {response_text}")
                
                if response.status == 200:
                    data = await response.json()
                    trigger_id = data.get("snapshot_id")
                    if trigger_id:
                        logger.info(f"✅ 트리거 성공: {trigger_id}")
                        return trigger_id
                    else:
                        logger.error(f"트리거 응답에 snapshot_id가 없음: {data}")
                        return None
                else:
                    logger.error(f"트리거 실패: HTTP {response.status} - {response_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"트리거 요청 예외: {str(e)}")
            return None
    
    async def _wait_for_snapshot_completion(self, session: aiohttp.ClientSession, trigger_id: str, max_wait_minutes: int = 15) -> Optional[List[Dict]]:
        """스냅샷 완료까지 대기하고 데이터를 다운로드합니다."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        status_url = f"https://api.brightdata.com/datasets/v3/snapshot/{trigger_id}"
        
        wait_seconds = 0
        max_wait_seconds = max_wait_minutes * 60
        check_interval = 10  # 10초마다 상태 체크
        
        logger.info(f"⏳ 스냅샷 완료 대기 중... (최대 {max_wait_minutes}분)")
        
        while wait_seconds < max_wait_seconds:
            try:
                async with session.get(status_url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        status = status_data.get("status")
                        
                        remaining_minutes = (max_wait_seconds - wait_seconds) // 60
                        logger.info(f"📊 스냅샷 상태: {status} (약 {remaining_minutes}분 남음)")
                        
                        if status == "ready":
                            # 스냅샷 완료, 데이터 다운로드
                            return await self._download_snapshot_data(session, trigger_id)
                        elif status == "failed" or status == "error":
                            logger.error(f"스냅샷 실패: {status}")
                            return None
                        # running, pending 등의 경우 계속 대기
                        
                    else:
                        logger.warning(f"상태 확인 실패: HTTP {response.status}")
                
                # 대기
                await asyncio.sleep(check_interval)
                wait_seconds += check_interval
                
            except Exception as e:
                logger.error(f"상태 확인 예외: {str(e)}")
                await asyncio.sleep(check_interval)
                wait_seconds += check_interval
        
        logger.error(f"스냅샷 대기 시간 초과: {max_wait_minutes}분")
        return None
    
    async def _download_snapshot_data(self, session: aiohttp.ClientSession, snapshot_id: str) -> Optional[List[Dict]]:
        """완료된 스냅샷 데이터를 다운로드합니다."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        download_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"
        
        logger.info(f"⬇️ 스냅샷 데이터 다운로드: {download_url}")
        
        try:
            async with session.get(download_url, headers=headers, timeout=60) as response:
                if response.status == 200:
                    # JSON Lines 형식으로 반환될 수 있음
                    response_text = await response.text()
                    
                    # JSON Lines 파싱
                    data_records = []
                    for line in response_text.strip().split('\n'):
                        if line.strip():
                            try:
                                record = json.loads(line)
                                data_records.append(record)
                            except json.JSONDecodeError:
                                continue
                    
                    logger.info(f"✅ 데이터 다운로드 완료: {len(data_records)}개 레코드")
                    return data_records
                else:
                    response_text = await response.text()
                    logger.error(f"데이터 다운로드 실패: HTTP {response.status} - {response_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"데이터 다운로드 예외: {str(e)}")
            return None
    
    async def _create_test_data(self, url: str, username: str, options: Dict[str, bool] = None) -> Dict[str, Any]:
        """테스트용 데이터를 생성합니다."""
        logger.info(f"🧪 테스트 데이터 생성: {username}")
        
        if not options:
            options = {"collectProfile": True, "collectPosts": True, "collectReels": True}
        
        result = {
            "profile": None,
            "posts": [],
            "reels": []
        }
        
        # 프로필 데이터 생성
        if options.get("collectProfile", True):
            result["profile"] = {
                "username": username,
                "full_name": f"{username.title()} Test User",
                "followers": 5000 + hash(username) % 10000,
                "following": 500 + hash(username) % 500,
                "bio": f"테스트 계정 {username}입니다. 맛집과 일상을 공유합니다.",
                "profile_pic_url": f"https://via.placeholder.com/150x150?text={username}",
                "account": "personal",
                "posts_count": 24,
                "avg_engagement": 3.5,
                "category_name": "Food & Lifestyle",
                "profile_name": username,
                "email_address": None,
                "is_business_account": False,
                "is_professional_account": False,
                "is_verified": False
            }
        
        # 게시물 데이터 생성
        if options.get("collectPosts", True):
            for i in range(6):  # 6개 테스트 게시물
                post = {
                    "post_id": f"{username}_post_{i+1}",
                    "media_type": "IMAGE",
                    "media_urls": [f"https://via.placeholder.com/400x400?text=Post{i+1}"],
                    "caption": f"테스트 게시물 {i+1}번입니다. #test #instagram #{username}",
                    "timestamp": now_kst().isoformat(),
                    "user_posted": username,
                    "profile_url": f"https://instagram.com/{username}",
                    "date_posted": now_kst().strftime("%Y-%m-%d"),
                    "num_comments": 10 + (i * 5),
                    "likes": 100 + (i * 20),
                    "photos": [f"https://via.placeholder.com/400x400?text=Post{i+1}"],
                    "content_type": "post",
                    "description": f"테스트 게시물 {i+1}번의 상세 설명입니다.",
                    "hashtags": ["#test", "#instagram", f"#{username}"]
                }
                result["posts"].append(post)
        
        # 릴스 데이터 생성
        if options.get("collectReels", True):
            for i in range(4):  # 4개 테스트 릴스
                reel = {
                    "reel_id": f"{username}_reel_{i+1}",
                    "media_type": "VIDEO", 
                    "media_urls": [f"https://via.placeholder.com/400x700?text=Reel{i+1}"],
                    "caption": f"테스트 릴스 {i+1}번입니다. #reel #video #{username}",
                    "timestamp": now_kst().isoformat(),
                    "user_posted": username,
                    "profile_url": f"https://instagram.com/{username}",
                    "date_posted": now_kst().strftime("%Y-%m-%d"),
                    "num_comments": 5 + (i * 3),
                    "likes": 200 + (i * 50),
                    "photos": [],
                    "content_type": "reel",
                    "description": f"테스트 릴스 {i+1}번의 상세 설명입니다.",
                    "hashtags": ["#reel", "#video", f"#{username}"],
                    "url": f"https://instagram.com/reel/{username}_reel_{i+1}",
                    "views": 1000 + (i * 200),
                    "video_play_count": 1000 + (i * 200)
                }
                result["reels"].append(reel)
        
        logger.info(f"✅ 테스트 데이터 생성 완료: 프로필=1, 게시물={len(result['posts'])}개, 릴스={len(result['reels'])}개")
        return result
    
    def _create_empty_result(self, url: str) -> Dict[str, Any]:
        """빈 결과 구조를 생성합니다."""
        username = self._extract_username_from_url(url)
        return {
            "profile": None,
            "posts": [],
            "reels": [],
            "error": "데이터 수집 실패 - 스냅샷 요청 또는 대기 중 오류 발생",
            "status": "collection_failed",
            "url": url
        }
    
    def _process_instagram_snapshot(self, snapshot_data: List[Dict], username: str) -> Dict[str, Any]:
        """BrightData Instagram 스냅샷 데이터를 처리합니다."""
        logger.info(f"🔄 Instagram 스냅샷 데이터 처리 시작: {username}, {len(snapshot_data)}개 레코드")
        
        profile_data = None
        posts_data = []
        reels_data = []
        
        for record in snapshot_data:
            try:
                # BrightData Instagram dataset 구조에 따라 파싱
                record_type = record.get("type", "post")
                
                if record_type == "profile" or ("profile" in record and record["profile"]):
                    # 프로필 데이터 처리
                    profile_info = record.get("profile", record)
                    profile_data = {
                        "username": username,
                        "full_name": profile_info.get("full_name") or profile_info.get("name", ""),
                        "followers": self._safe_int(profile_info.get("followers") or profile_info.get("follower_count", 0)),
                        "following": self._safe_int(profile_info.get("following") or profile_info.get("following_count", 0)),
                        "bio": profile_info.get("bio") or profile_info.get("biography", ""),
                        "profile_pic_url": profile_info.get("profile_pic_url") or profile_info.get("avatar", ""),
                        "account": profile_info.get("account_type", "personal"),
                        "posts_count": self._safe_int(profile_info.get("posts_count") or profile_info.get("media_count", 0)),
                        "avg_engagement": self._safe_float(profile_info.get("avg_engagement", 0)),
                        "category_name": profile_info.get("category", ""),
                        "profile_name": profile_info.get("profile_name", username),
                        "email_address": profile_info.get("email"),
                        "is_business_account": profile_info.get("is_business", False),
                        "is_professional_account": profile_info.get("is_professional", False),
                        "is_verified": profile_info.get("is_verified", False)
                    }
                    
                elif record_type == "reel" or record.get("media_type") == "VIDEO":
                    # 릴스 데이터 처리
                    reel_data = {
                        "reel_id": record.get("id") or record.get("shortcode", f"{username}_reel_{len(reels_data)+1}"),
                        "media_type": "VIDEO",
                        "media_urls": self._extract_media_urls(record),
                        "caption": record.get("caption") or record.get("text", ""),
                        "timestamp": self._parse_timestamp(record.get("taken_at") or record.get("timestamp")),
                        "user_posted": username,
                        "profile_url": f"https://instagram.com/{username}",
                        "date_posted": record.get("date", ""),
                        "num_comments": self._safe_int(record.get("comment_count") or record.get("comments", 0)),
                        "likes": self._safe_int(record.get("like_count") or record.get("likes", 0)),
                        "photos": [],
                        "content_type": "reel",
                        "description": record.get("caption") or record.get("text", ""),
                        "hashtags": self._extract_hashtags(record.get("caption", "")),
                        "url": record.get("url") or f"https://instagram.com/reel/{record.get('shortcode', '')}",
                        "views": self._safe_int(record.get("view_count") or record.get("play_count", 0)),
                        "video_play_count": self._safe_int(record.get("play_count") or record.get("view_count", 0))
                    }
                    reels_data.append(reel_data)
                    
                else:
                    # 일반 게시물 데이터 처리
                    post_data = {
                        "post_id": record.get("id") or record.get("shortcode", f"{username}_post_{len(posts_data)+1}"),
                        "media_type": record.get("media_type", "IMAGE"),
                        "media_urls": self._extract_media_urls(record),
                        "caption": record.get("caption") or record.get("text", ""),
                        "timestamp": self._parse_timestamp(record.get("taken_at") or record.get("timestamp")),
                        "user_posted": username,
                        "profile_url": f"https://instagram.com/{username}",
                        "date_posted": record.get("date", ""),
                        "num_comments": self._safe_int(record.get("comment_count") or record.get("comments", 0)),
                        "likes": self._safe_int(record.get("like_count") or record.get("likes", 0)),
                        "photos": self._extract_media_urls(record),
                        "content_type": "post",
                        "description": record.get("caption") or record.get("text", ""),
                        "hashtags": self._extract_hashtags(record.get("caption", ""))
                    }
                    posts_data.append(post_data)
                    
            except Exception as e:
                logger.warning(f"레코드 처리 실패: {str(e)} - {record}")
                continue
        
        # 기본 프로필이 없으면 생성
        if not profile_data:
            profile_data = {
                "username": username,
                "full_name": f"{username.title()}",
                "followers": 0,
                "following": 0,
                "bio": "",
                "profile_pic_url": "",
                "account": "personal",
                "posts_count": len(posts_data),
                "avg_engagement": 0.0,
                "category_name": "",
                "profile_name": username,
                "email_address": None,
                "is_business_account": False,
                "is_professional_account": False,
                "is_verified": False
            }
        
        result = {
            "profile": profile_data,
            "posts": posts_data,
            "reels": reels_data
        }
        
        logger.info(f"✅ 데이터 처리 완료: 프로필=1, 게시물={len(posts_data)}개, 릴스={len(reels_data)}개")
        return result
    
    def _extract_username_from_url(self, url: str) -> str:
        """Instagram URL에서 사용자명을 추출합니다."""
        import re
        
        # URL 정리 (trailing slash 제거, 쿼리 파라미터 제거)
        clean_url = url.strip().rstrip('/')
        if '?' in clean_url:
            clean_url = clean_url.split('?')[0]
        
        # 다양한 Instagram URL 패턴들
        patterns = [
            r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?',
            r'(?:https?://)?(?:www\.)?ig\.me/([a-zA-Z0-9_.]+)/?',
            r'(?:https?://)?(?:m\.)?instagram\.com/([a-zA-Z0-9_.]+)/?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_url)
            if match:
                username = match.group(1)
                # 유효하지 않은 경로들 제외
                if username not in ['p', 'reel', 'tv', 'stories', 'explore', 'accounts']:
                    return username
        
        return "unknown_user"
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """타임스탬프 문자열을 datetime 객체로 변환합니다."""
        if not timestamp_str:
            return None
            
        try:
            # Various timestamp formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
            
            # If all formats fail, try to parse as integer timestamp
            try:
                return datetime.fromtimestamp(int(timestamp_str))
            except (ValueError, OSError):
                pass
            
            logger.warning(f"타임스탬프 파싱 실패: {timestamp_str}")
            return None
            
        except Exception as e:
            logger.error(f"타임스탬프 파싱 오류: {str(e)}")
            return None
    
    def _safe_int(self, value) -> int:
        """안전하게 정수로 변환"""
        if value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    
    def _safe_float(self, value) -> float:
        """안전하게 실수로 변환"""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _extract_media_urls(self, media_item: Dict[str, Any]) -> List[str]:
        """미디어 URL 추출 - Instagram의 다양한 형식 지원"""
        urls = []
        
        # 다양한 가능한 필드명들
        possible_fields = [
            "media_url", "video_url", "url", "src", "display_url",
            "thumbnail_url", "display_src", "video_src",
            # Instagram Graph API 형식
            "media_url_https", "video_url_https", "display_resources",
            # BrightData 특수 형식
            "image_url", "images", "videos", "media"
        ]
        
        for field in possible_fields:
            if field in media_item and media_item[field]:
                value = media_item[field]
                
                if isinstance(value, list):
                    # 배열인 경우 모든 URL 추가
                    for item in value:
                        if isinstance(item, str):
                            urls.append(item)
                        elif isinstance(item, dict):
                            # display_resources와 같은 구조 처리
                            if "src" in item:
                                urls.append(item["src"])
                            elif "url" in item:
                                urls.append(item["url"])
                elif isinstance(value, str):
                    urls.append(value)
                elif isinstance(value, dict):
                    # 중첩된 구조 처리
                    if "src" in value:
                        urls.append(value["src"])
                    elif "url" in value:
                        urls.append(value["url"])
        
        # edge_sidecar_to_children 처리 (Instagram carousel posts)
        if "edge_sidecar_to_children" in media_item:
            edges = media_item["edge_sidecar_to_children"].get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                child_urls = self._extract_media_urls(node)
                urls.extend(child_urls)
        
        # 중복 제거
        unique_urls = list(dict.fromkeys(urls))  # 순서 유지하며 중복 제거
        
        if unique_urls:
            logger.debug(f"미디어 URL 추출 완료: {len(unique_urls)}개")
        
        return unique_urls
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """텍스트에서 해시태그 추출"""
        if not text:
            return []
        
        import re
        hashtags = re.findall(r'#\w+', text)
        return hashtags
    
    def _extract_profile_from_brightdata(self, data: List[Dict], username: str) -> Optional[Dict]:
        """BrightData 프로필 데이터에서 프로필 정보를 추출합니다."""
        try:
            for item in data:
                profile_data = self._extract_profile_from_item(item, username)
                if profile_data:
                    return profile_data
            
            # 프로필 데이터가 없으면 기본 프로필 반환
            return self._create_default_profile(username)
            
        except Exception as e:
            logger.error(f"프로필 데이터 추출 오류: {str(e)}")
            return self._create_default_profile(username)
    
    def _extract_posts_from_brightdata(self, data: List[Dict], username: str) -> List[Dict]:
        """BrightData 게시물 데이터에서 게시물 정보를 추출합니다."""
        posts = []
        
        try:
            for item in data:
                if self._is_post_item(item):
                    post = self._extract_post_from_item(item, username)
                    if post:
                        posts.append(post)
            
            logger.info(f"게시물 추출 완료: {len(posts)}개")
            return posts
            
        except Exception as e:
            logger.error(f"게시물 데이터 추출 오류: {str(e)}")
            return []
    
    def _extract_reels_from_brightdata(self, data: List[Dict], username: str) -> List[Dict]:
        """BrightData 릴스 데이터에서 릴스 정보를 추출합니다."""
        reels = []
        
        try:
            for item in data:
                if self._is_reel_item(item) or item.get("media_type") == "VIDEO":
                    reel = self._extract_reel_from_item(item, username)
                    if reel:
                        reels.append(reel)
            
            logger.info(f"릴스 추출 완료: {len(reels)}개")
            return reels
            
        except Exception as e:
            logger.error(f"릴스 데이터 추출 오류: {str(e)}")
            return []
