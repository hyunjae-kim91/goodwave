from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON, Date, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    campaign_type = Column(String(50), nullable=False)  # instagram_post, instagram_reel, blog
    budget = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    product = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    campaign_urls = relationship("CampaignURL", back_populates="campaign")
    collection_schedules = relationship("CollectionSchedule", back_populates="campaign")

class CampaignURL(Base):
    __tablename__ = "campaign_urls"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    url = Column(Text, nullable=False)
    channel = Column(String(50), nullable=False)  # instagram_post, instagram_reel, blog
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    campaign = relationship("Campaign", back_populates="campaign_urls")

class CollectionSchedule(Base):
    __tablename__ = "collection_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    channel = Column(String(50), nullable=False)
    campaign_url = Column(Text, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    campaign = relationship("Campaign", back_populates="collection_schedules")

class InstagramPost(Base):
    __tablename__ = "instagram_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), nullable=False)
    display_name = Column(String(255))
    follower_count = Column(Integer)
    thumbnail_url = Column(Text)
    s3_thumbnail_url = Column(Text)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    subscription_motivation = Column(String(100))  # OpenAI classification
    category = Column(String(100))  # OpenAI classification
    grade = Column(String(50))  # 등급 또는 안내 문구
    posted_at = Column(DateTime)
    collected_at = Column(DateTime, default=func.now())

class InstagramReel(Base):
    __tablename__ = "instagram_reels"
    
    id = Column(Integer, primary_key=True, index=True)
    reel_id = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), nullable=False)
    display_name = Column(String(255))
    follower_count = Column(Integer)
    thumbnail_url = Column(Text)
    s3_thumbnail_url = Column(Text)
    video_view_count = Column(Integer, default=0)
    subscription_motivation = Column(String(100))  # OpenAI classification
    category = Column(String(100))  # OpenAI classification
    grade = Column(String(50))  # 등급 또는 안내 문구
    posted_at = Column(DateTime)
    collected_at = Column(DateTime, default=func.now())

class BlogPost(Base):
    __tablename__ = "blog_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    title = Column(Text)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    daily_visitors = Column(Integer, default=0)
    posted_at = Column(DateTime)
    collected_at = Column(DateTime, default=func.now())

class BlogRanking(Base):
    __tablename__ = "blog_rankings"
    
    id = Column(Integer, primary_key=True, index=True)
    blog_url = Column(Text, nullable=False)
    keyword = Column(String(255), nullable=False)
    ranking = Column(Integer, nullable=False)
    collection_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())

# Campaign collection tables
class CampaignInstagramPost(Base):
    __tablename__ = "campaign_instagram_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    campaign_url = Column(Text, nullable=False)
    post_id = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    display_name = Column(String(255))
    follower_count = Column(Integer)
    thumbnail_url = Column(Text)
    s3_thumbnail_url = Column(Text)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    subscription_motivation = Column(String(100))
    category = Column(String(100))
    grade = Column(String(50))
    product = Column(String(255))
    posted_at = Column(DateTime)
    collection_date = Column(DateTime, nullable=False)

class CampaignInstagramReel(Base):
    __tablename__ = "campaign_instagram_reels"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    campaign_url = Column(Text, nullable=False)
    reel_id = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    display_name = Column(String(255))
    follower_count = Column(Integer)
    thumbnail_url = Column(Text)
    s3_thumbnail_url = Column(Text)
    video_view_count = Column(Integer, default=0)
    subscription_motivation = Column(String(100))
    category = Column(String(100))
    grade = Column(String(50))
    product = Column(String(255))
    posted_at = Column(DateTime)
    collection_date = Column(DateTime, nullable=False)

class CampaignBlog(Base):
    __tablename__ = "campaign_blogs"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    campaign_url = Column(Text, nullable=False)
    username = Column(String(255))
    title = Column(Text)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    daily_visitors = Column(Integer, default=0)
    # NOTE: keyword/ranking columns kept for backward compatibility but rankings are stored in campaign_blog_rankings
    keyword = Column(String(255))
    ranking = Column(Integer)
    product = Column(String(255))
    posted_at = Column(DateTime)
    collection_date = Column(DateTime, nullable=False)

    rankings = relationship(
        "CampaignBlogRanking",
        back_populates="campaign_blog",
        cascade="all, delete-orphan",
    )


class CampaignBlogRanking(Base):
    __tablename__ = "campaign_blog_rankings"

    id = Column(Integer, primary_key=True, index=True)
    campaign_blog_id = Column(Integer, ForeignKey("campaign_blogs.id", ondelete="CASCADE"), nullable=False)
    keyword = Column(String(255), nullable=False)
    ranking = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    campaign_blog = relationship("CampaignBlog", back_populates="rankings")

