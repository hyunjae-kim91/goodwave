import logging
import json
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.influencer_models import (
    ClassificationRequest,
    ClassificationResponse,
    ClassificationOverrideUpdateRequest,
)
from ..services.influencer_service import InfluencerService, SystemPromptService
from ..services.openai_service import OpenAIService
from ..services.classification_worker import start_classification_worker
from ..db.database import get_db
from ..db.models import (
    ClassificationJob,
    InfluencerClassificationSummary,
    InfluencerClassificationOverride,
    InfluencerReel,
    ReelClassification,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_CODE_BLOCK_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


def _extract_json_from_text(raw_text: Any) -> Dict[str, Any]:
    """Parse a JSON object from a string, tolerating markdown code fences."""
    if isinstance(raw_text, dict):
        return raw_text
    if not isinstance(raw_text, str):
        return {}

    cleaned = raw_text.strip()
    match = _CODE_BLOCK_JSON_RE.search(cleaned)
    candidate = match.group(1) if match else cleaned

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


def _normalize_classification_payload(payload: Any) -> Dict[str, Any]:
    """Return a dict payload, repairing known OpenAI parsing failures."""
    if isinstance(payload, dict):
        data = dict(payload)
    else:
        data = _extract_json_from_text(payload)

    if not data:
        return {}

    if data.get("error") == "parsing_failed":
        parsed = _extract_json_from_text(data.get("raw_text"))
        if parsed:
            merged = {**data, **parsed}
            merged.pop("error", None)
            merged.pop("raw_text", None)
            return merged
        # Remove the error field if we cannot recover to avoid poisoning downstream logic
        data.pop("error", None)

    return data


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _pick_confidence(*values: Any) -> Optional[float]:
    for value in values:
        confidence = _to_float(value)
        if confidence is not None:
            return confidence
    return None


def _parse_classification_value(value: Any) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    if isinstance(value, dict):
        label = (
            value.get("label")
            or value.get("value")
            or value.get("name")
            or value.get("classification")
            or value.get("classification_result")
        )
        confidence = _pick_confidence(
            value.get("confidence"),
            value.get("confidence_score"),
            value.get("score"),
        )
        reasoning = (
            value.get("reasoning")
            or value.get("reason")
            or value.get("analysis")
            or value.get("explanation")
        )

        if not label:
            primary = value.get("primary")
            if isinstance(primary, dict):
                primary_label, primary_confidence, primary_reasoning = _parse_classification_value(primary)
                label = label or primary_label
                confidence = confidence if confidence is not None else primary_confidence
                reasoning = reasoning or primary_reasoning

        if not label:
            nested = value.get("result") or value.get("details") or value.get("data")
            if nested:
                nested_label, nested_confidence, nested_reasoning = _parse_classification_value(nested)
                label = label or nested_label
                confidence = confidence if confidence is not None else nested_confidence
                reasoning = reasoning or nested_reasoning

        if not label:
            labels = value.get("labels") or value.get("options") or value.get("choices")
            if labels:
                nested_label, nested_confidence, nested_reasoning = _parse_classification_value(labels)
                label = label or nested_label
                confidence = confidence if confidence is not None else nested_confidence
                reasoning = reasoning or nested_reasoning

        if not label and isinstance(value.get("label"), dict):
            nested_label, nested_confidence, nested_reasoning = _parse_classification_value(value.get("label"))
            label = label or nested_label
            confidence = confidence if confidence is not None else nested_confidence
            reasoning = reasoning or nested_reasoning

        return (label if label else None, confidence, reasoning)

    if isinstance(value, list):
        label: Optional[str] = None
        confidence: Optional[float] = None
        reasoning: Optional[str] = None
        for item in value:
            item_label, item_confidence, item_reasoning = _parse_classification_value(item)
            if not label and item_label:
                label = item_label
            if confidence is None and item_confidence is not None:
                confidence = item_confidence
            if not reasoning and item_reasoning:
                reasoning = item_reasoning
            if label and (confidence is not None or reasoning):
                break
        return (label, confidence, reasoning)

    if isinstance(value, str):
        stripped = value.strip()
        return (stripped or None, None, None)

    if isinstance(value, (int, float)):
        return (str(value), None, None)

    return (None, None, None)


def _extract_classification_details(payload: Dict[str, Any], prefix: str) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    if not isinstance(payload, dict) or not payload:
        return (None, None, None)

    label: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None

    key_groups = ["category"] if prefix == "category" else ["motivation", "subscription_motivation"]

    def update_from_value(value: Any) -> None:
        nonlocal label, confidence, reasoning
        value_label, value_confidence, value_reasoning = _parse_classification_value(value)
        if not label and value_label:
            label = value_label
        if confidence is None and value_confidence is not None:
            confidence = value_confidence
        if not reasoning and value_reasoning:
            reasoning = value_reasoning

    for key in key_groups:
        if key in payload:
            update_from_value(payload.get(key))
        if label and (confidence is not None or reasoning):
            break

    if not label and "result" in payload:
        update_from_value(payload.get("result"))

    if not label and "details" in payload:
        update_from_value(payload.get("details"))

    if not label and "data" in payload:
        update_from_value(payload.get("data"))

    if not label:
        for key in key_groups:
            update_from_value(payload.get(f"{key}_details"))
            update_from_value(payload.get(f"{key}_result"))
            if label:
                break

    if not label:
        for key in key_groups:
            candidate = payload.get(f"{key}_label") or payload.get(f"{key}_name") or payload.get(f"{key}_value")
            update_from_value(candidate)
            if label:
                break

    if confidence is None:
        for key in key_groups:
            confidence = _pick_confidence(
                payload.get(f"{key}_confidence"),
                payload.get(f"{key}_confidence_score"),
                payload.get(f"{key}_score"),
            )
            if confidence is not None:
                break

    if not reasoning:
        for key in key_groups:
            reasoning = (
                payload.get(f"{key}_reasoning")
                or payload.get(f"{key}_reason")
                or payload.get(f"{key}_analysis")
                or payload.get(f"{key}_explanation")
            )
            if reasoning:
                break

    if not label:
        update_from_value(payload)

    if confidence is None:
        confidence = _pick_confidence(
            payload.get("confidence"),
            payload.get("confidence_score"),
            payload.get("score"),
        )

    if not reasoning:
        reasoning = (
            payload.get("reasoning")
            or payload.get("reason")
            or payload.get("analysis")
            or payload.get("explanation")
        )

    return (label if label else None, confidence, reasoning)


def _build_manual_summary(override: InfluencerClassificationOverride) -> Dict[str, Any]:
    distribution: List[Dict[str, Any]] = []
    if override.primary_classification:
        distribution.append(
            {
                "label": override.primary_classification,
                "percentage": override.primary_percentage,
                "count": None,
                "average_confidence": None,
            }
        )
    if override.secondary_classification:
        distribution.append(
            {
                "label": override.secondary_classification,
                "percentage": override.secondary_percentage,
                "count": None,
                "average_confidence": None,
            }
        )

    timestamp = override.updated_at.isoformat() if override.updated_at else None

    return {
        "classification_job_id": None,
        "primary_classification": override.primary_classification,
        "primary_percentage": override.primary_percentage,
        "secondary_classification": override.secondary_classification,
        "secondary_percentage": override.secondary_percentage,
        "classification_distribution": distribution,
        "statistics": None,
        "processed_at": timestamp,
        "timestamp": timestamp,
        "method": "manual_override",
    }

@router.post("/influencer/classification/subscription-motivation", response_model=ClassificationResponse)
async def classify_subscription_motivation(
    request: ClassificationRequest,
    db: Session = Depends(get_db)
):
    """구독 동기 분류를 수행합니다."""
    try:
        logger.info(f"구독 동기 분류 요청: {request.username}")
        
        influencer_service = InfluencerService(db)
        openai_service = OpenAIService(db)
        
        # 프로필 조회
        profile = influencer_service.get_profile_by_username(request.username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {request.username}를 찾을 수 없습니다")
        
        # 릴스 데이터 조회
        reels = influencer_service.get_reels_by_profile_id(profile.id)
        
        if not reels:
            raise HTTPException(status_code=404, detail=f"사용자 {request.username}의 릴스 데이터를 찾을 수 없습니다")
        
        prompt_type = (request.prompt_type or "system_prompt").strip()

        for reel in reels:
            await openai_service.classify_reel_combined(reel, prompt_type=prompt_type)

        aggregated = openai_service.aggregate_classification_results(
            request.username,
            classification_job_id=None,
            classification_type="subscription_motivation",
        )

        if aggregated and not aggregated.get("error"):
            influencer_service.save_analysis_result(
                profile.id,
                "subscription_motivation",
                aggregated,
                "reel_combined_classification",
            )
        
        logger.info(f"구독 동기 분류 완료: {request.username}")
        
        return ClassificationResponse(
            success=True,
            message="구독 동기 분류가 완료되었습니다",
            username=request.username,
            classification_type="subscription_motivation",
            result=aggregated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"구독 동기 분류 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"구독 동기 분류 중 오류가 발생했습니다: {str(e)}",
            "code": "CLASSIFICATION_ERROR"
        })

@router.post("/influencer/classification/category", response_model=ClassificationResponse)
async def classify_category(
    request: ClassificationRequest,
    db: Session = Depends(get_db)
):
    """카테고리 분류를 수행합니다."""
    try:
        logger.info(f"카테고리 분류 요청: {request.username}")
        
        influencer_service = InfluencerService(db)
        openai_service = OpenAIService(db)
        
        # 프로필 조회
        profile = influencer_service.get_profile_by_username(request.username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {request.username}를 찾을 수 없습니다")
        
        # 릴스 데이터 조회
        reels = influencer_service.get_reels_by_profile_id(profile.id)
        
        if not reels:
            raise HTTPException(status_code=404, detail=f"사용자 {request.username}의 릴스 데이터를 찾을 수 없습니다")
        
        prompt_type = (request.prompt_type or "system_prompt").strip()

        for reel in reels:
            await openai_service.classify_reel_combined(reel, prompt_type=prompt_type)

        aggregated = openai_service.aggregate_classification_results(
            request.username,
            classification_job_id=None,
            classification_type="category",
        )

        if aggregated and not aggregated.get("error"):
            influencer_service.save_analysis_result(
                profile.id,
                "category",
                aggregated,
                "reel_combined_classification",
            )
        
        logger.info(f"카테고리 분류 완료: {request.username}")
        
        return ClassificationResponse(
            success=True,
            message="카테고리 분류가 완료되었습니다",
            username=request.username,
            classification_type="category",
            result=aggregated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"카테고리 분류 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"카테고리 분류 중 오류가 발생했습니다: {str(e)}",
            "code": "CLASSIFICATION_ERROR"
        })

@router.post("/influencer/classification/combined", response_model=ClassificationResponse)
async def classify_combined(
    request: ClassificationRequest,
    db: Session = Depends(get_db)
):
    """통합 분류 작업을 큐에 등록합니다."""
    try:
        logger.info(f"통합 분류 요청 수신(큐 등록): {request.username}")

        influencer_service = InfluencerService(db)

        profile = influencer_service.get_profile_by_username(request.username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {request.username}를 찾을 수 없습니다")

        reels = influencer_service.get_reels_by_profile_id(profile.id)
        if not reels:
            raise HTTPException(status_code=404, detail=f"사용자 {request.username}의 릴스 데이터를 찾을 수 없습니다")

        job_type = request.classification_type or "combined"
        prompt_type = (request.prompt_type or "system_prompt").strip()

        prompt_service = SystemPromptService(db)
        prompt_entry = prompt_service.get_prompt_by_type(prompt_type)
        if not prompt_entry and prompt_type != "system_prompt":
            logger.error("선택한 프롬프트가 존재하지 않습니다: %s", prompt_type)
            raise HTTPException(status_code=400, detail="선택한 프롬프트를 찾을 수 없습니다.")

        existing_job = db.query(ClassificationJob).filter(
            ClassificationJob.username == request.username,
            ClassificationJob.classification_type == job_type,
            ClassificationJob.status.in_(["pending", "processing"])
        ).first()

        if existing_job:
            existing_prompt_type = "system_prompt"
            if isinstance(existing_job.job_metadata, dict):
                existing_prompt_type = existing_job.job_metadata.get("prompt_type") or "system_prompt"
            if existing_prompt_type == prompt_type:
                logger.info("통합 분류 작업이 이미 큐에 존재: %s", existing_job.job_id)
                return ClassificationResponse(
                    success=True,
                    message="이미 처리 중인 분류 작업이 있습니다.",
                    username=request.username,
                    classification_type=job_type,
                    result=None,
                    job_id=existing_job.job_id
                )

        job_id = str(uuid.uuid4())
        classification_job = ClassificationJob(
            job_id=job_id,
            username=request.username,
            classification_type=job_type,
            status="pending",
            job_metadata={"prompt_type": prompt_type}
        )
        db.add(classification_job)
        db.commit()

        await start_classification_worker()

        logger.info("통합 분류 작업이 큐에 추가되었습니다: %s", job_id)

        return ClassificationResponse(
            success=True,
            message="통합 분류 작업을 큐에 등록했습니다.",
            username=request.username,
            classification_type=job_type,
            result=None,
            job_id=job_id
        )

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(f"통합 분류 큐 등록 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"통합 분류 큐 등록 중 오류가 발생했습니다: {str(e)}",
            "code": "CLASSIFICATION_ENQUEUE_ERROR"
        })


@router.get("/influencer/classification-jobs")
async def list_classification_jobs(
    status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """분류 작업 큐 목록을 조회합니다."""
    try:
        query = db.query(ClassificationJob)

        if status:
            if status == "active":
                query = query.filter(ClassificationJob.status.in_(["pending", "processing", "failed"]))
            else:
                query = query.filter(ClassificationJob.status == status)
        else:
            query = query.filter(ClassificationJob.status != "completed")

        jobs = query.order_by(
            ClassificationJob.priority.desc(),
            ClassificationJob.created_at.desc()
        ).limit(limit).all()

        return {
            "success": True,
            "jobs": [job.to_dict() for job in jobs]
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"분류 작업 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"분류 작업 조회 중 오류가 발생했습니다: {str(e)}",
            "code": "CLASSIFICATION_QUEUE_FETCH_ERROR"
        })


@router.delete("/influencer/classification-jobs/{job_id}")
async def delete_classification_job(job_id: str, db: Session = Depends(get_db)):
    """분류 작업을 큐에서 제거합니다."""
    try:
        job = db.query(ClassificationJob).filter(ClassificationJob.job_id == job_id).first()
        if not job:
            return {"success": False, "message": "작업을 찾을 수 없습니다"}

        if job.status == "processing":
            return {"success": False, "message": "진행 중인 작업은 삭제할 수 없습니다"}

        db.delete(job)
        db.commit()
        logger.info("분류 작업 삭제: %s", job_id)
        return {"success": True, "message": "작업을 삭제했습니다"}
    except Exception as e:  # noqa: BLE001
        logger.error(f"분류 작업 삭제 실패: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "error": f"분류 작업 삭제 중 오류가 발생했습니다: {str(e)}",
            "code": "CLASSIFICATION_QUEUE_DELETE_ERROR"
        })

