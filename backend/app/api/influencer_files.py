from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from typing import List, Dict, Any

from ..models.influencer_models import DeleteUsersRequest
from ..services.influencer_service import InfluencerService
from ..db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/influencer/files/users")
async def get_saved_users(db: Session = Depends(get_db)):
    """저장된 인플루언서 사용자 목록을 반환합니다."""
    try:
        influencer_service = InfluencerService(db)
        profiles = influencer_service.get_all_profiles()
        
        users = []
        for profile in profiles:
            posts_count = len(profile.influencer_posts)
            reels_count = len(profile.influencer_reels)
            
            user_info = {
                "username": profile.username,
                "hasProfile": True,
                "hasPosts": posts_count > 0,
                "hasReels": reels_count > 0,
                "lastModified": profile.updated_at.timestamp() if profile.updated_at else None,
                "postsCount": posts_count,
                "reelsCount": reels_count,
                "followers": profile.followers,
                "fullName": profile.full_name
            }
            users.append(user_info)
        
        return {"users": users}
        
    except Exception as e:
        logger.error(f"사용자 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"사용자 목록 조회 중 오류가 발생했습니다: {str(e)}", 
            "code": "USER_LIST_ERROR"
        })

@router.post("/influencer/files/users/delete")
async def delete_users(req: DeleteUsersRequest, db: Session = Depends(get_db)):
    """선택한 사용자들의 데이터를 삭제합니다."""
    try:
        influencer_service = InfluencerService(db)
        
        deleted_count = 0
        failed_count = 0
        results: List[Dict[str, Any]] = []
        
        for username in req.usernames:
            try:
                success = influencer_service.delete_profile(username)
                if success:
                    results.append({"username": username, "deleted": True})
                    deleted_count += 1
                else:
                    results.append({"username": username, "deleted": False, "error": "User not found"})
                    failed_count += 1
            except Exception as e:
                logger.error(f"사용자 데이터 삭제 실패: {username}, {str(e)}")
                results.append({"username": username, "deleted": False, "error": str(e)})
                failed_count += 1
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "results": results,
        }
        
    except Exception as e:
        logger.error(f"사용자 데이터 일괄 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"사용자 데이터 삭제 중 오류가 발생했습니다: {str(e)}", 
            "code": "USER_DELETE_ERROR"
        })

@router.get("/influencer/files/user/{username}/data")
async def get_user_data(username: str, db: Session = Depends(get_db)):
    """특정 사용자의 저장된 데이터를 조회합니다."""
    try:
        influencer_service = InfluencerService(db)
        
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail={
                "error": f"사용자 {username}를 찾을 수 없습니다",
                "code": "USER_NOT_FOUND"
            })
        
        posts = influencer_service.get_posts_by_profile_id(profile.id)
        reels = influencer_service.get_reels_by_profile_id(profile.id)
        
        # DB 모델을 딕셔너리로 변환
        profile_data = {
            "username": profile.username,
            "fullName": profile.full_name,
            "followers": profile.followers,
            "following": profile.following,
            "bio": profile.bio,
            "profilePicUrl": profile.profile_pic_url,
            "account": profile.account,
            "posts_count": profile.posts_count,
            "avg_engagement": profile.avg_engagement,
            "category_name": profile.category_name,
            "profile_name": profile.profile_name,
            "email_address": profile.email_address,
            "is_business_account": profile.is_business_account,
            "is_professional_account": profile.is_professional_account,
            "is_verified": profile.is_verified
        }
        
        posts_data = []
        for post in posts:
            post_dict = {
                "id": post.post_id,
                "mediaType": post.media_type,
                "mediaUrls": post.media_urls or [],
                "caption": post.caption,
                "timestamp": post.timestamp,
                "user_posted": post.user_posted,
                "profile_url": post.profile_url,
                "date_posted": post.date_posted,
                "num_comments": post.num_comments,
                "likes": post.likes,
                "photos": post.photos or [],
                "content_type": post.content_type,
                "description": post.description,
                "hashtags": post.hashtags or []
            }
            posts_data.append(post_dict)
        
        reels_data = []
        for reel in reels:
            reel_dict = {
                "id": reel.reel_id,
                "mediaType": reel.media_type,
                "mediaUrls": reel.media_urls or [],
                "caption": reel.caption,
                "timestamp": reel.timestamp,
                "user_posted": reel.user_posted,
                "profile_url": reel.profile_url,
                "date_posted": reel.date_posted,
                "num_comments": reel.num_comments,
                "likes": reel.likes,
                "photos": reel.photos or [],
                "content_type": reel.content_type,
                "description": reel.description,
                "hashtags": reel.hashtags or [],
                "url": reel.url,
                "views": reel.views,
                "video_play_count": reel.video_play_count
            }
            reels_data.append(reel_dict)
        
        return {
            "username": username,
            "profile": profile_data,
            "posts": posts_data,
            "reels": reels_data,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 데이터 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"사용자 데이터 조회 중 오류가 발생했습니다: {str(e)}", 
            "code": "USER_DATA_ERROR"
        })

