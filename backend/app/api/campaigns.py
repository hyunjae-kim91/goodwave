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

router = APIRouter()
logger = logging.getLogger(__name__)

KST_OFFSET = timedelta(hours=9)


async def _run_immediate_collection(schedule_ids: List[int]) -> None:
    if not schedule_ids:
        return

    scheduler = SchedulerService()
    try:
        for schedule_id in schedule_ids:
            schedule = (
                scheduler.db.query(models.CollectionSchedule)
                .filter(models.CollectionSchedule.id == schedule_id)
                .first()
            )
            if not schedule:
                continue
            try:
                await scheduler._process_schedule(schedule)  # noqa: SLF001
            except Exception as exc:  # noqa: BLE001
                logger.error("즉시 캠페인 수집 실패 (schedule_id=%s): %s", schedule_id, exc)
    finally:
        scheduler.db.close()


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

    if immediate_schedule_ids:
        asyncio.create_task(_run_immediate_collection(immediate_schedule_ids))

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

    return campaign

@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Delete related records
    db.query(models.CampaignInstagramPost).filter(models.CampaignInstagramPost.campaign_id == campaign_id).delete()
    db.query(models.CampaignInstagramReel).filter(models.CampaignInstagramReel.campaign_id == campaign_id).delete()

    campaign_blogs = db.query(models.CampaignBlog).filter(models.CampaignBlog.campaign_id == campaign_id).all()
    for blog_entry in campaign_blogs:
        db.delete(blog_entry)

    db.query(models.CampaignURL).filter(models.CampaignURL.campaign_id == campaign_id).delete()
    db.query(models.CollectionSchedule).filter(models.CollectionSchedule.campaign_id == campaign_id).delete()
    
    db.delete(campaign)
    db.commit()
    
    return {"message": "Campaign deleted successfully"}