@router.get("/influencer/classification/{username}/{classification_type}")
async def get_classification_result(
    username: str, 
    classification_type: str,
    db: Session = Depends(get_db)
):
    """분류 결과를 조회합니다."""
    try:
        logger.info(f"분류 결과 조회 요청: {username}/{classification_type}")
        
        influencer_service = InfluencerService(db)
        
        # 프로필 조회
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")
        
        # 분석 결과 조회
        analysis_result = influencer_service.get_analysis_result(profile.id, classification_type)
        if not analysis_result:
            raise HTTPException(status_code=404, detail=f"분류 결과를 찾을 수 없습니다: {classification_type}")
        
        logger.info(f"분류 결과 조회 완료: {username}/{classification_type}")
        return analysis_result.analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분류 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/influencer/files/parsed-subscription-motivation/{username}")
async def get_parsed_subscription_motivation(username: str, db: Session = Depends(get_db)):
    """파싱된 구독 동기 분류 결과를 조회합니다."""
    try:
        logger.info(f"파싱된 구독 동기 분류 결과 조회 요청: {username}")
        
        influencer_service = InfluencerService(db)
        
        # 프로필 조회
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")
        
        # 분석 결과 조회
        analysis_result = influencer_service.get_analysis_result(profile.id, "subscription_motivation")
        if not analysis_result:
            raise HTTPException(status_code=404, detail="파싱된 구독 동기 분류 결과 파일을 찾을 수 없습니다")
        
        logger.info(f"파싱된 구독 동기 분류 결과 조회 완료: {username}")
        return analysis_result.analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파싱된 구독 동기 분류 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/influencer/files/parsed-category/{username}")
