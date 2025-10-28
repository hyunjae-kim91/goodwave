import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignURLCreate,
    CampaignUpdate,
)
from app.services.scheduler_service import SchedulerService
from app.services.campaign_collection_service import campaign_collection_service
from app.services.campaign_reel_collection_service import CampaignReelCollectionService
import requests
import re

router = APIRouter()
logger = logging.getLogger(__name__)

KST_OFFSET = timedelta(hours=9)


async def _queue_campaign_automation(campaign_id: int) -> None:
    """캠페인 자동화를 큐에 추가 (비블로킹)"""
    try:
        # 짧은 지연 후 백그라운드에서 처리
        await asyncio.sleep(1)
        
        # 새로운 DB 세션 생성 (원래 세션과 분리)
        from app.db.database import get_db
        db = next(get_db())
        
        try:
            # 캠페인 정보 조회
            campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found for automation")
                return
            
            # 캠페인 URL에서 Instagram URL 추출
            campaign_urls = db.query(models.CampaignURL).filter(
                models.CampaignURL.campaign_id == campaign_id
            ).all()
            
            instagram_urls = []
            for url_obj in campaign_urls:
                if 'instagram.com' in url_obj.url:
                    # Extract username and create profile URL
                    match = re.search(r'instagram\.com/([^/?]+)', url_obj.url)
                    if match:
                        username = match.group(1)
                        profile_url = f"https://www.instagram.com/{username}/"
                        instagram_urls.append(profile_url)
            
            if instagram_urls:
                logger.info(f"Queueing data collection for campaign {campaign_id}: {len(instagram_urls)} URLs")
                
                # 인플루언서 데이터 수집 큐에 추가
                response = requests.post(
                    "http://localhost:8000/api/influencer/ingest/batch",
                    json={
                        "instagramUrls": instagram_urls,
                        "options": {
                            "collectProfile": True,
                            "collectPosts": False,
                            "collectReels": True
                        }
                    },
                    timeout=5  # 짧은 타임아웃
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Data collection queued: {result.get('message')}")
                    
                    # 캠페인 처리도 큐에 스케줄
                    asyncio.create_task(_queue_campaign_processing(campaign_id, delay_minutes=3))
                else:
                    logger.error(f"Failed to queue data collection: {response.status_code}")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in campaign automation queueing: {str(e)}")


async def _queue_campaign_processing(campaign_id: int, delay_minutes: int = 3) -> None:
    """캠페인 처리를 큐에 스케줄링"""
    try:
        # 데이터 수집 완료 대기
        await asyncio.sleep(delay_minutes * 60)
        
        logger.info(f"Queueing campaign processing for campaign {campaign_id}")
        
        # 캠페인 처리 API 호출 (타임아웃 짧게)
        response = requests.post(
            f"http://localhost:8000/api/campaigns/{campaign_id}/process-reels",
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Campaign processing queued successfully: {result.get('message', 'Success')}")
        else:
            logger.warning(f"Campaign processing queue returned {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error queueing campaign processing: {str(e)}")


async def _process_reel_collection_jobs_async(campaign_id: int) -> None:
    """캠페인의 릴스 수집 작업을 백그라운드에서 처리"""
    try:
        logger.info(f"🎬 캠페인 {campaign_id} 릴스 수집 작업 시작")
        
        # 짧은 지연 후 처리 (다른 작업들이 완료되길 기다림)
        await asyncio.sleep(2)
        
        collection_service = CampaignReelCollectionService()
        
        # 캠페인의 대기 중인 릴스 수집 작업들을 처리
        processed_count = collection_service.process_pending_jobs(limit=10, campaign_id=campaign_id)
        
        logger.info(f"🎬 캠페인 {campaign_id} 릴스 수집 완료: {processed_count}개 작업 처리됨")
        
        if processed_count > 0:
            # 수집 완료 후 약간의 지연 후 추가 처리 (인플루언서 프로필 수집 등)
            await asyncio.sleep(5)
            logger.info(f"🎬 캠페인 {campaign_id} 후속 처리 완료 대기...")
        
    except Exception as e:
        logger.error(f"Error processing reel collection jobs for campaign {campaign_id}: {str(e)}")


async def _run_simple_immediate_collection(campaign_id: int) -> None:
    """캠페인 등록 시 즉시 간단 수집"""
    try:
        logger.info(f"🚀 캠페인 {campaign_id} 즉시 수집 시작")
        
        # 새로운 DB 세션 생성
        from app.db.database import get_db
        db = next(get_db())
        
        try:
            # 캠페인 정보 조회
            campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return
            
            # 스케줄러 서비스를 통한 즉시 수집
            from app.services.scheduler_service import SchedulerService
            scheduler = SchedulerService()
            
            # 캠페인의 스케줄들 가져오기
            schedules = db.query(models.CollectionSchedule).filter(
                models.CollectionSchedule.campaign_id == campaign_id,
                models.CollectionSchedule.is_active == True
            ).all()
            
            logger.info(f"📋 {len(schedules)}개 스케줄 즉시 실행")
            
            from datetime import datetime
            collection_date = datetime.now()
            
            for schedule in schedules:
                try:
                    logger.info(f"🔄 스케줄 처리: {schedule.campaign_url}")
                    await scheduler._process_schedule(schedule)
                except Exception as e:
                    logger.error(f"스케줄 처리 실패 {schedule.campaign_url}: {str(e)}")
                    continue
            
            logger.info(f"🎉 캠페인 {campaign_id} 즉시 수집 완료")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in simple immediate collection: {str(e)}")


@router.post("/", response_model=CampaignResponse)
async def create_campaign(campaign_data: CampaignCreate, db: Session = Depends(get_db)):
    db_campaign = models.Campaign(
        name=campaign_data.name,
        campaign_type=campaign_data.campaign_type,
        budget=campaign_data.budget,
        start_date=campaign_data.start_date,
        end_date=campaign_data.end_date,
        product=campaign_data.product,
    )
    db.add(db_campaign)
    db.flush()

    immediate_schedule_ids: List[int] = []
    now_kst = datetime.utcnow() + KST_OFFSET

    for url_data in campaign_data.urls:
        db_url = models.CampaignURL(
            campaign_id=db_campaign.id,
            url=url_data.url,
            channel=url_data.channel,
        )
        db.add(db_url)

        db_schedule = models.CollectionSchedule(
            campaign_id=db_campaign.id,
            channel=url_data.channel,
            campaign_url=url_data.url,
            start_date=campaign_data.start_date,
            end_date=campaign_data.end_date,
        )
        db.add(db_schedule)
        db.flush()

        if (
            db_schedule.is_active
            and db_schedule.start_date <= now_kst
            and db_schedule.end_date >= now_kst
        ):
            immediate_schedule_ids.append(db_schedule.id)

    db.commit()
    db.refresh(db_campaign)

    # 즉시 수집 (간단한 방식) - 릴스 URL이 있으면 캠페인 타입과 관계없이 처리
    if any(url_data.channel == 'instagram_reel' and 'instagram.com/reel/' in url_data.url for url_data in campaign_data.urls):
        asyncio.create_task(_run_simple_immediate_collection(db_campaign.id))
    
    # 릴스 URL들을 단일 릴스 수집 큐에 추가
    reel_urls = [url_data.url for url_data in campaign_data.urls 
                if url_data.channel == 'instagram_reel' and 'instagram.com/reel/' in url_data.url]
    
    if reel_urls:
        try:
            collection_service = CampaignReelCollectionService()
            collection_service.add_reel_collection_jobs(db_campaign.id, reel_urls, check_existing_data=False)
            logger.info(f"Added {len(reel_urls)} reel collection jobs for campaign {db_campaign.id}")
            
            # 즉시 릴스 수집 작업 시작 (백그라운드)
            try:
                asyncio.create_task(_process_reel_collection_jobs_async(db_campaign.id))
                logger.info(f"Background processing task created for campaign {db_campaign.id}")
            except Exception as e:
                logger.error(f"Failed to create background task: {str(e)}")
                # 백그라운드 작업 실패 시 동기적으로 처리
                try:
                    collection_service = CampaignReelCollectionService()
                    processed_count = collection_service.process_pending_jobs(limit=10, campaign_id=db_campaign.id)
                    logger.info(f"Synchronously processed {processed_count} jobs for campaign {db_campaign.id}")
                except Exception as sync_e:
                    logger.error(f"Synchronous processing also failed: {str(sync_e)}")
        except Exception as e:
            logger.error(f"Error adding reel collection jobs: {str(e)}")

    return db_campaign

@router.get("/", response_model=List[CampaignResponse])
async def get_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(models.Campaign).all()
    return campaigns

@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(models.Campaign)
        .filter(models.Campaign.id == campaign_id)
        .first()
    )

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    updated = False
    if campaign_data.campaign_type is not None:
        campaign.campaign_type = campaign_data.campaign_type
        updated = True
    if campaign_data.budget is not None:
        campaign.budget = campaign_data.budget
        updated = True

    start_date_changed = False
    if campaign_data.start_date is not None:
        campaign.start_date = campaign_data.start_date
        updated = True
        start_date_changed = True

    end_date_changed = False
    if campaign_data.end_date is not None:
        campaign.end_date = campaign_data.end_date
        updated = True
        end_date_changed = True

    if campaign_data.product is not None:
        campaign.product = campaign_data.product.strip()
        updated = True

    if campaign_data.urls is not None:
        existing_urls = {url.id: url for url in campaign.campaign_urls}
        processed_ids = set()

        for url_update in campaign_data.urls:
            db_url = existing_urls.get(url_update.id)
            if not db_url:
                raise HTTPException(
                    status_code=400,
                    detail=f"Campaign URL(ID={url_update.id})을 찾을 수 없습니다.",
                )

            old_url = db_url.url
            old_channel = db_url.channel
            new_url = url_update.url

            if url_update.channel and url_update.channel != db_url.channel:
                db_url.channel = url_update.channel
                updated = True

            if new_url != old_url:
                db_url.url = new_url
                updated = True

                schedules = (
                    db.query(models.CollectionSchedule)
                    .filter(
                        models.CollectionSchedule.campaign_id == campaign.id,
                        models.CollectionSchedule.campaign_url == old_url,
                        models.CollectionSchedule.channel == old_channel,
                    )
                    .all()
                )
                for schedule in schedules:
                    schedule.campaign_url = new_url
                    schedule.channel = db_url.channel

                db.query(models.CampaignInstagramPost).filter(
                    models.CampaignInstagramPost.campaign_id == campaign.id,
                    models.CampaignInstagramPost.campaign_url == old_url,
                ).update({models.CampaignInstagramPost.campaign_url: new_url}, synchronize_session=False)

                db.query(models.CampaignInstagramReel).filter(
                    models.CampaignInstagramReel.campaign_id == campaign.id,
                    models.CampaignInstagramReel.campaign_url == old_url,
                ).update({models.CampaignInstagramReel.campaign_url: new_url}, synchronize_session=False)

                db.query(models.CampaignBlog).filter(
                    models.CampaignBlog.campaign_id == campaign.id,
                    models.CampaignBlog.campaign_url == old_url,
                ).update({models.CampaignBlog.campaign_url: new_url}, synchronize_session=False)

            processed_ids.add(db_url.id)

        # 현재는 URL 삭제를 지원하지 않지만, 추후 확장을 위해 미처리 ID를 확인
        remaining_ids = set(existing_urls.keys()) - processed_ids
        if remaining_ids:
            logger.debug("미처리된 캠페인 URL ID: %s", remaining_ids)

    if not updated:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    if campaign.start_date >= campaign.end_date:
        raise HTTPException(status_code=400, detail="시작일은 종료일보다 이전이어야 합니다.")

    if start_date_changed or end_date_changed:
        schedules = (
            db.query(models.CollectionSchedule)
            .filter(models.CollectionSchedule.campaign_id == campaign.id)
            .all()
        )
        for schedule in schedules:
            schedule.start_date = campaign.start_date
            schedule.end_date = campaign.end_date

    db.commit()
    db.refresh(campaign)

    # 캠페인 수정 시에도 새로운 릴스 URL들을 수집 큐에 추가 (릴스 URL이 있으면 캠페인 타입과 관계없이 처리)
    if campaign_data.urls is not None:
        reel_urls = []
        new_reel_urls = []  # 새로 추가되거나 변경된 URL들
        
        for url_update in campaign_data.urls:
            db_url = existing_urls.get(url_update.id)
            if db_url and db_url.channel == 'instagram_reel' and 'instagram.com/reel/' in db_url.url:
                reel_urls.append(db_url.url)
                
                # URL이 변경된 경우 새로운 URL로 간주
                old_url = None
                for orig_id, orig_url_obj in existing_urls.items():
                    if orig_id == url_update.id:
                        old_url = orig_url_obj.url
                        break
                
                if old_url != db_url.url:
                    new_reel_urls.append(db_url.url)
                    logger.info(f"URL changed from {old_url} to {db_url.url}")
        
        # 기존 데이터 확인하여 누락된 것만 추가
        if reel_urls:
            try:
                collection_service = CampaignReelCollectionService()
                jobs_added = collection_service.add_reel_collection_jobs(campaign.id, reel_urls, check_existing_data=True)
                logger.info(f"Added missing reel collection jobs for updated campaign {campaign.id}")
                
                # 새로운 작업이 추가되었거나 URL이 변경되었다면 즉시 처리 시작
                if len(jobs_added) > 0 or len(new_reel_urls) > 0:
                    try:
                        asyncio.create_task(_process_reel_collection_jobs_async(campaign.id))
                        logger.info(f"Started background processing for updated campaign {campaign.id} with {len(jobs_added)} new jobs and {len(new_reel_urls)} changed URLs")
                    except Exception as e:
                        logger.error(f"Failed to create background task for update: {str(e)}")
                        # 백그라운드 작업 실패 시 동기적으로 처리
                        try:
                            processed_count = collection_service.process_pending_jobs(limit=10, campaign_id=campaign.id)
                            logger.info(f"Synchronously processed {processed_count} jobs for updated campaign {campaign.id}")
                        except Exception as sync_e:
                            logger.error(f"Synchronous processing also failed for update: {str(sync_e)}")
            except Exception as e:
                logger.error(f"Error adding reel collection jobs for update: {str(e)}")

    return campaign

@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    try:
        # Delete related records in the correct order (child -> parent)
        
        # First, delete campaign blog rankings (child of campaign_blogs)
        campaign_blog_ids = db.query(models.CampaignBlog.id).filter(
            models.CampaignBlog.campaign_id == campaign_id
        ).all()
        
        if campaign_blog_ids:
            blog_ids = [row[0] for row in campaign_blog_ids]
            db.query(models.CampaignBlogRanking).filter(
                models.CampaignBlogRanking.campaign_blog_id.in_(blog_ids)
            ).delete(synchronize_session=False)
        
        # Delete campaign-specific data
        db.query(models.CampaignInstagramPost).filter(
            models.CampaignInstagramPost.campaign_id == campaign_id
        ).delete(synchronize_session=False)
        
        db.query(models.CampaignInstagramReel).filter(
            models.CampaignInstagramReel.campaign_id == campaign_id
        ).delete(synchronize_session=False)
        
        db.query(models.CampaignBlog).filter(
            models.CampaignBlog.campaign_id == campaign_id
        ).delete(synchronize_session=False)
        
        # Delete campaign collection jobs
        db.query(models.CampaignReelCollectionJob).filter(
            models.CampaignReelCollectionJob.campaign_id == campaign_id
        ).delete(synchronize_session=False)
        
        # Delete campaign configuration
        db.query(models.CampaignURL).filter(
            models.CampaignURL.campaign_id == campaign_id
        ).delete(synchronize_session=False)
        
        db.query(models.CollectionSchedule).filter(
            models.CollectionSchedule.campaign_id == campaign_id
        ).delete(synchronize_session=False)
        
        # Finally, delete the campaign
        db.delete(campaign)
        db.commit()
        
        logger.info(f"Successfully deleted campaign {campaign_id}: {campaign.name}")
        return {"message": "Campaign deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting campaign {campaign_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(e)}")

@router.post("/{campaign_id}/process-reels")
async def process_campaign_reels(campaign_id: int, db: Session = Depends(get_db)):
    """Process collected reels data for a campaign and assign grades"""
    try:
        # Check if campaign exists
        campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Process the campaign reels
        result = campaign_collection_service.process_campaign_reels(
            db=db, 
            campaign_id=campaign_id,
            collection_date=datetime.now()
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to process campaign reels: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/{campaign_id}/reels-data")
async def get_campaign_reels_data(campaign_id: int, db: Session = Depends(get_db)):
    """Get processed reels data for a campaign"""
    try:
        # Check if campaign exists
        campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign reels data
        reels_data = campaign_collection_service.get_campaign_reel_data(db, campaign_id)
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "reels_count": len(reels_data),
            "reels": reels_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get campaign reels data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get data: {str(e)}")
