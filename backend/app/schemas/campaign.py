from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import List, Optional

class CampaignURLCreate(BaseModel):
    url: str
    channel: str  # instagram_post, instagram_reel, blog

class CampaignURLResponse(BaseModel):
    id: int
    url: str
    channel: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class CampaignCreate(BaseModel):
    name: str
    campaign_type: str
    budget: float
    start_date: datetime
    end_date: datetime
    product: str
    urls: List[CampaignURLCreate]

class CampaignResponse(BaseModel):
    id: int
    name: str
    campaign_type: str
    budget: float
    start_date: datetime
    end_date: datetime
    product: str
    created_at: datetime
    updated_at: datetime
    campaign_urls: Optional[List[CampaignURLResponse]] = []
    
    class Config:
        from_attributes = True


class CampaignURLUpdate(BaseModel):
    id: int
    url: str
    channel: Optional[str] = None

    @model_validator(mode="after")
    def validate_url(self) -> "CampaignURLUpdate":
        normalized = self.url.strip() if self.url else ""
        if not normalized:
            raise ValueError("URL은 비워둘 수 없습니다.")
        self.url = normalized
        if self.channel is not None:
            self.channel = self.channel.strip()
        return self


class CampaignUpdate(BaseModel):
    campaign_type: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    product: Optional[str] = None
    urls: Optional[List[CampaignURLUpdate]] = None

    @model_validator(mode="after")
    def validate_payload(self) -> "CampaignUpdate":
        has_urls = self.urls is not None
        if not any(
            value is not None
            for value in (
                self.campaign_type,
                self.budget,
                self.start_date,
                self.end_date,
                self.product,
                self.urls if has_urls else None,
            )
        ):
            raise ValueError("업데이트할 항목이 없습니다.")

        if has_urls and not self.urls:
            raise ValueError("업데이트할 캠페인 URL을 입력해주세요.")

        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("시작일은 종료일보다 이전이어야 합니다.")

        if self.product is not None:
            stripped = self.product.strip()
            if not stripped:
                raise ValueError("제품명은 비워둘 수 없습니다.")
            self.product = stripped

        return self

class InstagramPostResponse(BaseModel):
    id: int
    post_id: str
    username: str
    display_name: Optional[str]
    follower_count: Optional[int]
    s3_thumbnail_url: Optional[str]
    likes_count: int
    comments_count: int
    subscription_motivation: Optional[str]
    category: Optional[str]
    grade: Optional[str]
    posted_at: Optional[datetime]
    collected_at: datetime
    
    class Config:
        from_attributes = True

class InstagramReelResponse(BaseModel):
    id: int
    reel_id: str
    username: str
    display_name: Optional[str]
    follower_count: Optional[int]
    s3_thumbnail_url: Optional[str]
    video_view_count: int
    subscription_motivation: Optional[str]
    category: Optional[str]
    grade: Optional[str]
    posted_at: Optional[datetime]
    collected_at: datetime
    
    class Config:
        from_attributes = True

class BlogPostResponse(BaseModel):
    id: int
    url: str
    title: Optional[str]
    likes_count: int
    comments_count: int
    daily_visitors: int
    posted_at: Optional[datetime]
    collected_at: datetime
    
    class Config:
        from_attributes = True
