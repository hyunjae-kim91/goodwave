from pydantic import BaseModel, validator, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re

class IngestRequest(BaseModel):
    instagramUrls: List[str]
    options: Optional[Dict[str, bool]] = None
    
    @validator('instagramUrls')
    def validate_instagram_urls(cls, v):
        if not v or len(v) == 0:
            raise ValueError('최소 1개의 Instagram URL이 필요합니다')
        
        if len(v) > 100:
            raise ValueError('최대 100개의 URL만 처리할 수 있습니다')
        
        instagram_patterns = [
            r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?',
            r'https?://(?:www\.)?ig\.me/[a-zA-Z0-9_.]+/?',
            r'https?://(?:www\.)?instagram\.com/reel/[a-zA-Z0-9_-]+/?',
            r'https?://(?:www\.)?instagram\.com/p/[a-zA-Z0-9_-]+/?'
        ]
        
        for i, url in enumerate(v):
            if not url.strip():
                raise ValueError(f'빈 URL은 허용되지 않습니다 (위치: {i+1}번째)')
            
            if not any(re.match(pattern, url.strip()) for pattern in instagram_patterns):
                raise ValueError(f'유효하지 않은 Instagram URL: {url} (위치: {i+1}번째)')
        
        return v

class Profile(BaseModel):
    username: str
    fullName: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    bio: Optional[str] = None
    profilePicUrl: Optional[str] = None
    account: Optional[str] = None
    posts_count: Optional[int] = None
    avg_engagement: Optional[float] = None
    category_name: Optional[str] = None
    profile_name: Optional[str] = None
    email_address: Optional[str] = None
    is_business_account: Optional[bool] = None
    is_professional_account: Optional[bool] = None
    is_verified: Optional[bool] = None

class Post(BaseModel):
    id: Optional[str] = ""
    mediaType: Optional[str] = "IMAGE"
    mediaUrls: Optional[List[str]] = []
    caption: Optional[str] = None
    timestamp: Optional[datetime] = None
    user_posted: Optional[str] = None
    profile_url: Optional[str] = None
    date_posted: Optional[str] = None
    num_comments: Optional[int] = None
    likes: Optional[int] = None
    photos: Optional[List[str]] = None
    content_type: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None

    class Config:
        extra = "ignore"  # 추가 필드 무시
        validate_assignment = False  # 할당 시 검증 비활성화

class IngestResponse(BaseModel):
    sessionId: str
    profile: Profile
    posts: List[Post]

class ErrorResponse(BaseModel):
    error: str
    code: Optional[str] = None

class ProfileResult(BaseModel):
    url: str
    success: bool
    username: Optional[str] = None
    profile: Optional[Profile] = None
    posts: List[Post] = []
    reels: List[Post] = []
    error: Optional[str] = None
    status: Optional[str] = None  # 수집 상태: "success", "api_error", "not_implemented", "processing_error"

class BatchIngestResponse(BaseModel):
    sessionId: str
    totalRequested: int
    successCount: int
    failureCount: int
    results: List[ProfileResult]
    summary: Dict[str, Any]

class PostsRequest(BaseModel):
    postUrls: List[str]
    
    @validator('postUrls')
    def validate_post_urls(cls, v):
        if not v or len(v) == 0:
            raise ValueError('최소 1개의 게시물 URL이 필요합니다')
        
        if len(v) > 50:
            raise ValueError('최대 50개의 게시물 URL만 처리할 수 있습니다')
        
        post_patterns = [
            r'https?://(?:www\.)?instagram\.com/p/[a-zA-Z0-9_-]+/?',
            r'https?://(?:www\.)?instagram\.com/reel/[a-zA-Z0-9_-]+/?',
            r'https?://(?:www\.)?ig\.me/p/[a-zA-Z0-9_-]+/?'
        ]
        
        for url in v:
            if not url.strip():
                raise ValueError('빈 URL은 허용되지 않습니다')
            
            if not any(re.match(pattern, url.strip()) for pattern in post_patterns):
                raise ValueError(f'유효하지 않은 Instagram 게시물 URL: {url}')
        
        return v

class ImageDownloadRequest(BaseModel):
    username: str

class ImageDownloadResponse(BaseModel):
    success: bool
    message: str
    downloaded_count: int
    total_count: int
    images_path: str

class DeleteUsersRequest(BaseModel):
    usernames: List[str]

class ClassificationRequest(BaseModel):
    username: str
    classification_type: str = "combined"  # "subscription_motivation", "category", "combined"
    prompt_type: Optional[str] = None

class ClassificationResponse(BaseModel):
    success: bool
    message: str
    username: str
    classification_type: str
    result: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None

class PromptUpdateRequest(BaseModel):
    prompt_type: Optional[str] = None  # "system", "subscription_motivation", "category"
    content: str

class PromptResponse(BaseModel):
    success: bool
    message: str
    prompt_type: str
    content: str


class ClassificationOverridePayload(BaseModel):
    primary_label: str
    primary_percentage: Optional[float] = None
    secondary_label: Optional[str] = None
    secondary_percentage: Optional[float] = None

    @validator('primary_label')
    def validate_primary_label(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError('1순위 분류명을 입력해주세요.')
        return value.strip()

    @validator('secondary_label', pre=True, always=True)
    def normalize_secondary_label(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @validator('primary_percentage', 'secondary_percentage')
    def validate_percentage(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError('퍼센트 값은 0과 100 사이여야 합니다.')
        return value

    @model_validator(mode="after")
    def validate_secondary_pair(cls, model: "ClassificationOverridePayload") -> "ClassificationOverridePayload":
        if model.secondary_label and model.secondary_percentage is None:
            raise ValueError('2순위 분류의 퍼센트 값을 입력해주세요.')
        if model.secondary_percentage is not None and not model.secondary_label:
            raise ValueError('2순위 분류명을 입력해주세요.')
        return model


class ClassificationOverrideUpdateRequest(BaseModel):
    subscription_motivation: Optional[ClassificationOverridePayload] = None
    category: Optional[ClassificationOverridePayload] = None

    @validator('subscription_motivation', 'category', pre=True, always=True)
    def normalize_empty_payload(cls, value):
        if isinstance(value, dict) and not value:
            return None
        return value

    @model_validator(mode="after")
    def ensure_any_payload(cls, model: "ClassificationOverrideUpdateRequest") -> "ClassificationOverrideUpdateRequest":
        if not model.subscription_motivation and not model.category:
            raise ValueError('수정할 분류 데이터가 없습니다.')
        return model
