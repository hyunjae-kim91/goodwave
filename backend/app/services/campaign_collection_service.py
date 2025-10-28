from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import statistics
import re

from app.db.models import (
    Campaign, CampaignURL, InfluencerProfile, InfluencerReel,
    CampaignInstagramReel, InstagramGradeThreshold
)
from app.services.grade_service import instagram_grade_service


class CampaignCollectionService:
    """Campaign data collection and processing service"""
    
    def __init__(self):
        pass
    
    def extract_username_from_url(self, url: str) -> Optional[str]:
        """Extract username from Instagram URL"""
        # Remove /reels/ or /posts/ or trailing slash
        clean_url = url.rstrip('/')
        if '/reels' in clean_url:
            clean_url = clean_url.replace('/reels', '')
        if '/posts' in clean_url:
            clean_url = clean_url.replace('/posts', '')
            
        # Extract username using regex
        match = re.search(r'instagram\.com/([^/?]+)', clean_url)
        if match:
            return match.group(1)
        return None
    
    def get_campaign_usernames(self, db: Session, campaign_id: int) -> List[str]:
        """Get all usernames for a campaign from its URLs"""
        campaign_urls = db.query(CampaignURL).filter(
            CampaignURL.campaign_id == campaign_id
        ).all()
        
        usernames = []
        for url_obj in campaign_urls:
            username = self.extract_username_from_url(url_obj.url)
            if username and username not in usernames:
                usernames.append(username)
        
        return usernames
    
    def calculate_average_view_count(self, view_counts: List[int]) -> float:
        """Calculate average of median 20 from 24 reels (excluding top 2 and bottom 2)"""
        if len(view_counts) < 4:
            # If less than 4 reels, return average of all
            return sum(view_counts) / len(view_counts) if view_counts else 0
        
        # Sort view counts
        sorted_counts = sorted(view_counts)
        
        # If we have 24 or more, take median 20 (exclude top 2 and bottom 2)
        if len(sorted_counts) >= 24:
            median_20 = sorted_counts[2:22]  # Remove top 2 and bottom 2
        else:
            # For fewer than 24, remove top and bottom 1
            median_20 = sorted_counts[1:-1] if len(sorted_counts) > 2 else sorted_counts
        
        return sum(median_20) / len(median_20) if median_20 else 0
    
    def process_campaign_reels(self, db: Session, campaign_id: int, 
                              collection_date: datetime = None) -> Dict[str, Any]:
        """Process collected reels for a campaign and assign grades"""
        if collection_date is None:
            collection_date = datetime.now()
        
        # Get campaign info
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"success": False, "message": "Campaign not found"}
        
        # Get usernames for this campaign
        usernames = self.get_campaign_usernames(db, campaign_id)
        if not usernames:
            return {"success": False, "message": "No usernames found for campaign"}
        
        results = []
        total_processed = 0
        
        for username in usernames:
            # Get influencer profile
            profile = db.query(InfluencerProfile).filter(
                InfluencerProfile.username == username
            ).first()
            
            if not profile:
                print(f"No profile found for username: {username}")
                continue
            
            # Get latest 24 reels for this profile
            reels = db.query(InfluencerReel).filter(
                InfluencerReel.profile_id == profile.id
            ).order_by(InfluencerReel.timestamp.desc()).limit(24).all()
            
            if not reels:
                print(f"No reels found for username: {username}")
                continue
            
            # Calculate average view count
            view_counts = [reel.views for reel in reels if reel.views]
            if not view_counts:
                print(f"No view counts found for username: {username}")
                continue
            
            avg_view_count = self.calculate_average_view_count(view_counts)
            
            # Get grade based on average view count
            grade = instagram_grade_service.get_grade_for_average(db, avg_view_count)
            
            # Store each reel as campaign reel data (commit individually)
            for reel in reels:
                try:
                    # Check if this reel already exists for this campaign
                    existing = db.query(CampaignInstagramReel).filter(
                        CampaignInstagramReel.campaign_id == campaign_id,
                        CampaignInstagramReel.reel_id == reel.reel_id
                    ).first()
                    
                    if existing:
                        # Update existing record
                        existing.video_view_count = reel.views or 0
                        existing.grade = grade or "등급 없음"
                        existing.collection_date = collection_date
                        existing.subscription_motivation = reel.subscription_motivation
                        existing.category = reel.category
                        existing.posted_at = reel.timestamp
                        db.commit()
                        print(f"Updated existing reel: {reel.reel_id}")
                    else:
                        # Create new campaign reel record
                        campaign_reel = CampaignInstagramReel(
                            campaign_id=campaign_id,
                            campaign_url=f"https://www.instagram.com/{username}/",
                            reel_id=reel.reel_id,
                            username=username,
                            display_name=profile.full_name,
                            follower_count=profile.followers,
                            thumbnail_url=reel.media_urls[0] if reel.media_urls else None,
                            s3_thumbnail_url=None,  # Would need to process if needed
                            video_view_count=reel.views or 0,
                            subscription_motivation=reel.subscription_motivation,
                            category=reel.category,
                            grade=grade or "등급 없음",
                            product=campaign.product,
                            posted_at=reel.timestamp,
                            collection_date=collection_date
                        )
                        db.add(campaign_reel)
                        db.commit()
                        total_processed += 1
                        print(f"Added new reel: {reel.reel_id}")
                        
                except Exception as e:
                    print(f"Error processing reel {reel.reel_id}: {str(e)}")
                    db.rollback()
                    continue
            
            results.append({
                "username": username,
                "reels_count": len(reels),
                "view_counts": view_counts,
                "average_view_count": avg_view_count,
                "grade": grade or "등급 없음"
            })
        
        # Changes were committed individually
        print(f"Successfully processed {total_processed} new reels")
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "processed_users": len(results),
            "total_reels_processed": total_processed,
            "collection_date": collection_date.isoformat(),
            "results": results
        }
    
    def get_campaign_reel_data(self, db: Session, campaign_id: int) -> List[Dict[str, Any]]:
        """Get campaign reel data for reporting"""
        campaign_reels = db.query(CampaignInstagramReel).filter(
            CampaignInstagramReel.campaign_id == campaign_id
        ).order_by(CampaignInstagramReel.collection_date.desc()).all()
        
        results = []
        for reel in campaign_reels:
            results.append({
                "reel_id": reel.reel_id,
                "username": reel.username,
                "display_name": reel.display_name,
                "follower_count": reel.follower_count,
                "video_view_count": reel.video_view_count,
                "grade": reel.grade,
                "subscription_motivation": reel.subscription_motivation,
                "category": reel.category,
                "product": reel.product,
                "posted_at": reel.posted_at.isoformat() if reel.posted_at else None,
                "collection_date": reel.collection_date.isoformat() if reel.collection_date else None
            })
        
        return results


campaign_collection_service = CampaignCollectionService()