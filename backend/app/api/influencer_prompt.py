from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from ..models.influencer_models import PromptUpdateRequest, PromptResponse
from ..services.influencer_service import SystemPromptService
from ..db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _normalize_prompt_type(prompt_type: str) -> str:
    if prompt_type in {"system_prompt", "system"}:
        return "system"
    return prompt_type


def _denormalize_prompt_type(prompt_type: str) -> str:
    if prompt_type == "system":
        return "system_prompt"
    return prompt_type

@router.get("/influencer/prompt/{prompt_type}")
async def get_prompt(prompt_type: str, db: Session = Depends(get_db)):
    """특정 타입의 프롬프트를 조회합니다."""
    try:
        logger.info(f"프롬프트 조회 요청: {prompt_type}")

        normalized_type = _normalize_prompt_type(prompt_type)
        prompt_service = SystemPromptService(db)
        prompt = prompt_service.get_prompt_by_type(normalized_type)

        if not prompt:
            logger.info("프롬프트가 존재하지 않습니다. 빈 문자열을 반환합니다: %s", prompt_type)
            return {"content": ""}

        return {"content": prompt.content}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"프롬프트 조회 중 오류가 발생했습니다: {str(e)}",
            "code": "PROMPT_FETCH_ERROR"
        })

@router.post("/influencer/prompt/{prompt_type}", response_model=PromptResponse)
async def update_prompt(
    prompt_type: str, 
    request: PromptUpdateRequest,
    db: Session = Depends(get_db)
):
    """프롬프트를 업데이트합니다."""
    try:
        logger.info(f"프롬프트 업데이트 요청: {prompt_type}")
        
        prompt_service = SystemPromptService(db)

        normalized_type = _normalize_prompt_type(prompt_type)

        # 프롬프트 생성 또는 업데이트
        prompt = prompt_service.create_or_update_prompt(normalized_type, request.content)
        
        logger.info(f"프롬프트 업데이트 완료: {prompt_type}")
        
        return PromptResponse(
            success=True,
            message=f"{prompt_type} 프롬프트가 성공적으로 업데이트되었습니다",
            prompt_type=prompt_type,
            content=request.content
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프롬프트 업데이트 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"프롬프트 업데이트 중 오류가 발생했습니다: {str(e)}",
            "code": "PROMPT_UPDATE_ERROR"
        })

@router.get("/influencer/prompts")
async def get_all_prompts(db: Session = Depends(get_db)):
    """모든 활성 프롬프트를 조회합니다."""
    try:
        logger.info("모든 프롬프트 조회 요청")
        
        prompt_service = SystemPromptService(db)
        prompts = prompt_service.get_all_prompts()

        result = {}
        for prompt in prompts:
            result[_denormalize_prompt_type(prompt.prompt_type)] = {
                "content": prompt.content,
                "created_at": prompt.created_at,
                "updated_at": prompt.updated_at,
            }

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모든 프롬프트 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"프롬프트 조회 중 오류가 발생했습니다: {str(e)}",
            "code": "PROMPTS_FETCH_ERROR"
        })


@router.get("/influencer/prompt-types")
async def get_prompt_types(db: Session = Depends(get_db)):
    """사용 가능한 프롬프트 타입 목록을 반환합니다."""
    try:
        prompt_service = SystemPromptService(db)
        prompt_types = [
            _denormalize_prompt_type(prompt_type)
            for prompt_type in prompt_service.get_prompt_types()
        ]
        return {"prompt_types": prompt_types}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프롬프트 타입 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"프롬프트 타입 조회 중 오류가 발생했습니다: {str(e)}",
            "code": "PROMPT_TYPE_FETCH_ERROR"
        })