# Influencer Analysis Models (goodwave_web features)
class InfluencerProfile(Base):
    __tablename__ = "influencer_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    followers = Column(Integer)
    following = Column(Integer)
    bio = Column(Text)
    profile_pic_url = Column(Text)
    account = Column(String(255))
    posts_count = Column(Integer)
    avg_engagement = Column(Float)
    category_name = Column(String(255))
    profile_name = Column(String(255))
    email_address = Column(String(255))
    is_business_account = Column(Boolean, default=False)
    is_professional_account = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    influencer_posts = relationship("InfluencerPost", back_populates="profile")
    influencer_reels = relationship("InfluencerReel", back_populates="profile")
    analysis_results = relationship("InfluencerAnalysis", back_populates="profile")
    classification_overrides = relationship(
        "InfluencerClassificationOverride", back_populates="profile"
    )

class InfluencerPost(Base):
    __tablename__ = "influencer_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("influencer_profiles.id"), nullable=False)
    post_id = Column(String(255), unique=True, nullable=False)
    media_type = Column(String(50))
    media_urls = Column(JSON)  # List of URLs
    caption = Column(Text)
    timestamp = Column(DateTime)
    user_posted = Column(String(255))
    profile_url = Column(Text)
    date_posted = Column(String(255))
    num_comments = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    photos = Column(JSON)  # List of photo URLs
    content_type = Column(String(100))
    description = Column(Text)
    hashtags = Column(JSON)  # List of hashtags
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    profile = relationship("InfluencerProfile", back_populates="influencer_posts")

class InfluencerReel(Base):
    __tablename__ = "influencer_reels"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("influencer_profiles.id"), nullable=False)
    reel_id = Column(String(255), unique=True, nullable=False)
    media_type = Column(String(50), default="VIDEO")
    media_urls = Column(JSON)  # List of URLs
    caption = Column(Text)
    timestamp = Column(DateTime)
    user_posted = Column(String(255))
    profile_url = Column(Text)
    date_posted = Column(String(255))
    num_comments = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    photos = Column(JSON)
    content_type = Column(String(100), default="reel")
    description = Column(Text)
    hashtags = Column(JSON)
    url = Column(Text)
    views = Column(Integer, default=0)
    video_play_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    
    # Subscription motivation classification results
    subscription_motivation = Column(String(100))
    subscription_motivation_confidence = Column(Float)
    subscription_motivation_reasoning = Column(Text)
    subscription_motivation_image_url = Column(Text)
    subscription_motivation_raw_response = Column(JSON)
    subscription_motivation_error = Column(Text)
    subscription_motivation_processed_at = Column(DateTime)
    subscription_motivation_job_id = Column(Integer, ForeignKey("classification_jobs.id"))

    # Category classification results
    category = Column(String(100))
    category_confidence = Column(Float)
    category_reasoning = Column(Text)
    category_image_url = Column(Text)
    category_raw_response = Column(JSON)
    category_error = Column(Text)
    category_processed_at = Column(DateTime)
    category_job_id = Column(Integer, ForeignKey("classification_jobs.id"))
    
    # Relationships
    profile = relationship("InfluencerProfile", back_populates="influencer_reels")
    analysis_results = relationship("InfluencerAnalysis", back_populates="reel")
    classification_summaries = relationship("InfluencerClassificationSummary", back_populates="reel")
    reel_classifications = relationship("ReelClassification", back_populates="reel")

class InfluencerAnalysis(Base):
    __tablename__ = "influencer_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("influencer_profiles.id"), nullable=False)
    reel_id = Column(Integer, ForeignKey("influencer_reels.id"), nullable=True)
    analysis_type = Column(String(100), nullable=False)  # subscription_motivation, category, combined
    analysis_result = Column(JSON)  # Stores the analysis results
    prompt_used = Column(Text)  # The prompt used for analysis
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    profile = relationship("InfluencerProfile", back_populates="analysis_results")
    reel = relationship("InfluencerReel", back_populates="analysis_results")

class InfluencerClassificationSummary(Base):
    __tablename__ = "influencer_classification_summaries"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False)
    reel_id = Column(Integer, ForeignKey("influencer_reels.id"), nullable=False)
    profile_id = Column(Integer, ForeignKey("influencer_profiles.id"), nullable=False)
    classification_job_id = Column(Integer, ForeignKey("classification_jobs.id"))
    classification_type = Column(String(50), nullable=False, default="combined")
    primary_classification = Column(String(100), nullable=False, default="")
    primary_percentage = Column(Float, nullable=False, default=0.0)
    secondary_classification = Column(String(100))
    secondary_percentage = Column(Float)
    classification_distribution = Column(JSON)
    total_reels_processed = Column(Integer, nullable=False, default=0)
    successful_classifications = Column(Integer, nullable=False, default=0)
    failed_classifications = Column(Integer)
    average_confidence_score = Column(Float)
    processing_metadata = Column(JSON)
    motivation = Column(String(100))
    motivation_confidence = Column(Float)
    motivation_reasoning = Column(Text)
    category = Column(String(100))
    category_confidence = Column(Float)
    category_reasoning = Column(Text)
    raw_response = Column(JSON)
    error = Column(Text)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    reel = relationship("InfluencerReel", back_populates="classification_summaries")
    profile = relationship("InfluencerProfile")
    classification_job = relationship("ClassificationJob")


