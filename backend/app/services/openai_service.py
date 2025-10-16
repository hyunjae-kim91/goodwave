import json
import logging
import asyncio
import tiktoken
from typing import List, Dict, Any, Optional
import openai
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.config import settings
from ..db.models import (
    InfluencerProfile,
    InfluencerReel,
    InfluencerClassificationSummary,
)
from ..services.influencer_service import SystemPromptService

logger = logging.getLogger(__name__)

MOTIVATION_LABELS = [
    "실용정보",
    "리뷰",
    "스토리",
    "자기계발",
    "웰니스",
    "프리미엄",
    "감성",
    "유머",
    "비주얼",
]

CATEGORY_LABELS = [
    "리빙",
    "맛집",
    "뷰티",
    "여행",
    "운동/레저",
    "육아/가족",
    "일상",
    "패션",
    "푸드",
]

PROMPT_HEADER = """[TASK TYPE]  
게시물의 설명과 해시태그(텍스트)와 사진(이미지)을 함께 분석하여, 구독동기정의 9개 중 하나로 분류하고, 카테고리 9개 중 하나로 분류한다.

[INSTRUCTIONS]  
1. 반드시 아래 9개의 구독동기정의와 9개의 카테고리 중 하나를 선택한다.
2. 사진 속 요소(색감, 분위기, 사람, 패션, 제품 등)와 텍스트의 의미를 함께 분석한다.
3. 최종 출력은 반드시 JSON 형식으로 제공한다.

[DO]  
- 텍스트와 사진을 함께 고려해야 한다.
- 반드시 아래 정의된 9개 카테고리명 그대로 사용해야 한다.    
- 출력은 JSON 형식으로 제한한다.

[DON'T]
- 중복 선택 금지
- 새로운 카테고리 생성 금지
- 텍스트 또는 이미지를 무시하지 말 것
- 해시태그에 #광고가 있거나 광고 글의 느낌이 난다면 절대 리뷰로 분류하지 말 것
- 9개 카테고리 외 다른 카테고리로 분류하지 않을 것

[OUTPUT FORMAT]
{"motivation": "", "category": ""}

[EXAMPLES]
{"motivation": "실용정보", "category":"푸드"}
{"motivation": "감성", "category":"일상"}

[구독동기정의(9개)]
- 실용정보: 생활에 실질적으로 도움이 되는 팁이나 정보를 얻기 위해 구독
- 리뷰: 제품 구매, 매장 방문 전 실제 사용 후기를 참고하거나 가성비 아이템을 추천받기 위해 구독 (광고성 글 제외)
- 스토리: 개인적인 경험과 일상 이야기에 공감하거나 삶의 흐름을 따라가고 싶어 구독
- 자기계발: 목표 달성이나 개인 성장을 위한 동기부여를 얻기 위해 구독
- 웰니스: 건강한 몸과 마음을 위한 습관이나 식습관을 배우기 위해 구독
- 프리미엄: 고급스러운 소비 경험이나 차별화된 가치를 동경하여 구독
- 감성: 사진·영상미·인테리어 등 시각적 요소에서 감각적 영감을 얻기 위해 구독
- 유머: 재미와 웃음을 얻기 위해 구독
- 비주얼: 모델·뷰티·패션 등 외적인 매력이나 시각적 즐거움을 위해 구독

[카테고리 정의 (9개)]
- 리빙: 인테리어, 가구, 생활 소품 등 집안 생활 관련
- 맛집: 특정 음식점, 외식 경험, 맛 평가
- 뷰티: 화장품, 메이크업, 스킨케어 등 미용 관련
- 여행: 국내외 여행, 휴가, 장소 이동 관련
- 운동/레저: 운동, 스포츠, 취미 활동 등
- 육아/가족: 자녀 양육, 가족 활동, 육아 경험
- 일상: 개인의 평범한 하루, 생활 전반 기록
- 패션: 옷, 스타일링, 패션 아이템 관련
- 푸드: 요리, 음식, 레시피, 식재료 관련
"""