@router.get("/influencer/files/user-profile/{username}")
async def get_user_profile_data(username: str, db: Session = Depends(get_db)):
    """사용자의 프로필 데이터를 반환합니다."""
    try:
        influencer_service = InfluencerService(db)
        
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}의 프로필 데이터를 찾을 수 없습니다")
        
        profile_data = {
            "username": profile.username,
            "fullName": profile.full_name,
            "followers": profile.followers,
            "following": profile.following,
            "bio": profile.bio,
            "profilePicUrl": profile.profile_pic_url,
            "account": profile.account,
            "posts_count": profile.posts_count,
            "avg_engagement": profile.avg_engagement,
            "category_name": profile.category_name,
            "profile_name": profile.profile_name,
            "email_address": profile.email_address,
            "is_business_account": profile.is_business_account,
            "is_professional_account": profile.is_professional_account,
            "is_verified": profile.is_verified
        }
        
        return profile_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 프로필 데이터 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"사용자 프로필 데이터 조회 중 오류가 발생했습니다: {str(e)}", 
            "code": "PROFILE_DATA_ERROR"
        })

@router.get("/influencer/files/parsed-reels/{username}")
async def get_parsed_reels_data(username: str, db: Session = Depends(get_db)):
    """사용자의 릴스 데이터를 반환합니다."""
    try:
        influencer_service = InfluencerService(db)
        
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}의 데이터를 찾을 수 없습니다")
        
        reels = influencer_service.get_reels_by_profile_id(profile.id)
        
        reels_data = []
        for reel in reels:
            reel_dict = {
                "id": reel.reel_id,
                "mediaType": reel.media_type,
                "mediaUrls": reel.media_urls or [],
                "caption": reel.caption,
                "timestamp": reel.timestamp,
                "user_posted": reel.user_posted,
                "profile_url": reel.profile_url,
                "date_posted": reel.date_posted,
                "num_comments": reel.num_comments,
                "likes": reel.likes,
                "photos": reel.photos or [],
                "content_type": reel.content_type,
                "description": reel.description,
                "hashtags": reel.hashtags or [],
                "url": reel.url,
                "views": reel.views,
                "video_play_count": reel.video_play_count
            }
            reels_data.append(reel_dict)
        
        return {"results": reels_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"릴스 데이터 읽기 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"릴스 데이터 읽기 중 오류가 발생했습니다: {str(e)}", 
            "code": "REELS_DATA_ERROR"
        })

@router.get("/influencer/files/analysis/user/{username}")
async def get_user_analysis_data(username: str, db: Session = Depends(get_db)):
    """사용자의 전체 분석 데이터를 반환합니다."""
    try:
        influencer_service = InfluencerService(db)
        
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")
        
        reels = influencer_service.get_reels_by_profile_id(profile.id)
        
        profile_data = {
            "username": profile.username,
            "fullName": profile.full_name,
            "followers": profile.followers,
            "following": profile.following,
            "bio": profile.bio,
            "profilePicUrl": profile.profile_pic_url,
            "account": profile.account,
            "posts_count": profile.posts_count,
            "avg_engagement": profile.avg_engagement,
            "category_name": profile.category_name,
            "profile_name": profile.profile_name,
            "email_address": profile.email_address,
            "is_business_account": profile.is_business_account,
            "is_professional_account": profile.is_professional_account,
            "is_verified": profile.is_verified
        }
        
        reels_data = []
        for reel in reels:
            reel_dict = {
                "id": reel.reel_id,
                "mediaType": reel.media_type,
                "mediaUrls": reel.media_urls or [],
                "caption": reel.caption,
                "timestamp": reel.timestamp,
                "user_posted": reel.user_posted,
                "profile_url": reel.profile_url,
                "date_posted": reel.date_posted,
                "num_comments": reel.num_comments,
                "likes": reel.likes,
                "photos": reel.photos or [],
                "content_type": reel.content_type,
                "description": reel.description,
                "hashtags": reel.hashtags or [],
                "url": reel.url,
                "views": reel.views,
                "video_play_count": reel.video_play_count
            }
            reels_data.append(reel_dict)
        
        analysis_data = {
            "username": username,
            "profile": profile_data,
            "reels": reels_data
        }
        
        return analysis_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 분석 데이터 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"사용자 분석 데이터 조회 중 오류가 발생했습니다: {str(e)}", 
            "code": "ANALYSIS_DATA_ERROR"
        })