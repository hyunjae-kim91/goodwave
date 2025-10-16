import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta

from ..db.database import get_db
from ..db.models import (
    InfluencerProfile, InfluencerPost, InfluencerReel, 
    InfluencerAnalysis, SystemPrompt, BatchIngestSession, BatchSessionResult
)
from ..models.influencer_models import Profile, Post
from .s3_service import S3Service

logger = logging.getLogger(__name__)

KST_OFFSET = timedelta(hours=9)


def now_kst() -> datetime:
    return datetime.utcnow() + KST_OFFSET

class InfluencerService:
    def __init__(self, db: Session, s3_service: Optional[S3Service] = None):
        self.db = db
        self.s3_service = s3_service or S3Service()

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except (ValueError, OSError):
                return None
        if isinstance(value, str):
            candidates = [
                value,
                value.replace("Z", "+00:00") if value.endswith("Z") else value,
            ]
            for candidate in candidates:
                try:
                    return datetime.fromisoformat(candidate)
                except ValueError:
                    continue
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _sanitize_profile_data(profile_data: Dict[str, Any]) -> Dict[str, Any]:
        allowed_fields = {
            "username",
            "full_name",
            "followers",
            "following",
            "bio",
            "profile_pic_url",
            "account",
            "posts_count",
            "avg_engagement",
            "category_name",
            "profile_name",
            "email_address",
            "is_business_account",
            "is_professional_account",
            "is_verified",
        }

        username = profile_data.get("username") or profile_data.get("user_posted")
        if not username:
            raise ValueError("프로필 데이터에 username이 없습니다")

        sanitized: Dict[str, Any] = {key: profile_data.get(key) for key in allowed_fields if key in profile_data}
        sanitized["username"] = username
        sanitized.setdefault("full_name", profile_data.get("profile_name") or username)
        sanitized.setdefault("profile_name", sanitized.get("full_name"))

        # 숫자 필드 정규화
        for numeric_field in ("followers", "following", "posts_count"):
            value = sanitized.get(numeric_field)
            if value is not None:
                try:
                    sanitized[numeric_field] = int(value)
                except (TypeError, ValueError):
                    sanitized[numeric_field] = None

        if sanitized.get("avg_engagement") is not None:
            try:
                sanitized["avg_engagement"] = float(sanitized["avg_engagement"])
            except (TypeError, ValueError):
                sanitized["avg_engagement"] = None

        return sanitized

    def _sanitize_post_data(self, post_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        post_id = post_data.get("post_id") or post_data.get("id")
        if not post_id:
            return None

        sanitized: Dict[str, Any] = {
            "post_id": str(post_id),
            "media_type": post_data.get("media_type") or post_data.get("content_type"),
            "media_urls": post_data.get("media_urls") or post_data.get("mediaUrls") or [],
            "caption": post_data.get("caption") or post_data.get("description"),
            "timestamp": self._parse_datetime(post_data.get("timestamp")),
            "user_posted": post_data.get("user_posted") or post_data.get("username"),
            "profile_url": post_data.get("profile_url"),
            "date_posted": post_data.get("date_posted"),
            "num_comments": post_data.get("num_comments"),
            "likes": post_data.get("likes"),
            "photos": post_data.get("photos") or post_data.get("media_urls") or [],
            "content_type": post_data.get("content_type") or "post",
            "description": post_data.get("description") or post_data.get("caption"),
            "hashtags": post_data.get("hashtags") or [],
        }

        for numeric_field in ("num_comments", "likes"):
            value = sanitized.get(numeric_field)
            if isinstance(value, dict) and "count" in value:
                value = value["count"]
            if value is not None:
                try:
                    sanitized[numeric_field] = int(value)
                except (TypeError, ValueError):
                    sanitized[numeric_field] = 0
            else:
                sanitized[numeric_field] = 0

        return sanitized

    def _sanitize_reel_data(self, reel_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        reel_id = reel_data.get("reel_id") or reel_data.get("id")
        if not reel_id:
            return None

        sanitized: Dict[str, Any] = {
            "reel_id": str(reel_id),
            "media_type": reel_data.get("media_type") or "VIDEO",
            "media_urls": reel_data.get("media_urls") or [],
            "caption": reel_data.get("caption") or reel_data.get("description"),
            "timestamp": self._parse_datetime(reel_data.get("timestamp")),
            "user_posted": reel_data.get("user_posted") or reel_data.get("username"),
            "profile_url": reel_data.get("profile_url"),
            "date_posted": reel_data.get("date_posted"),
            "num_comments": reel_data.get("num_comments"),
            "likes": reel_data.get("likes"),
            "photos": reel_data.get("photos") or [],
            "content_type": reel_data.get("content_type") or "reel",
            "description": reel_data.get("description") or reel_data.get("caption"),
            "hashtags": reel_data.get("hashtags") or [],
            "url": reel_data.get("url"),
            "views": reel_data.get("views"),
            "video_play_count": reel_data.get("video_play_count") or reel_data.get("views"),
        }

        for numeric_field in ("num_comments", "likes", "views", "video_play_count"):
            value = sanitized.get(numeric_field)
            if isinstance(value, dict) and "count" in value:
                value = value["count"]
            if value is not None:
                try:
                    sanitized[numeric_field] = int(value)
                except (TypeError, ValueError):
                    sanitized[numeric_field] = 0
            else:
                sanitized[numeric_field] = 0

        return sanitized
    
    def create_or_update_profile(self, profile_data: Dict[str, Any]) -> InfluencerProfile:
        """프로필 생성 또는 업데이트"""
        sanitized = self._sanitize_profile_data(profile_data)
        existing_profile = self.db.query(InfluencerProfile).filter(
            InfluencerProfile.username == sanitized["username"]
        ).first()
        
        if existing_profile:
            for key, value in sanitized.items():
                if hasattr(existing_profile, key):
                    setattr(existing_profile, key, value)
            existing_profile.updated_at = now_kst()
            self.db.commit()
            self.db.refresh(existing_profile)
            return existing_profile
        else:
            db_profile = InfluencerProfile(**sanitized)
            self.db.add(db_profile)
            self.db.commit()
            self.db.refresh(db_profile)
            return db_profile
    
    def save_posts(self, profile_id: int, posts_data: List[Dict[str, Any]]) -> List[InfluencerPost]:
        """게시물 저장"""
        saved_posts = []
        for post_data in posts_data:
            existing_post = self.db.query(InfluencerPost).filter(
                InfluencerPost.post_id == post_data["post_id"]
            ).first()
            
            if not existing_post:
                post_data["profile_id"] = profile_id
                db_post = InfluencerPost(**post_data)
                self.db.add(db_post)
                saved_posts.append(db_post)
        
        if saved_posts:
            self.db.commit()
            for post in saved_posts:
                self.db.refresh(post)
        
        return saved_posts
    
    def save_reels(self, profile_id: int, reels_data: List[Dict[str, Any]]) -> List[InfluencerReel]:
        """릴스 저장"""
        print(f"🎬 DB Save: Starting to save {len(reels_data)} reels for profile_id={profile_id}")
        saved_reels = []
        
        for idx, reel_data in enumerate(reels_data):
            reel_id = reel_data.get("reel_id")
            print(f"🔍 DB Check: Checking if reel {reel_id} already exists")
            
            existing_reel = self.db.query(InfluencerReel).filter(
                InfluencerReel.reel_id == reel_id
            ).first()
            
            if existing_reel:
                print(f"⚠️ DB Skip: Reel {reel_id} already exists, skipping")
            else:
                print(f"➕ DB Insert: Adding new reel {reel_id}")
                reel_data["profile_id"] = profile_id
                
                # DB 필드 매핑 로깅
                print(f"🗂️ DB Fields: {list(reel_data.keys())}")
                print(f"📊 DB Values: reel_id={reel_data.get('reel_id')}, media_type={reel_data.get('media_type')}, views={reel_data.get('views')}")
                
                try:
                    db_reel = InfluencerReel(**reel_data)
                    self.db.add(db_reel)
                    saved_reels.append(db_reel)
                    print(f"✅ DB Success: Added reel {reel_id} to session")
                except Exception as e:
                    print(f"❌ DB Error: Failed to create InfluencerReel: {e}")
                    print(f"💥 DB Error Data: {reel_data}")
                    raise
        
        if saved_reels:
            print(f"💾 DB Commit: Committing {len(saved_reels)} reels to database")
            try:
                self.db.commit()
                print(f"✅ DB Commit Success: All reels committed")
                
                for idx, reel in enumerate(saved_reels):
                    self.db.refresh(reel)
                    print(f"🔄 DB Refresh: Refreshed reel {idx+1}, ID={reel.id}")
            except Exception as e:
                print(f"❌ DB Commit Error: {e}")
                self.db.rollback()
                raise
        else:
            print(f"📝 DB Skip: No new reels to save")
        
        print(f"🎉 DB Complete: Successfully processed {len(reels_data)} reels, saved {len(saved_reels)} new ones")
        return saved_reels
    
    def get_profile_by_username(self, username: str) -> Optional[InfluencerProfile]:
        """사용자명으로 프로필 조회"""
        return self.db.query(InfluencerProfile).filter(
            InfluencerProfile.username == username
        ).first()
    
    def get_posts_by_profile_id(self, profile_id: int) -> List[InfluencerPost]:
        """프로필 ID로 게시물 조회"""
        return self.db.query(InfluencerPost).filter(
            InfluencerPost.profile_id == profile_id
        ).all()
    
    def get_reels_by_profile_id(self, profile_id: int) -> List[InfluencerReel]:
        """프로필 ID로 릴스 조회"""
        return self.db.query(InfluencerReel).filter(
            InfluencerReel.profile_id == profile_id
        ).all()
    
    def save_analysis_result(
        self,
        profile_id: int,
        analysis_type: str,
        analysis_result: Dict[str, Any],
        prompt_used: str | None = None,
        reel_id: int | None = None,
    ) -> InfluencerAnalysis:
        """분석 결과 저장"""
        query = self.db.query(InfluencerAnalysis).filter(
            InfluencerAnalysis.profile_id == profile_id,
            InfluencerAnalysis.analysis_type == analysis_type
        )

        if reel_id is not None:
            query = query.filter(InfluencerAnalysis.reel_id == reel_id)
        else:
            query = query.filter(InfluencerAnalysis.reel_id.is_(None))

        existing_analysis = query.first()
        
        if existing_analysis:
            existing_analysis.analysis_result = analysis_result
            existing_analysis.prompt_used = prompt_used
            existing_analysis.created_at = now_kst()
            existing_analysis.reel_id = reel_id
            self.db.commit()
            self.db.refresh(existing_analysis)
            return existing_analysis
        else:
            db_analysis = InfluencerAnalysis(
                profile_id=profile_id,
                analysis_type=analysis_type,
                reel_id=reel_id,
                analysis_result=analysis_result,
                prompt_used=prompt_used
            )
            self.db.add(db_analysis)
            self.db.commit()
            self.db.refresh(db_analysis)
            return db_analysis
    
    def get_analysis_result(self, profile_id: int, analysis_type: str) -> Optional[InfluencerAnalysis]:
        """분석 결과 조회"""
        return self.db.query(InfluencerAnalysis).filter(
            and_(
                InfluencerAnalysis.profile_id == profile_id,
                InfluencerAnalysis.analysis_type == analysis_type
            )
        ).first()

    async def save_profile_data(self, profile_data: Dict[str, Any]) -> InfluencerProfile:
        """비동기 워커 호환 프로필 저장"""
        return self.create_or_update_profile(profile_data)

    async def save_posts_data(self, posts_data: List[Dict[str, Any]], username: str) -> List[InfluencerPost]:
        profile = self.get_profile_by_username(username)
        if not profile:
            profile = self.create_or_update_profile({"username": username})

        sanitized_posts = []
        for post in posts_data:
            sanitized = self._sanitize_post_data(post)
            if sanitized:
                sanitized_posts.append(sanitized)

        if not sanitized_posts:
            return []

        return self.save_posts(profile.id, sanitized_posts)

    async def save_reels_data(self, reels_data: List[Dict[str, Any]], username: str) -> List[InfluencerReel]:
        profile = self.get_profile_by_username(username)
        if not profile:
            profile = self.create_or_update_profile({"username": username})

        sanitized_reels = []
        for reel in reels_data:
            thumbnail_source = (
                reel.get("thumbnail")
                or reel.get("thumbnail_url")
                or (reel.get("media_urls") or [None])[0]
            )

            sanitized = self._sanitize_reel_data(reel)
            if sanitized:
                if thumbnail_source and self.s3_service and self.s3_service.bucket_name not in thumbnail_source:
                    try:
                        s3_url = await self.s3_service.upload_instagram_thumbnail(
                            thumbnail_source,
                            username=username,
                            post_type="reel"
                        )
                        if s3_url:
                            sanitized["media_urls"] = [s3_url]
                            sanitized["photos"] = [s3_url]
                    except Exception as e:
                        logger.error(f"릴스 썸네일 업로드 실패: {thumbnail_source} - {e}")

                sanitized_reels.append(sanitized)

        if not sanitized_reels:
            return []

        return self.save_reels(profile.id, sanitized_reels)
    
    def get_all_profiles(self) -> List[InfluencerProfile]:
        """모든 프로필 조회"""
        return self.db.query(InfluencerProfile).order_by(
            InfluencerProfile.updated_at.desc()
        ).all()
    
    def delete_profile(self, username: str) -> bool:
        """프로필 및 관련 데이터 삭제"""
        profile = self.get_profile_by_username(username)
        if profile:
            # 관련 데이터 수동 삭제 (CASCADE 설정이 안되어 있어서)
            # 1. 분석 결과 삭제
            self.db.query(InfluencerAnalysis).filter(
                InfluencerAnalysis.profile_id == profile.id
            ).delete()
            
            # 2. 릴스 데이터 삭제
            self.db.query(InfluencerReel).filter(
                InfluencerReel.profile_id == profile.id
            ).delete()
            
            # 3. 게시물 데이터 삭제
            self.db.query(InfluencerPost).filter(
                InfluencerPost.profile_id == profile.id
            ).delete()
            
            # 4. 프로필 삭제
            self.db.delete(profile)
            self.db.commit()
            return True
        return False
    
    def create_batch_session(self, session_id: str, total_requested: int, 
                           summary: Dict[str, Any]) -> BatchIngestSession:
        """배치 세션 생성"""
        db_session = BatchIngestSession(
            session_id=session_id,
            total_requested=total_requested,
            summary=summary
        )
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session
    
    def add_batch_result(self, session_id: str, url: str, success: bool, 
                        username: str = None, error_message: str = None) -> BatchSessionResult:
        """배치 결과 추가"""
        db_result = BatchSessionResult(
            session_id=session_id,
            url=url,
            success=success,
            username=username,
            error_message=error_message
        )
        self.db.add(db_result)
        self.db.commit()
        self.db.refresh(db_result)
        return db_result
    
    def update_batch_session(self, session_id: str, success_count: int, 
                           failure_count: int, summary: Dict[str, Any]) -> BatchIngestSession:
        """배치 세션 업데이트"""
        session = self.db.query(BatchIngestSession).filter(
            BatchIngestSession.session_id == session_id
        ).first()
        
        if session:
            session.success_count = success_count
            session.failure_count = failure_count
            session.summary = summary
            session.completed_at = now_kst()
            self.db.commit()
            self.db.refresh(session)
            return session
        else:
            raise ValueError(f"Session {session_id} not found")
    
    def get_batch_session(self, session_id: str) -> Optional[BatchIngestSession]:
        """배치 세션 조회"""
        return self.db.query(BatchIngestSession).filter(
            BatchIngestSession.session_id == session_id
        ).first()

class SystemPromptService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_prompt_by_type(self, prompt_type: str) -> Optional[SystemPrompt]:
        """타입별 활성 프롬프트 조회"""
        return self.db.query(SystemPrompt).filter(
            and_(
                SystemPrompt.prompt_type == prompt_type,
                SystemPrompt.is_active == True
            )
        ).first()
    
    def create_or_update_prompt(self, prompt_type: str, content: str) -> SystemPrompt:
        """프롬프트 생성 또는 업데이트"""
        # 기존 활성 프롬프트 비활성화
        existing_prompts = self.db.query(SystemPrompt).filter(
            and_(
                SystemPrompt.prompt_type == prompt_type,
                SystemPrompt.is_active == True
            )
        ).all()
        
        for prompt in existing_prompts:
            prompt.is_active = False
        
        # 새 프롬프트 생성
        new_prompt = SystemPrompt(
            prompt_type=prompt_type,
            content=content,
            is_active=True
        )
        self.db.add(new_prompt)
        self.db.commit()
        self.db.refresh(new_prompt)
        return new_prompt
    
    def get_all_prompts(self) -> List[SystemPrompt]:
        """모든 활성 프롬프트 조회"""
        return self.db.query(SystemPrompt).filter(
            SystemPrompt.is_active == True
        ).order_by(SystemPrompt.prompt_type).all()

    def get_prompt_types(self) -> List[str]:
        prompts = (
            self.db.query(SystemPrompt)
            .filter(SystemPrompt.is_active == True)
            .order_by(SystemPrompt.prompt_type)
            .all()
        )
        return [prompt.prompt_type for prompt in prompts if prompt.prompt_type]
