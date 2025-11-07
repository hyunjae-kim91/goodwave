import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from ..db.database import get_db
from ..db.models import (
    InfluencerProfile, InfluencerPost, InfluencerReel, 
    InfluencerAnalysis, SystemPrompt, BatchIngestSession, BatchSessionResult
)
from ..models.influencer_models import Profile, Post
from .s3_service import S3Service
from ..utils.sequence_fixer import safe_db_operation

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
    def _sanitize_profile_data(profile_data: Dict[str, Any], fallback_username: str = None) -> Dict[str, Any]:
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

        username = profile_data.get("username") or profile_data.get("user_posted") or fallback_username
        if not username:
            raise ValueError("프로필 데이터에 username이 없습니다")

        # 매핑된 필드만 추출
        sanitized: Dict[str, Any] = {key: profile_data.get(key) for key in allowed_fields if key in profile_data}
        sanitized["username"] = username
        sanitized.setdefault("full_name", profile_data.get("profile_name") or username)
        sanitized.setdefault("profile_name", sanitized.get("full_name"))
        
        # BrightData API 필드명 매핑 시도
        field_mappings = {
            "followers": ["followers", "follower_count", "followers_count", "num_followers"],
            "following": ["following", "following_count", "followees_count", "num_following"],
            "posts_count": ["posts_count", "post_count", "num_posts", "media_count"],
            "full_name": ["full_name", "name", "display_name", "real_name"],
            "bio": ["bio", "biography", "description"],
            "profile_pic_url": ["profile_pic_url", "profile_picture_url", "avatar_url", "picture_url"]
        }
        
        # 다양한 필드명으로 매핑 시도
        for standard_field, possible_fields in field_mappings.items():
            if standard_field not in sanitized or sanitized[standard_field] is None:
                for field_name in possible_fields:
                    if field_name in profile_data and profile_data[field_name] is not None:
                        sanitized[standard_field] = profile_data[field_name]
                        logger.info(f"🔗 필드 매핑 성공: {field_name} -> {standard_field} = {profile_data[field_name]}")
                        break

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
    
    def create_or_update_profile(self, profile_data: Dict[str, Any], fallback_username: str = None) -> InfluencerProfile:
        """프로필 생성 또는 업데이트 - 중복키 이슈 완전 방지"""
        try:
            # 원본 프로필 데이터 로깅
            logger.info(f"🔍 원본 프로필 데이터: {json.dumps(profile_data, ensure_ascii=False, indent=2)}")
            
            sanitized = self._sanitize_profile_data(profile_data, fallback_username)
            username = sanitized["username"]
            
            # 정제된 프로필 데이터 로깅
            logger.info(f"🧹 정제된 프로필 데이터: {json.dumps(sanitized, ensure_ascii=False, indent=2)}")
            
            # 1. 기존 프로필 확인 (대소문자 구분 없이)
            existing_profile = self.db.query(InfluencerProfile).filter(
                InfluencerProfile.username.ilike(username)
            ).first()
            
            if existing_profile:
                # 기존 프로필 업데이트
                logger.info(f"📝 기존 프로필 업데이트: {existing_profile.username} (ID: {existing_profile.id})")
                for key, value in sanitized.items():
                    if hasattr(existing_profile, key) and key != 'id':  # ID는 업데이트하지 않음
                        setattr(existing_profile, key, value)
                existing_profile.updated_at = now_kst()
                self.db.commit()
                self.db.refresh(existing_profile)
                logger.info(f"✅ 프로필 업데이트 완료: {existing_profile.username}")
                return existing_profile
            else:
                # 새 프로필 생성 (한 번 더 체크)
                logger.info(f"➕ 새 프로필 생성 시도: {username}")
                
                # 생성 직전 다시 한 번 확인 (race condition 방지)
                double_check = self.db.query(InfluencerProfile).filter(
                    InfluencerProfile.username.ilike(username)
                ).first()
                
                if double_check:
                    logger.warning(f"⚠️ 생성 중 기존 프로필 발견: {username} - 업데이트로 전환")
                    for key, value in sanitized.items():
                        if hasattr(double_check, key) and key != 'id':
                            setattr(double_check, key, value)
                    double_check.updated_at = now_kst()
                    self.db.commit()
                    self.db.refresh(double_check)
                    return double_check
                
                # 새 프로필 생성
                db_profile = InfluencerProfile(**sanitized)
                self.db.add(db_profile)
                self.db.commit()
                self.db.refresh(db_profile)
                logger.info(f"✅ 새 프로필 생성 완료: {db_profile.username} (ID: {db_profile.id})")
                return db_profile
                
        except Exception as e:
            logger.error(f"❌ 프로필 생성/업데이트 실패: {username} - {str(e)}")
            self.db.rollback()
            
            # 실패 시 기존 프로필이 있는지 다시 확인
            existing = self.db.query(InfluencerProfile).filter(
                InfluencerProfile.username.ilike(username)
            ).first()
            if existing:
                logger.info(f"🔄 실패 후 기존 프로필 반환: {existing.username}")
                return existing
            else:
                raise e
    
    def save_posts(self, profile_id: int, posts_data: List[Dict[str, Any]]) -> List[InfluencerPost]:
        """게시물 저장 - 새로운 데이터로 완전 교체"""
        saved_posts = []
        for post_data in posts_data:
            # 새 게시물 생성 (기존 데이터는 이미 삭제됨)
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
        """릴스 저장 - 새로운 데이터로 완전 교체"""
        print(f"🎬 Save: Starting to save {len(reels_data)} reels for profile_id={profile_id}")
        saved_reels = []
        
        for idx, reel_data in enumerate(reels_data):
            reel_id = reel_data.get("reel_id")
            print(f"🔍 Creating new reel {reel_id}")
            
            try:
                reel_data["profile_id"] = profile_id
                
                # 새 릴스 생성 (기존 데이터는 이미 삭제됨)
                print(f"➕ Creating new reel: {reel_id}")
                new_reel = InfluencerReel(**reel_data)
                self.db.add(new_reel)
                self.db.flush()  # ID 생성을 위해 flush
                saved_reels.append(new_reel)
                print(f"✅ Create Success: {reel_id} (ID: {new_reel.id})")
                    
            except Exception as e:
                print(f"❌ Create Error: {reel_id} - {e}")
                # 개별 실패해도 계속 진행
                continue
        
        # 한 번에 커밋
        try:
            self.db.commit()
            print(f"✅ Commit: {len(saved_reels)} reels committed")
            
            # 새로고침
            for reel in saved_reels:
                self.db.refresh(reel)
                
        except Exception as commit_error:
            print(f"❌ Commit Error: {commit_error}")
            self.db.rollback()
            saved_reels = []
        
        print(f"🎉 Complete: {len(saved_reels)} reels saved")
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
        """분석 결과 저장 (UniqueViolation 자동 복구 기능 포함)"""
        
        def _save_operation():
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
        
        # UniqueViolation 발생 시 자동으로 시퀀스 리셋 후 재시도
        return safe_db_operation(
            self.db,
            _save_operation,
            'influencer_analysis',
            max_retries=2
        )
    
    def get_analysis_result(self, profile_id: int, analysis_type: str) -> Optional[InfluencerAnalysis]:
        """분석 결과 조회"""
        return self.db.query(InfluencerAnalysis).filter(
            and_(
                InfluencerAnalysis.profile_id == profile_id,
                InfluencerAnalysis.analysis_type == analysis_type
            )
        ).first()

    async def save_profile_data(self, profile_data: Dict[str, Any], fallback_username: str = None) -> InfluencerProfile:
        """비동기 워커 호환 프로필 저장"""
        return self.create_or_update_profile(profile_data, fallback_username)

    async def save_posts_data(self, posts_data: List[Dict[str, Any]], username: str) -> List[InfluencerPost]:
        profile = self.get_profile_by_username(username)
        if not profile:
            profile = self.create_or_update_profile({"username": username})

        # 기존 게시물 데이터 삭제 (새로운 수집으로 교체)
        existing_posts = self.db.query(InfluencerPost).filter(
            InfluencerPost.profile_id == profile.id
        ).all()
        
        if existing_posts:
            print(f"🗑️ 기존 게시물 {len(existing_posts)}개 삭제 중...")
            for post in existing_posts:
                self.db.delete(post)
            self.db.commit()
            print(f"✅ 기존 게시물 데이터 삭제 완료")

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

        # 기존 릴스 데이터 삭제 (새로운 수집으로 교체)
        existing_reels = self.db.query(InfluencerReel).filter(
            InfluencerReel.profile_id == profile.id
        ).all()
        
        if existing_reels:
            print(f"🗑️ 기존 릴스 {len(existing_reels)}개 삭제 중...")
            for reel in existing_reels:
                self.db.delete(reel)
            self.db.commit()
            print(f"✅ 기존 릴스 데이터 삭제 완료")

        sanitized_reels = []
        for reel in reels_data:
            thumbnail_source = (
                reel.get("thumbnail")
                or reel.get("thumbnail_url")
                or (reel.get("media_urls") or [None])[0]
            )

            sanitized = self._sanitize_reel_data(reel)
            if sanitized:
                # 더미/테스트 URL 무시
                if (thumbnail_source and 
                    self.s3_service and 
                    self.s3_service.bucket_name not in thumbnail_source and
                    "placeholder" not in thumbnail_source.lower() and
                    "via.placeholder" not in thumbnail_source.lower()):
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
                elif thumbnail_source and "placeholder" in thumbnail_source.lower():
                    logger.warning(f"더미 이미지 URL 무시: {thumbnail_source}")

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
        try:
            profile = self.get_profile_by_username(username)
            if profile:
                profile_id = profile.id
                logger.info(f"🗑️ 프로필 ID {profile_id}의 모든 데이터 삭제 중: {username}")
                
                # 관련 데이터 수동 삭제 (CASCADE 설정이 안되어 있어서)
                # 1. 분석 결과 삭제
                analysis_count = self.db.query(InfluencerAnalysis).filter(
                    InfluencerAnalysis.profile_id == profile_id
                ).delete(synchronize_session=False)
                logger.info(f"  - 분석 결과 {analysis_count}개 삭제됨")
                
                # 2. 릴스 데이터 삭제  
                reels_count = self.db.query(InfluencerReel).filter(
                    InfluencerReel.profile_id == profile_id
                ).delete(synchronize_session=False)
                logger.info(f"  - 릴스 데이터 {reels_count}개 삭제됨")
                
                # 3. 게시물 데이터 삭제
                posts_count = self.db.query(InfluencerPost).filter(
                    InfluencerPost.profile_id == profile_id
                ).delete(synchronize_session=False)
                logger.info(f"  - 게시물 데이터 {posts_count}개 삭제됨")
                
                # 4. 프로필 삭제
                self.db.delete(profile)
                self.db.commit()
                logger.info(f"✅ 프로필 {username} (ID: {profile_id}) 완전 삭제 완료")
                return True
            else:
                logger.info(f"ℹ️ 삭제할 프로필이 없음: {username}")
                return False
        except Exception as e:
            logger.error(f"❌ 프로필 삭제 실패: {username} - {str(e)}")
            self.db.rollback()
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
