"""
통합 뷰를 위한 모델들
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class CampaignInstagramUnifiedView(Base):
    """캠페인 인스타그램 통합 뷰 모델"""
    __tablename__ = "campaign_instagram_unified_view"
    
    # Primary key는 reel_record_id를 사용 (view에서는 복합키 불가)
    reel_record_id = Column(Integer, primary_key=True)
    
    # 데이터 소스
    data_source = Column(String(50))  # 'campaign' or 'influencer'
    
    # 캠페인 정보
    campaign_id = Column(Integer)
    campaign_name = Column(String(255))
    campaign_product = Column(String(255))
    campaign_start_date = Column(DateTime)
    campaign_end_date = Column(DateTime)
    
    # 릴스 정보
    reel_id = Column(String(255))
    username = Column(String(255))
    display_name = Column(String(255))
    follower_count = Column(Integer)
    s3_thumbnail_url = Column(Text)
    video_view_count = Column(Integer)
    
    # 분석 정보
    subscription_motivation = Column(String(100))
    category = Column(String(100))
    grade = Column(String(50))
    
    # 날짜 정보
    posted_at = Column(DateTime)
    collection_date = Column(DateTime)
    campaign_url = Column(Text)
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.reel_record_id,
            'data_source': self.data_source,
            'campaign_id': self.campaign_id,
            'campaign_name': self.campaign_name,
            'campaign_product': self.campaign_product,
            'reel_id': self.reel_id,
            'username': self.username,
            'display_name': self.display_name,
            'follower_count': self.follower_count or 0,
            's3_thumbnail_url': self.s3_thumbnail_url,
            'video_view_count': self.video_view_count or 0,
            'subscription_motivation': self.subscription_motivation,
            'category': self.category,
            'grade': self.grade,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'collection_date': self.collection_date.isoformat() if self.collection_date else None,
            'campaign_url': self.campaign_url
        }