class InfluencerClassificationOverride(Base):
    __tablename__ = "influencer_classification_overrides"
    __table_args__ = (
        UniqueConstraint("profile_id", "classification_type", name="uq_override_profile_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("influencer_profiles.id"), nullable=False)
    classification_type = Column(String(50), nullable=False)
    primary_classification = Column(String(100), nullable=False)
    primary_percentage = Column(Float)
    secondary_classification = Column(String(100))
    secondary_percentage = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    profile = relationship("InfluencerProfile", back_populates="classification_overrides")


class ReelClassification(Base):
    __tablename__ = "reel_classifications"

    id = Column(Integer, primary_key=True, index=True)
    reel_id = Column(Integer, ForeignKey("influencer_reels.id"), nullable=False)
    classification_job_id = Column(Integer, ForeignKey("classification_jobs.id"), nullable=False)
    classification_type = Column(String(50), nullable=False)
    classification_result = Column(String(100), nullable=False)
    confidence_score = Column(Float)
    reasoning = Column(Text)
    image_url = Column(Text)
    raw_response = Column(JSON)
    error_message = Column(Text)
    processed_at = Column(DateTime, default=func.now())

    reel = relationship("InfluencerReel", back_populates="reel_classifications")
    classification_job = relationship("ClassificationJob")


class InstagramGradeThreshold(Base):
    __tablename__ = "instagram_grade_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    grade_name = Column(String(50), unique=True, nullable=False)
    min_view_count = Column(Integer, nullable=False)
    max_view_count = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class SystemPrompt(Base):
    __tablename__ = "system_prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_type = Column(String(100), nullable=False)  # system, subscription_motivation, category
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class BatchIngestSession(Base):
    __tablename__ = "batch_ingest_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False)
    total_requested = Column(Integer, nullable=False)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    summary = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    
    # Relationships
    session_results = relationship("BatchSessionResult", back_populates="session")

class BatchSessionResult(Base):
    __tablename__ = "batch_session_results"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("batch_ingest_sessions.session_id"), nullable=False)
    url = Column(Text, nullable=False)
    success = Column(Boolean, nullable=False)
    username = Column(String(255))
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    session = relationship("BatchIngestSession", back_populates="session_results")

class CollectionJob(Base):
    __tablename__ = "collection_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), unique=True, nullable=False)  # UUID
    url = Column(Text, nullable=False)
    username = Column(String(255))
    collect_profile = Column(Boolean, default=True)
    collect_posts = Column(Boolean, default=True)
    collect_reels = Column(Boolean, default=True)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    priority = Column(Integer, default=0)  # 높은 숫자가 우선순위 높음
    
    # 진행상황 추적
    profile_status = Column(String(50), default="pending")  # pending, processing, completed, failed, skipped
    posts_status = Column(String(50), default="pending")
    reels_status = Column(String(50), default="pending")
    
    # 결과 카운트
    profile_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    reels_count = Column(Integer, default=0)
    
    # 메타데이터
    error_message = Column(Text)
    job_metadata = Column(JSON)  # 추가 정보 저장
    
    # 타임스탬프
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "url": self.url,
            "username": self.username,
            "collect_profile": self.collect_profile,
            "collect_posts": self.collect_posts,
            "collect_reels": self.collect_reels,
            "status": self.status,
            "priority": self.priority,
            "profile_status": self.profile_status,
            "posts_status": self.posts_status,
            "reels_status": self.reels_status,
            "profile_count": self.profile_count,
            "posts_count": self.posts_count,
            "reels_count": self.reels_count,
            "error_message": self.error_message,
            "job_metadata": self.job_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

class ClassificationJob(Base):
    __tablename__ = "classification_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), nullable=False)
    classification_type = Column(String(50), nullable=False, default="combined")
    status = Column(String(50), nullable=False, default="pending")  # pending, processing, completed, failed
    priority = Column(Integer, default=0)
    error_message = Column(Text)
    job_metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "username": self.username,
            "classification_type": self.classification_type,
            "status": self.status,
            "priority": self.priority,
            "error_message": self.error_message,
            "job_metadata": self.job_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