class OpenAIService:
    def __init__(self, db: Session = None):
        openai.api_key = settings.openai_api_key
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.vision_client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_vision_model
        self.text_model = settings.openai_text_model
        self.db = db
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.max_tokens = 7000  # 안전한 토큰 제한 (8192 - 1000 completion - 192 여유분)
        
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")

    async def classify_image(self, image_url: str, prompt_type: str) -> Optional[str]:
        try:
            if prompt_type == "motivation":
                prompt = self._get_motivation_prompt()
            elif prompt_type == "category":
                prompt = self._get_category_prompt()
            else:
                return None

            response = self.vision_client.chat.completions.create(
                model=settings.openai_vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error classifying image with OpenAI: {str(e)}")
            return None

    async def classify_combined(
        self,
        profile: InfluencerProfile,
        reels: List[InfluencerReel],
        prompt_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """프로필의 모든 릴스를 분류하고 최신 요약을 반환합니다."""
        try:
            logger.info("통합 분류 시작: %s", profile.username)

            for reel in reels:
                await self.classify_reel_combined(reel, prompt_type=prompt_type)

            motivation_summary = self.aggregate_classification_results(
                profile.username,
                classification_job_id=None,
                classification_type="subscription_motivation",
            )

            category_summary = self.aggregate_classification_results(
                profile.username,
                classification_job_id=None,
                classification_type="category",
            )

            combined_result = {
                "subscription_motivation": motivation_summary,
                "category": category_summary,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info("통합 분류 완료: %s", profile.username)
            return combined_result

        except Exception as exc:  # noqa: BLE001
            logger.error("통합 분류 실패: %s", exc)
            raise

    async def extract_keywords_from_titles(
        self,
        titles: List[str],
        top_n: int = 10,
    ) -> List[str]:
        """주어진 블로그 제목 목록에서 핵심 명사 키워드를 추출합니다."""
        cleaned_titles = [title.strip() for title in titles if title and title.strip()]
        if not cleaned_titles or not settings.openai_api_key:
            return []

        joined_titles = "\n".join(f"- {title}" for title in cleaned_titles)
        user_prompt = (
            "다음은 동일한 캠페인에 속한 블로그 게시물 제목 목록입니다."\
            "\n각 제목에서 의미 있는 명사를 추출한 뒤, 유사한 단어는 하나로 묶어 상위 {top_n}개의 핵심 키워드만 남겨 주세요."\
            "\n출력은 아래 JSON 형식만 사용하십시오.\n"\
            "{\n  \"keywords\": [\"키워드1\", \"키워드2\", ...]\n}\n"\
            "키워드는 한글 명사 형태로 1~3글자 정도의 짧은 표현을 사용하고, 등장 빈도가 높은 순서로 정렬해 주세요."\
            "\n제목 목록:\n" + joined_titles
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 한국어 블로그 데이터를 분석하여 핵심 명사 키워드를 추출하는 데이터 분석가입니다."
                            " 의미 없는 단어, 조사, 숫자만 있는 단어는 제외하고, 상위 키워드는 10개 이내로 제한합니다."
                        ),
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.1,
                max_tokens=512,
            )

            content = (response.choices[0].message.content or "").strip()
            keywords: List[str] = []

            try:
                payload = json.loads(content)
                if isinstance(payload, dict):
                    candidate = payload.get("keywords")
                else:
                    candidate = payload
                if isinstance(candidate, list):
                    keywords = [str(item).strip() for item in candidate if str(item).strip()]
            except json.JSONDecodeError:
                # 시도: JSON이 문자열 안에 포함된 경우 추출
                import re

                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    try:
                        payload = json.loads(match.group(0))
                        candidate = payload.get("keywords") if isinstance(payload, dict) else None
                        if isinstance(candidate, list):
                            keywords = [str(item).strip() for item in candidate if str(item).strip()]
                    except Exception:
                        keywords = []

            # 최종 정제 및 개수 제한
            unique: List[str] = []
            for keyword in keywords:
                normalized = keyword.replace(" ", "")
                if normalized and normalized not in unique:
                    unique.append(normalized)
            return unique[:top_n]

        except Exception as exc:  # noqa: BLE001
            logger.error("키워드 추출 실패: %s", exc)
            return []
    
    async def classify_reel_combined(
        self,
        reel: InfluencerReel,
        classification_job_id: Optional[int] = None,
        prompt_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """캡션/해시태그/이미지를 활용해 릴스의 구독동기와 카테고리를 동시 분류합니다."""
        image_url: Optional[str] = None
        if reel.media_urls and isinstance(reel.media_urls, list) and reel.media_urls:
            image_url = reel.media_urls[0]
        elif reel.photos and isinstance(reel.photos, list) and reel.photos:
            image_url = reel.photos[0]

        if not image_url:
            raise ValueError("릴스에 분석할 이미지 URL이 없습니다")

        caption = self._truncate_text(reel.caption or "", 400)
        hashtags_list = []
        if isinstance(reel.hashtags, list):
            hashtags_list = [str(tag) for tag in reel.hashtags if tag]
        elif reel.hashtags:
            hashtags_list = [str(reel.hashtags)]
        hashtags_text = ", ".join(hashtags_list)

        prompt_body = (
            f"{PROMPT_HEADER}\n\n[CONTENT]\n설명: {caption or '없음'}\n해시태그: {hashtags_text or '없음'}"
        )

        system_prompt = self._get_system_prompt(prompt_type or "system_prompt")

        user_content = [
            {
                "type": "text",
                "text": prompt_body,
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                    "detail": "low",
                },
            },
        ]

        if not settings.openai_api_key:
            mock_result = self._generate_mock_combined_classification()
            self._persist_reel_classification(
                reel=reel,
                payload=mock_result,
                image_url=image_url,
                classification_job_id=classification_job_id,
            )
            return mock_result

        try:
            response = self.vision_client.chat.completions.create(
                model=settings.openai_vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=120,
                temperature=0.1,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAI Vision 호출 실패: %s", exc)
            error_result = {
                "motivation": None,
                "category": None,
                "error": str(exc),
            }
            self._persist_reel_classification(
                reel=reel,
                payload=error_result,
                image_url=image_url,
                classification_job_id=classification_job_id,
                error_message=str(exc),
            )
            return error_result

        result_text = response.choices[0].message.content

        try:
            parsed = json.loads(result_text)
        except json.JSONDecodeError:
            logger.error("OpenAI 응답 JSON 파싱 실패: %s", result_text)
            parsed = {
                "motivation": None,
                "category": None,
                "error": "JSON parsing failed",
                "raw_response": result_text,
            }

        motivation = parsed.get("motivation")
        category = parsed.get("category")

        if motivation not in MOTIVATION_LABELS:
            if motivation is not None:
                logger.warning("허용되지 않은 구독동기 라벨: %s", motivation)
            motivation = MOTIVATION_LABELS[0]

        if category not in CATEGORY_LABELS:
            if category is not None:
                logger.warning("허용되지 않은 카테고리 라벨: %s", category)
            category = CATEGORY_LABELS[0]

        normalized_payload = {
            "motivation": motivation,
            "category": category,
            "raw_response": parsed,
        }

        self._persist_reel_classification(
            reel=reel,
            payload=normalized_payload,
            image_url=image_url,
            classification_job_id=classification_job_id,
        )

        logger.info(
            "릴스 분류 완료: %s -> (%s, %s)",
            reel.reel_id,
            motivation,
            category,
        )
        return normalized_payload

    def _persist_reel_classification(
        self,
        reel: InfluencerReel,
        payload: Dict[str, Any],
        image_url: Optional[str],
        classification_job_id: Optional[int],
        error_message: Optional[str] = None,
    ) -> None:
        """분류 결과를 릴 테이블과 요약 테이블에 저장합니다."""
        if not self.db:
            return

        processed_at = datetime.utcnow()
        motivation = payload.get("motivation")
        category = payload.get("category")
        raw_response = payload.get("raw_response", payload)
        error_value = error_message or payload.get("error")

        try:
            reel.subscription_motivation = motivation
            reel.subscription_motivation_confidence = None
            reel.subscription_motivation_reasoning = None
            reel.subscription_motivation_image_url = image_url
            reel.subscription_motivation_raw_response = raw_response
            reel.subscription_motivation_error = error_value
            reel.subscription_motivation_processed_at = processed_at
            reel.subscription_motivation_job_id = classification_job_id

            reel.category = category
            reel.category_confidence = None
            reel.category_reasoning = None
            reel.category_image_url = image_url
            reel.category_raw_response = raw_response
            reel.category_error = error_value
            reel.category_processed_at = processed_at
            reel.category_job_id = classification_job_id

            self.db.add(reel)

            summary = (
                self.db.query(InfluencerClassificationSummary)
                .filter(
                    InfluencerClassificationSummary.reel_id == reel.id,
                    InfluencerClassificationSummary.classification_job_id
                    == classification_job_id,
                )
                .first()
            )

            username = reel.profile.username if reel.profile else None

            if not summary:
                summary = InfluencerClassificationSummary(
                    username=username or "",
                    reel_id=reel.id,
                    profile_id=reel.profile_id,
                    classification_job_id=classification_job_id,
                    classification_type="combined",
                    primary_classification=motivation or "",
                    primary_percentage=100.0 if motivation else 0.0,
                    secondary_classification=category,
                    secondary_percentage=100.0 if category else None,
                    total_reels_processed=1,
                    successful_classifications=1 if motivation and category else 0,
                    average_confidence_score=None,
                )
            else:
                summary.total_reels_processed = (summary.total_reels_processed or 0) + 1
                if motivation and category:
                    summary.successful_classifications = (summary.successful_classifications or 0) + 1

            summary.username = username or summary.username
            summary.reel_id = reel.id
            summary.profile_id = reel.profile_id
            summary.motivation = motivation
            summary.category = category
            summary.motivation_confidence = reel.subscription_motivation_confidence
            summary.category_confidence = reel.category_confidence
            summary.motivation_reasoning = reel.subscription_motivation_reasoning
            summary.category_reasoning = reel.category_reasoning
            summary.raw_response = raw_response
            summary.error = error_value
            summary.processed_at = processed_at
            summary.primary_classification = motivation or summary.primary_classification
            summary.primary_percentage = 100.0 if motivation else summary.primary_percentage
            summary.secondary_classification = category
            summary.secondary_percentage = 100.0 if category else summary.secondary_percentage

            self.db.add(summary)

            self.db.commit()
            self.db.refresh(reel)
        except Exception as db_error:  # noqa: BLE001
            logger.error("릴스 분류 결과 저장 실패: %s", db_error)
            self.db.rollback()
    
    def _get_system_prompt(self, prompt_type: str) -> str:
        """시스템 프롬프트를 가져옵니다."""
        if self.db:
            prompt_service = SystemPromptService(self.db)
            prompt = prompt_service.get_prompt_by_type(prompt_type)
            if prompt:
                return prompt.content
        
        # 기본 프롬프트
        default_prompts = {
            "system": "당신은 인플루언서 분석 전문가입니다. 한국어로 정확하고 상세한 분석을 제공해주세요.",
            "subscription_motivation": "인플루언서의 구독 동기를 분석하는 전문가입니다. 콘텐츠와 프로필을 분석하여 팔로워들이 구독하는 주요 동기를 파악해주세요.",
            "category": "인플루언서의 콘텐츠 카테고리를 분류하는 전문가입니다. 프로필과 콘텐츠를 분석하여 주요 카테고리를 정확히 분류해주세요."
        }
        
        return default_prompts.get(prompt_type, default_prompts["system"])
    
    def _count_tokens(self, text: str) -> int:
        """텍스트의 토큰 수를 계산합니다."""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # 대략적인 추정치 (한국어 기준)
            return len(text) // 2
    
    def _truncate_text(self, text: str, max_length: int = 500) -> str:
        """텍스트를 안전하게 자릅니다."""
        if not text:
            return ""
        
        # 토큰 수 확인
        if self._count_tokens(text) <= max_length:
            return text
        
        # 문자 단위로 자르기 (대략적)
        char_limit = max_length * 2  # 한국어 기준 추정
        if len(text) <= char_limit:
            return text
        
        # 문장 단위로 자르기 시도
        sentences = text.split('.')
        truncated = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence + ".")
            if current_tokens + sentence_tokens > max_length:
                break
            truncated += sentence + "."
            current_tokens += sentence_tokens
        
        if truncated:
            return truncated
        
        # 문장 단위로 안 되면 문자 단위로
        return text[:char_limit] + "..."
    
    
    def _generate_mock_combined_classification(self) -> Dict[str, Any]:
        """개발용 결합 분류 목 데이터를 생성합니다."""
        import random

        return {
            "motivation": random.choice(MOTIVATION_LABELS),
            "category": random.choice(CATEGORY_LABELS),
            "raw_response": {
                "motivation": random.choice(MOTIVATION_LABELS),
                "category": random.choice(CATEGORY_LABELS),
                "mock": True,
            },
        }
    
    def aggregate_classification_results(
        self,
        username: str,
        classification_job_id: Optional[int],
        classification_type: str,
    ) -> Dict[str, Any]:
        """개별 릴스 분류 결과를 집계합니다."""
        try:
            logger.info(f"분류 결과 집계 시작: {username}, 타입: {classification_type}")
            
            if not self.db:
                return {"error": "데이터베이스 연결이 없습니다"}
            
            profile = self.db.query(InfluencerProfile).filter(
                InfluencerProfile.username == username
            ).first()

            if not profile:
                return {"error": "사용자 프로필을 찾을 수 없습니다"}

            if classification_type not in {"subscription_motivation", "category"}:
                raise ValueError(f"지원하지 않는 분류 타입: {classification_type}")

            summaries_query = self.db.query(InfluencerClassificationSummary).filter(
                InfluencerClassificationSummary.profile_id == profile.id
            )

            if classification_job_id is not None:
                summaries_query = summaries_query.filter(
                    InfluencerClassificationSummary.classification_job_id
                    == classification_job_id
                )
            else:
                summaries_query = summaries_query.filter(
                    InfluencerClassificationSummary.classification_job_id.is_(None)
                )

            summaries = summaries_query.all()

            if not summaries:
                return {"error": "분류 결과가 없습니다"}

            classification_counts: Dict[str, Dict[str, float]] = {}
            total_confidence = 0.0
            successful_classifications = 0
            failed_classifications = 0
            processed_at_candidates = []

            for summary in summaries:
                if classification_type == "subscription_motivation":
                    label = summary.motivation
                    confidence = summary.motivation_confidence or 0.0
                else:
                    label = summary.category
                    confidence = summary.category_confidence or 0.0

                if summary.processed_at:
                    processed_at_candidates.append(summary.processed_at)

                if summary.error or not label:
                    failed_classifications += 1
                    continue

                bucket = classification_counts.setdefault(
                    label, {"count": 0, "total_confidence": 0.0}
                )
                bucket["count"] += 1
                bucket["total_confidence"] += confidence
                total_confidence += confidence
                successful_classifications += 1

            if successful_classifications == 0:
                return {"error": "성공한 분류 결과가 없습니다"}

            total_processed = len(summaries)
            success_rate = (
                round((successful_classifications / total_processed) * 100, 1)
                if total_processed
                else 0
            )
            average_confidence = (
                total_confidence / successful_classifications
                if successful_classifications
                else 0
            )

            distribution = []
            for label, data in classification_counts.items():
                count = data["count"]
                percentage = round((count / successful_classifications) * 100, 1)
                distribution.append(
                    {
                        "label": label,
                        "count": count,
                        "percentage": percentage,
                        "average_confidence": round(
                            data["total_confidence"] / count, 3
                        )
                        if count
                        else 0,
                    }
                )

            distribution.sort(key=lambda item: item["count"], reverse=True)

            primary = distribution[0]
            secondary = distribution[1] if len(distribution) > 1 else None

            most_recent_processed = (
                max(processed_at_candidates).isoformat()
                if processed_at_candidates
                else None
            )

            result = {
                "classification_job_id": classification_job_id,
                "primary_classification": primary["label"],
                "primary_percentage": primary["percentage"],
                "secondary_classification": secondary["label"] if secondary else None,
                "secondary_percentage": secondary["percentage"] if secondary else None,
                "classification_distribution": distribution,
                "statistics": {
                    "total_reels_processed": total_processed,
                    "total_reels_considered": total_processed,
                    "successful_classifications": successful_classifications,
                    "failed_classifications": failed_classifications,
                    "success_rate": success_rate,
                    "average_confidence_score": round(average_confidence, 3),
                },
                "processed_at": most_recent_processed,
                "timestamp": most_recent_processed,
            }

            logger.info(
                "분류 결과 집계 완료: %s, 주요 분류: %s (%s%%)",
                username,
                primary["label"],
                primary["percentage"],
            )
            return result
            
        except Exception as e:
            logger.error(f"분류 결과 집계 실패: {str(e)}")
            return {"error": f"집계 실패: {str(e)}"}
    
    async def process_all_reels_for_user(
        self,
        username: str,
        classification_job_id: int,
        classification_types: List[str] = None,
        prompt_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """사용자의 모든 릴스를 개별적으로 분류하고 집계합니다."""
        try:
            logger.info(f"사용자 릴스 일괄 분류 시작: {username}")
            
            if not self.db:
                return {"error": "데이터베이스 연결이 없습니다"}
            
            if classification_types is None:
                classification_types = ["subscription_motivation", "category"]

            from ..db.models import InfluencerProfile

            profile = self.db.query(InfluencerProfile).filter(
                InfluencerProfile.username == username
            ).first()

            if not profile:
                return {"error": "사용자 프로필을 찾을 수 없습니다"}

            reels = (
                self.db.query(InfluencerReel)
                .filter(InfluencerReel.profile_id == profile.id)
                .order_by(InfluencerReel.created_at.desc())
                .all()
            )

            if not reels:
                return {"error": "분류할 릴스가 없습니다"}

            individual_results = []
            for idx, reel in enumerate(reels, start=1):
                try:
                    logger.info("릴스 분류 진행: %d/%d - %s", idx, len(reels), reel.reel_id)
                    result = await self.classify_reel_combined(
                        reel,
                        classification_job_id,
                        prompt_type=prompt_type,
                    )
                    individual_results.append(
                        {
                            "reel_id": reel.reel_id,
                            "reel_db_id": reel.id,
                            "result": result,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error("릴스 %s 분류 실패: %s", reel.reel_id, exc)
                    individual_results.append(
                        {
                            "reel_id": reel.reel_id,
                            "reel_db_id": reel.id,
                            "result": {"error": str(exc)},
                        }
                    )
                await asyncio.sleep(1)

            aggregated_results = {}
            for classification_type in classification_types:
                aggregated_results[classification_type] = self.aggregate_classification_results(
                    username, classification_job_id, classification_type
                )

            logger.info(
                "사용자 릴스 일괄 분류 완료: %s (릴스 %d개)",
                username,
                len(reels),
            )

            return {
                "username": username,
                "total_reels": len(reels),
                "classification_types": classification_types,
                "individual_results": individual_results,
                "aggregated_results": aggregated_results,
            }
            
        except Exception as e:
            logger.error(f"사용자 릴스 일괄 분류 실패: {str(e)}")
            return {"error": f"일괄 분류 실패: {str(e)}"}
    

    def _get_motivation_prompt(self) -> str:
        return """다음 인스타그램 이미지를 보고 구독 동기를 한 단어로 분류해주세요.
        
가능한 분류:
- 정보성: 유용한 정보나 팁을 제공하는 콘텐츠
- 엔터테인먼트: 재미나 오락을 위한 콘텐츠
- 영감: 동기부여나 영감을 주는 콘텐츠
- 라이프스타일: 일상이나 취미를 공유하는 콘텐츠
- 상품소개: 제품이나 서비스를 홍보하는 콘텐츠

한 단어로만 답변해주세요."""

    def _get_category_prompt(self) -> str:
        return """다음 인스타그램 이미지를 보고 카테고리를 한 단어로 분류해주세요.
        
가능한 분류:
- 패션: 옷, 액세서리, 스타일 관련
- 뷰티: 화장품, 스킨케어, 헤어 관련
- 푸드: 음식, 요리, 카페 관련
- 여행: 여행지, 관광, 숙소 관련
- 피트니스: 운동, 헬스, 요가 관련
- 테크: 기술, 가젯, 앱 관련
- 육아: 아이, 육아용품, 교육 관련
- 인테리어: 집, 가구, 데코 관련
- 기타: 위에 해당하지 않는 모든 것

한 단어로만 답변해주세요."""

openai_service = OpenAIService()
