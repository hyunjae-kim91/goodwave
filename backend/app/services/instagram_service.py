import requests
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import sys
import os
from pathlib import Path

# instagram_api.py 임포트 (백엔드 루트 디렉토리에 복사됨)
backend_root = str(Path(__file__).parent.parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
from instagram_api import Instagram

from app.core.config import settings
from app.services.s3_service import s3_service
from app.services.openai_service import openai_service

class InstagramService:
    def __init__(self):
        self.api_key = settings.brightdata_api_key
        self.instagram_api = Instagram()
        self.base_url = settings.brightdata_service_url

    def get_grade_from_followers(self, follower_count: int) -> str:
        """팔로워 수에 따른 등급 분류"""
        if follower_count >= 100000:
            return "A"
        elif follower_count >= 10000:
            return "B"
        else:
            return "C"

    async def collect_instagram_post_data(self, post_url: str) -> Optional[Dict[str, Any]]:
        """인스타그램 게시물 데이터 수집"""
        try:
            # instagram_api.py의 올바른 스냅샷 방식 사용
            config = {"include_errors": True}
            data = await self.instagram_api.get_post_data(post_url, config)
            
            if data:
                # data가 리스트인 경우 첫 번째 유효한 데이터 항목을 찾아서 처리
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and not item.get('warning'):
                            return await self._process_instagram_post(item)
                    print(f"No valid post data found in response for: {post_url}")
                    return None
                else:
                    return await self._process_instagram_post(data)
            else:
                print(f"No data returned for Instagram post: {post_url}")
                return None
                
        except Exception as e:
            print(f"Error in collect_instagram_post_data: {str(e)}")
            return None

    async def collect_instagram_reel_data(self, reel_url: str) -> Optional[Dict[str, Any]]:
        """인스타그램 릴스 데이터 수집"""
        try:
            # instagram_api.py의 올바른 스냅샷 방식 사용
            config = {"include_errors": True}
            data = await self.instagram_api.get_reel_data(reel_url, config)
            
            if data:
                # data가 리스트인 경우 첫 번째 유효한 데이터 항목을 찾아서 처리
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and not item.get('warning'):
                            return await self._process_instagram_reel(item)
                    print(f"No valid reel data found in response for: {reel_url}")
                    return None
                else:
                    return await self._process_instagram_reel(data)
            else:
                print(f"No data returned for Instagram reel: {reel_url}")
                return None
                
        except Exception as e:
            print(f"Error in collect_instagram_reel_data: {str(e)}")
            return None

    async def collect_user_posts_thumbnails(self, username: str, limit: int = 24) -> List[Dict[str, Any]]:
        """사용자의 게시물 썸네일 이미지 24개 수집"""
        try:
            if not hasattr(self, 'base_url') or not self.base_url:
                print(f"Base URL not configured for API requests")
                return []
                
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'username': username,
                'limit': limit,
                'media_type': 'post'
            }
            
            response = requests.post(
                f"{self.base_url}/instagram/user/posts",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data or not isinstance(data, dict):
                    print(f"Invalid response data for user posts: {username}")
                    return []
                return await self._process_user_posts(data, username)
            else:
                print(f"Error fetching user posts: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error in collect_user_posts_thumbnails: {str(e)}")
            return []

    async def collect_user_reels_thumbnails(self, username: str, limit: int = 24) -> List[Dict[str, Any]]:
        """사용자의 릴스 썸네일 이미지 24개 수집"""
        try:
            profile_url = f"https://www.instagram.com/{username}/"
            print(f"🎬 사용자 릴스 수집 시작: {profile_url}")
            
            # BrightData 서비스를 사용하여 프로필 데이터 수집
            from .brightdata_service import BrightDataService
            from ..db.database import get_db
            db_session = next(get_db())
            brightdata_service = BrightDataService(db_session)
            
            # 프로필 + 릴스 수집 옵션
            options = {
                "collect_profile": True,
                "collect_posts": False,
                "collect_reels": True
            }
            
            results = await brightdata_service.collect_instagram_data_batch([profile_url], options)
            
            if not results or len(results) == 0:
                print(f"No data received for {username}")
                return []
            
            result = results[0]
            reels = result.get('reels', [])
            
            if not reels:
                print(f"No reels found for {username}")
                return []
            
            processed_reels = []
            for reel in reels[:limit]:  # limit 적용
                try:
                    processed_reel = await self._process_instagram_reel(reel)
                    if processed_reel:
                        processed_reels.append(processed_reel)
                except Exception as e:
                    print(f"Error processing reel for {username}: {str(e)}")
                    continue
            
            print(f"✅ 처리된 릴스 수: {len(processed_reels)}개")
            return processed_reels
                
        except Exception as e:
            print(f"Error in collect_user_reels_thumbnails: {str(e)}")
            return []

    async def _process_instagram_post(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """게시물 데이터 처리"""
        processed_data = {
            'post_id': data.get('id'),
            'username': data.get('username'),
            'display_name': data.get('display_name'),
            'follower_count': data.get('follower_count', 0),
            'thumbnail_url': data.get('thumbnail_url'),
            'likes_count': data.get('likes_count', 0),
            'comments_count': data.get('comments_count', 0),
            'posted_at': self._parse_datetime(data.get('posted_at'))
        }
        
        # S3에 썸네일 업로드
        if processed_data['thumbnail_url']:
            s3_url = await s3_service.upload_instagram_thumbnail(
                processed_data['thumbnail_url'],
                processed_data['username'],
                'post'
            )
            processed_data['s3_thumbnail_url'] = s3_url
        
        # 등급 분류
        processed_data['grade'] = self.get_grade_from_followers(processed_data['follower_count'])
        
        # OpenAI를 통한 이미지 분류
        if processed_data['s3_thumbnail_url']:
            motivation = await openai_service.classify_image(
                processed_data['s3_thumbnail_url'],
                'motivation'
            )
            category = await openai_service.classify_image(
                processed_data['s3_thumbnail_url'],
                'category'
            )
            processed_data['subscription_motivation'] = motivation
            processed_data['category'] = category
        
        return processed_data

    async def _process_instagram_reel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """릴스 데이터 처리"""
        processed_data = {
            'reel_id': data.get('id'),
            'username': data.get('username'),
            'display_name': data.get('display_name'),
            'follower_count': data.get('follower_count', 0),
            'thumbnail_url': data.get('thumbnail_url'),
            'video_view_count': data.get('video_view_count', 0),
            'posted_at': self._parse_datetime(data.get('posted_at'))
        }
        
        # S3에 썸네일 업로드
        if processed_data['thumbnail_url']:
            s3_url = await s3_service.upload_instagram_thumbnail(
                processed_data['thumbnail_url'],
                processed_data['username'],
                'reel'
            )
            processed_data['s3_thumbnail_url'] = s3_url
        
        # 등급 분류
        processed_data['grade'] = self.get_grade_from_followers(processed_data['follower_count'])
        
        # OpenAI를 통한 이미지 분류
        if processed_data['s3_thumbnail_url']:
            motivation = await openai_service.classify_image(
                processed_data['s3_thumbnail_url'],
                'motivation'
            )
            category = await openai_service.classify_image(
                processed_data['s3_thumbnail_url'],
                'category'
            )
            processed_data['subscription_motivation'] = motivation
            processed_data['category'] = category
        
        return processed_data

    async def _process_user_posts(self, data: Dict[str, Any], username: str) -> List[Dict[str, Any]]:
        """사용자 게시물들 처리"""
        posts = []
        posts_data = data.get('posts', [])
        if not isinstance(posts_data, list):
            print(f"Invalid posts data type for {username}: expected list, got {type(posts_data)}")
            return []
            
        for item in posts_data:
            if not item or not isinstance(item, dict):
                print(f"Skipping invalid post item for {username}: {item}")
                continue
            try:
                post_data = await self._process_instagram_post(item)
                if post_data:
                    posts.append(post_data)
            except Exception as e:
                print(f"Error processing post for {username}: {str(e)}")
                continue
        return posts

    async def _process_user_reels(self, data: Dict[str, Any], username: str) -> List[Dict[str, Any]]:
        """사용자 릴스들 처리"""
        reels = []
        reels_data = data.get('reels', [])
        if not isinstance(reels_data, list):
            print(f"Invalid reels data type for {username}: expected list, got {type(reels_data)}")
            return []
            
        for item in reels_data:
            if not item or not isinstance(item, dict):
                print(f"Skipping invalid reel item for {username}: {item}")
                continue
            try:
                reel_data = await self._process_instagram_reel(item)
                if reel_data:
                    reels.append(reel_data)
            except Exception as e:
                print(f"Error processing reel for {username}: {str(e)}")
                continue
        return reels

    def _parse_datetime(self, date_string: str) -> Optional[datetime]:
        """날짜 문자열을 datetime 객체로 변환"""
        if not date_string:
            return None
        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except:
            return None

instagram_service = InstagramService()