async def get_parsed_category(username: str, db: Session = Depends(get_db)):
    """파싱된 카테고리 분류 결과를 조회합니다."""
    try:
        logger.info(f"파싱된 카테고리 분류 결과 조회 요청: {username}")
        
        influencer_service = InfluencerService(db)
        
        # 프로필 조회
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")
        
        # 분석 결과 조회
        analysis_result = influencer_service.get_analysis_result(profile.id, "category")
        if not analysis_result:
            raise HTTPException(status_code=404, detail="파싱된 카테고리 분류 결과 파일을 찾을 수 없습니다")
        
        logger.info(f"파싱된 카테고리 분류 결과 조회 완료: {username}")
        return analysis_result.analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파싱된 카테고리 분류 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/influencer/files/combined-classification/{username}")
async def get_combined_classification(username: str, db: Session = Depends(get_db)):
    """통합 분류 결과를 조회합니다."""
    try:
        logger.info(f"통합 분류 결과 조회 요청: {username}")
        
        influencer_service = InfluencerService(db)
        
        # 프로필 조회
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")
        
        subscription_entry = influencer_service.get_analysis_result(profile.id, "subscription_motivation")
        category_entry = influencer_service.get_analysis_result(profile.id, "category")
        combined_entry = influencer_service.get_analysis_result(profile.id, "combined")

        results = []
        subscription_payload = _normalize_classification_payload(
            subscription_entry.analysis_result if subscription_entry else {}
        )
        category_payload = _normalize_classification_payload(
            category_entry.analysis_result if category_entry else {}
        )
        combined_payload = _normalize_classification_payload(
            combined_entry.analysis_result if combined_entry else {}
        )

        if subscription_payload or category_payload:
            motivation_primary = (
                subscription_payload.get("primary_motivation")
                or subscription_payload.get("primary_classification")
                or subscription_payload.get("classification")
                or ""
            )
            motivation_secondary = (
                subscription_payload.get("secondary_motivation")
                or subscription_payload.get("secondary_classification")
            )
            motivation_confidence = (
                subscription_payload.get("confidence_score")
                or subscription_payload.get("primary_percentage")
            )

            category_primary = (
                category_payload.get("primary_category")
                or category_payload.get("primary_classification")
                or category_payload.get("classification")
                or ""
            )
            category_secondary = (
                category_payload.get("secondary_category")
                or category_payload.get("secondary_classification")
            )
            category_confidence = (
                category_payload.get("confidence_score")
                or category_payload.get("primary_percentage")
            )

            results.append({
                "motivation": motivation_primary,
                "motivation_secondary": motivation_secondary,
                "motivation_confidence": motivation_confidence,
                "motivation_details": subscription_payload,
                "category": category_primary,
                "category_secondary": category_secondary,
                "category_confidence": category_confidence,
                "category_details": category_payload,
                "overall_analysis": combined_payload.get("overall_analysis") if isinstance(combined_payload, dict) else None,
                "timestamp": combined_payload.get("timestamp")
                if isinstance(combined_payload, dict)
                else subscription_payload.get("timestamp")
            })

        logger.info(f"통합 분류 결과 조회 완료: {username}")
        return {"results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"통합 분류 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/influencer/individual-reels/{username}")
async def get_individual_reel_classifications(username: str, db: Session = Depends(get_db)):
    """개별 릴스 분류 결과를 조회합니다."""
    try:
        logger.info(f"개별 릴스 분류 결과 조회: {username}")
        
        influencer_service = InfluencerService(db)
        
        # 프로필 조회
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")
        
        reels = (
            db.query(InfluencerReel)
            .filter(InfluencerReel.profile_id == profile.id)
            .order_by(InfluencerReel.created_at.desc())
            .all()
        )

        if not reels:
            raise HTTPException(status_code=404, detail="개별 릴스 분류 결과를 찾을 수 없습니다")

        reel_ids = [reel.id for reel in reels]

        classification_map: Dict[tuple[int, str], ReelClassification] = {}
        if reel_ids:
            classifications = (
                db.query(ReelClassification)
                .filter(ReelClassification.reel_id.in_(reel_ids))
                .filter(
                    ReelClassification.classification_type.in_(
                        ["subscription_motivation", "category"]
                    )
                )
                .order_by(ReelClassification.reel_id, ReelClassification.classification_type, ReelClassification.processed_at.desc().nullslast())
                .all()
            )

            for item in classifications:
                key = (item.reel_id, item.classification_type)
                current = classification_map.get(key)
                if not current:
                    classification_map[key] = item
                    continue

                current_ts = current.processed_at
                item_ts = item.processed_at
                if item_ts and (not current_ts or item_ts > current_ts):
                    classification_map[key] = item

        def build_classification_payload(reel: InfluencerReel, prefix: str) -> Dict[str, Any]:
            label = getattr(reel, prefix, None)
            confidence = getattr(reel, f"{prefix}_confidence", None)
            reasoning = getattr(reel, f"{prefix}_reasoning", None)
            image_url = getattr(reel, f"{prefix}_image_url", None)
            raw_response = getattr(reel, f"{prefix}_raw_response", None)
            error_message = getattr(reel, f"{prefix}_error", None)
            processed_at = getattr(reel, f"{prefix}_processed_at", None)
            job_id = getattr(reel, f"{prefix}_job_id", None)

            classification_type = (
                "subscription_motivation" if prefix == "subscription_motivation" else "category"
            )
            classification = classification_map.get((reel.id, classification_type))

            if classification:
                label = label or classification.classification_result
                confidence = confidence if confidence is not None else classification.confidence_score
                reasoning = reasoning or classification.reasoning
                image_url = image_url or classification.image_url
                raw_response = raw_response or classification.raw_response
                error_message = error_message or classification.error_message
                processed_at = processed_at or classification.processed_at
                job_id = job_id or classification.classification_job_id

            normalized_raw_response = _normalize_classification_payload(raw_response)
            extracted_label, extracted_confidence, extracted_reasoning = _extract_classification_details(
                normalized_raw_response, prefix
            )
            if not label and extracted_label:
                label = extracted_label
            if confidence is None and extracted_confidence is not None:
                confidence = extracted_confidence
            if not reasoning and extracted_reasoning:
                reasoning = extracted_reasoning
            if error_message == "parsing_failed" and normalized_raw_response:
                error_message = None

            if not image_url:
                # fallback to first media url if specific classification image is missing
                if reel.media_urls and isinstance(reel.media_urls, list) and reel.media_urls:
                    image_url = reel.media_urls[0]
                elif reel.photos and isinstance(reel.photos, list) and reel.photos:
                    image_url = reel.photos[0]

            return {
                "label": label,
                "confidence": confidence,
                "reasoning": reasoning,
                "image_url": image_url,
                "raw_response": normalized_raw_response or raw_response,
                "error": error_message,
                "processed_at": processed_at.isoformat() if processed_at else None,
                "classification_job_id": job_id,
                "status": "completed" if label and not error_message else "error" if error_message else "pending"
            }

        reel_data: List[Dict[str, Any]] = []
        for reel in reels:
            reel_entry = {
                "reel_id": reel.reel_id,
                "reel_db_id": reel.id,
                "caption": reel.caption,
                "description": reel.description,
                "hashtags": reel.hashtags,
                "media_urls": reel.media_urls,
                "likes": reel.likes,
                "comments": reel.num_comments,
                "views": reel.views or reel.video_play_count,
                "created_at": reel.created_at.isoformat() if reel.created_at else None,
                "subscription_motivation": build_classification_payload(reel, "subscription_motivation"),
                "category": build_classification_payload(reel, "category"),
            }
            reel_data.append(reel_entry)

        logger.info("개별 릴스 분류 결과 조회 완료: %s, %d개", username, len(reel_data))
        return {
            "username": username,
            "profile_id": profile.id,
            "total_reels": len(reel_data),
            "reels": reel_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"개별 릴스 분류 결과 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/influencer/individual-reels/{reel_id}")
async def delete_individual_reel_classification(
    reel_id: int,
    classification_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """특정 릴의 분류 결과를 삭제합니다."""
    try:
        reel = db.query(InfluencerReel).filter(InfluencerReel.id == reel_id).first()
        if not reel:
            raise HTTPException(status_code=404, detail="릴을 찾을 수 없습니다")

        valid_types = {"subscription_motivation", "category"}
        if classification_type:
            if classification_type not in valid_types:
                raise HTTPException(status_code=400, detail="지원하지 않는 분류 타입입니다")
            target_types = {classification_type}
        else:
            target_types = valid_types

        if "subscription_motivation" in target_types:
            reel.subscription_motivation = None
            reel.subscription_motivation_confidence = None
            reel.subscription_motivation_reasoning = None
            reel.subscription_motivation_image_url = None
            reel.subscription_motivation_raw_response = None
            reel.subscription_motivation_error = None
            reel.subscription_motivation_processed_at = None
            reel.subscription_motivation_job_id = None

        if "category" in target_types:
            reel.category = None
            reel.category_confidence = None
            reel.category_reasoning = None
            reel.category_image_url = None
            reel.category_raw_response = None
            reel.category_error = None
            reel.category_processed_at = None
            reel.category_job_id = None

        db.query(ReelClassification).filter(
            ReelClassification.reel_id == reel_id,
            ReelClassification.classification_type.in_(target_types),
        ).delete(synchronize_session=False)

        summaries = (
            db.query(InfluencerClassificationSummary)
            .filter(InfluencerClassificationSummary.reel_id == reel_id)
            .all()
        )

        for summary in summaries:
            if "subscription_motivation" in target_types:
                summary.motivation = None
                summary.motivation_confidence = None
                summary.motivation_reasoning = None
            if "category" in target_types:
                summary.category = None
                summary.category_confidence = None
                summary.category_reasoning = None

            has_motivation = any(
                value is not None
                for value in (
                    summary.motivation,
                    summary.motivation_confidence,
                    summary.motivation_reasoning,
                )
            )
            has_category = any(
                value is not None
                for value in (
                    summary.category,
                    summary.category_confidence,
                    summary.category_reasoning,
                )
            )

            if not has_motivation and not has_category:
                db.delete(summary)

        db.commit()

        return {
            "success": True,
            "message": "릴 분류 결과를 삭제했습니다.",
            "classification_type": list(target_types),
        }

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("릴 분류 삭제 실패 (%s): %s", reel_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/influencer/aggregated-summary/{username}")
async def get_aggregated_classification_summary(username: str, db: Session = Depends(get_db)):
    """집계된 분류 요약 결과를 조회합니다."""
    try:
        logger.info("집계된 분류 요약 조회: %s", username)

        influencer_service = InfluencerService(db)

        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")

        from ..db.models import InfluencerReel

        classification_types = ["subscription_motivation", "category"]

        overrides = (
            db.query(InfluencerClassificationOverride)
            .filter(
                InfluencerClassificationOverride.profile_id == profile.id,
                InfluencerClassificationOverride.classification_type.in_(classification_types),
            )
            .all()
        )
        override_map = {override.classification_type: override for override in overrides}

        openai_service = OpenAIService(db)
        summaries_data: Dict[str, Any] = {}

        job_id_map = {
            "subscription_motivation": db.query(
                func.max(InfluencerReel.subscription_motivation_job_id)
            )
            .filter(InfluencerReel.profile_id == profile.id)
            .scalar(),
            "category": db.query(func.max(InfluencerReel.category_job_id))
            .filter(InfluencerReel.profile_id == profile.id)
            .scalar(),
        }

        summary_presence = {
            "subscription_motivation": db.query(InfluencerClassificationSummary.id)
            .filter(
                InfluencerClassificationSummary.profile_id == profile.id,
                InfluencerClassificationSummary.motivation.isnot(None),
            )
            .first()
            is not None,
            "category": db.query(InfluencerClassificationSummary.id)
            .filter(
                InfluencerClassificationSummary.profile_id == profile.id,
                InfluencerClassificationSummary.category.isnot(None),
            )
            .first()
            is not None,
        }

        for classification_type in classification_types:
            override = override_map.get(classification_type)
            if override:
                summaries_data[classification_type] = _build_manual_summary(override)
                continue

            job_id = job_id_map.get(classification_type)
            summary: Optional[Dict[str, Any]] = None

            if job_id is not None or summary_presence.get(classification_type):
                summary = openai_service.aggregate_classification_results(
                    username,
                    job_id if job_id is not None else None,
                    classification_type,
                )

            if summary and not summary.get("error"):
                summary["method"] = "per_reel_classification"
                summaries_data[classification_type] = summary
                continue

            if summary and summary.get("error"):
                logger.warning(
                    "집계 결과 조회 중 오류 (%s): %s",
                    classification_type,
                    summary["error"],
                )

            analysis_entry = influencer_service.get_analysis_result(
                profile.id, classification_type
            )
            if analysis_entry and analysis_entry.analysis_result:
                result_payload = analysis_entry.analysis_result
                if isinstance(result_payload, dict):
                    result_payload.setdefault("method", "stored_analysis_result")
                summaries_data[classification_type] = result_payload

        if not summaries_data:
            raise HTTPException(status_code=404, detail="집계된 분류 요약 결과를 찾을 수 없습니다")

        logger.info(
            "집계된 분류 요약 조회 완료: %s, %d개 타입",
            username,
            len(summaries_data),
        )
        return {
            "username": username,
            "aggregated_summaries": summaries_data,
        }

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("집계된 분류 요약 조회 실패 (%s): %s", username, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/influencer/aggregated-summary/{username}")
async def update_manual_classification_summary(
    username: str,
    payload: ClassificationOverrideUpdateRequest,
    db: Session = Depends(get_db),
):
    """관리자가 수동으로 분류 요약 결과를 수정합니다."""
    try:
        influencer_service = InfluencerService(db)

        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")

        updates: Dict[str, InfluencerClassificationOverride] = {}

        for classification_type in ("subscription_motivation", "category"):
            override_payload = getattr(payload, classification_type)
            if not override_payload:
                continue

            override = (
                db.query(InfluencerClassificationOverride)
                .filter(
                    InfluencerClassificationOverride.profile_id == profile.id,
                    InfluencerClassificationOverride.classification_type
                    == classification_type,
                )
                .first()
            )

            if override:
                override.primary_classification = override_payload.primary_label
                override.primary_percentage = override_payload.primary_percentage
                override.secondary_classification = override_payload.secondary_label
                override.secondary_percentage = override_payload.secondary_percentage
            else:
                override = InfluencerClassificationOverride(
                    profile_id=profile.id,
                    classification_type=classification_type,
                    primary_classification=override_payload.primary_label,
                    primary_percentage=override_payload.primary_percentage,
                    secondary_classification=override_payload.secondary_label,
                    secondary_percentage=override_payload.secondary_percentage,
                )
                db.add(override)

            updates[classification_type] = override

        if not updates:
            raise HTTPException(status_code=400, detail="수정할 분류 데이터가 없습니다.")

        db.commit()

        for override in updates.values():
            db.refresh(override)

        summaries = {
            classification_type: _build_manual_summary(override)
            for classification_type, override in updates.items()
        }

        logger.info(
            "수동 분류 요약 저장 완료: %s, 수정 타입: %s",
            username,
            ", ".join(summaries.keys()),
        )

        return {
            "success": True,
            "message": "수정 내용이 저장되었습니다.",
            "overrides": summaries,
        }

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("수동 분류 요약 저장 실패 (%s): %s", username, exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/influencer/classification-data/users")
async def list_users_with_classification_data(db: Session = Depends(get_db)):
    """분류 데이터가 있는 모든 사용자 목록을 조회합니다."""
    try:
        logger.info("분류 데이터가 있는 사용자 목록 조회")
        
        influencer_service = InfluencerService(db)
        
        from ..db.models import (
            InfluencerProfile,
            InfluencerClassificationSummary,
        )

        profiles_with_data = db.query(InfluencerProfile).all()
        
        users_data = []
        for profile in profiles_with_data:
            summaries = db.query(InfluencerClassificationSummary).filter(
                InfluencerClassificationSummary.profile_id == profile.id
            ).all()

            classification_info = {
                "subscription_motivation": None,
                "category": None,
                "reel_classification": None,
            }
            
            if summaries:
                latest_processed = max(
                    (summary.processed_at for summary in summaries if summary.processed_at),
                    default=None,
                )
                classification_info["reel_classification"] = {
                    "exists": True,
                    "created_at": latest_processed.isoformat() if latest_processed else None,
                    "method": "per_reel_classification",
                    "total_reels": len(summaries),
                }

                motivation_counts: Dict[str, int] = {}
                category_counts: Dict[str, int] = {}

                for summary in summaries:
                    if summary.motivation:
                        motivation_counts[summary.motivation] = (
                            motivation_counts.get(summary.motivation, 0) + 1
                        )
                    if summary.category:
                        category_counts[summary.category] = (
                            category_counts.get(summary.category, 0) + 1
                        )

                if motivation_counts:
                    top_motivation = max(
                        motivation_counts.items(), key=lambda item: item[1]
                    )
                    classification_info["subscription_motivation"] = {
                        "exists": True,
                        "created_at": latest_processed.isoformat() if latest_processed else None,
                        "method": "per_reel_classification",
                        "primary_classification": top_motivation[0],
                        "primary_percentage": round(
                            (top_motivation[1] / len(summaries)) * 100,
                            1,
                        ),
                        "total_reels": len(summaries),
                    }

                if category_counts:
                    top_category = max(
                        category_counts.items(), key=lambda item: item[1]
                    )
                    classification_info["category"] = {
                        "exists": True,
                        "created_at": latest_processed.isoformat() if latest_processed else None,
                        "method": "per_reel_classification",
                        "primary_classification": top_category[0],
                        "primary_percentage": round(
                            (top_category[1] / len(summaries)) * 100,
                            1,
                        ),
                        "total_reels": len(summaries),
                    }
            
            if any(
                info
                for key, info in classification_info.items()
                if info and key in {"subscription_motivation", "category", "reel_classification"}
            ):
                users_data.append({
                    "username": profile.username,
                    "profile_id": profile.id,
                    "classification_data": classification_info
                })
        
        logger.info(f"분류 데이터가 있는 사용자 {len(users_data)}명 조회 완료")
        return {
            "users": users_data,
            "total_count": len(users_data)
        }
        
    except Exception as e:
        logger.error(f"사용자 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/influencer/classification-data/{username}")
async def delete_user_classification_data(
    username: str, 
    classification_type: str = None,
    db: Session = Depends(get_db)
):
    """특정 사용자의 분류 데이터를 삭제합니다."""
    try:
        logger.info(f"사용자 {username}의 분류 데이터 삭제 요청, 타입: {classification_type}")
        
        influencer_service = InfluencerService(db)
        
        # 프로필 조회
        profile = influencer_service.get_profile_by_username(username)
        if not profile:
            raise HTTPException(status_code=404, detail=f"사용자 {username}를 찾을 수 없습니다")
        
        from ..db.models import (
            InfluencerAnalysis,
            InfluencerClassificationSummary,
            InfluencerReel,
            ReelClassification,
        )
        
        deleted_count = 0
        
        subscription_reset = {
            InfluencerReel.subscription_motivation: None,
            InfluencerReel.subscription_motivation_confidence: None,
            InfluencerReel.subscription_motivation_reasoning: None,
            InfluencerReel.subscription_motivation_image_url: None,
            InfluencerReel.subscription_motivation_raw_response: None,
            InfluencerReel.subscription_motivation_error: None,
            InfluencerReel.subscription_motivation_processed_at: None,
            InfluencerReel.subscription_motivation_job_id: None,
        }

        category_reset = {
            InfluencerReel.category: None,
            InfluencerReel.category_confidence: None,
            InfluencerReel.category_reasoning: None,
            InfluencerReel.category_image_url: None,
            InfluencerReel.category_raw_response: None,
            InfluencerReel.category_error: None,
            InfluencerReel.category_processed_at: None,
            InfluencerReel.category_job_id: None,
        }

        analysis_query = db.query(InfluencerAnalysis).filter(
            InfluencerAnalysis.profile_id == profile.id
        )

        if classification_type:
            analysis_query = analysis_query.filter(
                InfluencerAnalysis.analysis_type == classification_type
            )

        deleted_count += analysis_query.delete(synchronize_session=False)

        reels_base_query = db.query(InfluencerReel).filter(
            InfluencerReel.profile_id == profile.id
        )
        reel_ids = [reel.id for reel in reels_base_query.all()]
        reels_update_query = (
            db.query(InfluencerReel).filter(InfluencerReel.id.in_(reel_ids))
            if reel_ids
            else None
        )

        summaries = db.query(InfluencerClassificationSummary).filter(
            InfluencerClassificationSummary.profile_id == profile.id
        ).all()

        if classification_type == "subscription_motivation":
            if reels_update_query is not None:
                deleted_count += reels_update_query.update(
                    subscription_reset, synchronize_session=False
                )

            for summary in summaries:
                if summary.motivation is not None or summary.motivation_confidence is not None:
                    summary.motivation = None
                    summary.motivation_confidence = None
                    summary.motivation_reasoning = None
                    summary.error = None if summary.category else summary.error
                    deleted_count += 1
                    if summary.category is None:
                        db.delete(summary)

            if reel_ids:
                deleted_count += db.query(ReelClassification).filter(
                    ReelClassification.reel_id.in_(reel_ids),
                    ReelClassification.classification_type == "subscription_motivation",
                ).delete(synchronize_session=False)

        elif classification_type == "category":
            if reels_update_query is not None:
                deleted_count += reels_update_query.update(
                    category_reset, synchronize_session=False
                )

            for summary in summaries:
                if summary.category is not None or summary.category_confidence is not None:
                    summary.category = None
                    summary.category_confidence = None
                    summary.category_reasoning = None
                    summary.error = None if summary.motivation else summary.error
                    deleted_count += 1
                    if summary.motivation is None:
                        db.delete(summary)

            if reel_ids:
                deleted_count += db.query(ReelClassification).filter(
                    ReelClassification.reel_id.in_(reel_ids),
                    ReelClassification.classification_type == "category",
                ).delete(synchronize_session=False)

        elif classification_type == "reel_classification":
            if reels_update_query is not None:
                deleted_count += reels_update_query.update(
                    {**subscription_reset, **category_reset},
                    synchronize_session=False,
                )
            for summary in summaries:
                db.delete(summary)
                deleted_count += 1

            if reel_ids:
                deleted_count += db.query(ReelClassification).filter(
                    ReelClassification.reel_id.in_(reel_ids)
                ).delete(synchronize_session=False)

        elif classification_type is None:
            if reels_update_query is not None:
                deleted_count += reels_update_query.update(
                    {**subscription_reset, **category_reset},
                    synchronize_session=False,
                )
            for summary in summaries:
                db.delete(summary)
                deleted_count += 1

            if reel_ids:
                deleted_count += db.query(ReelClassification).filter(
                    ReelClassification.reel_id.in_(reel_ids)
                ).delete(synchronize_session=False)

        db.commit()
        
        logger.info(f"사용자 {username}의 분류 데이터 삭제 완료: {deleted_count}개 항목")
        return {
            "success": True,
            "message": f"사용자 {username}의 분류 데이터가 삭제되었습니다",
            "deleted_count": deleted_count,
            "classification_type": classification_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분류 데이터 삭제 실패: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
