import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker

from app.db.database import engine
from app.db.models import ClassificationJob
from app.services.influencer_service import InfluencerService
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

KST_OFFSET = timedelta(hours=9)


def now_kst() -> datetime:
    return datetime.utcnow() + KST_OFFSET


class ClassificationWorker:
    def __init__(self) -> None:
        self.is_running = False
        self.Session = sessionmaker(bind=engine)
        self._thread: Optional[threading.Thread] = None

    async def start(self) -> None:
        if self.is_running:
            logger.info("📦 분류 워커가 이미 실행 중입니다")
            return

        self.is_running = True
        logger.info("🚀 분류 워커 시작")

        self.reset_orphaned_jobs()

        while self.is_running:
            try:
                processed = await self.process_next_job()
            except Exception as exc:  # noqa: BLE001
                logger.error("분류 워커 처리 중 오류: %s", exc)
                processed = False

            await asyncio.sleep(1 if processed else 5)

    def _run_forever(self) -> None:
        try:
            asyncio.run(self.start())
        except Exception as exc:  # noqa: BLE001
            logger.error("분류 워커 스레드 오류: %s", exc)
        finally:
            self.is_running = False
            self._thread = None

    def start_background(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.info("📦 분류 워커 스레드가 이미 실행 중입니다")
            return

        self._thread = threading.Thread(target=self._run_forever, name="classification-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.is_running = False
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5)
        self._thread = None
        logger.info("⏹️ 분류 워커 중지")

    def is_active(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def reset_orphaned_jobs(self) -> None:
        session = self.Session()
        try:
            now = now_kst()
            threshold = now - timedelta(minutes=5)
            stale_jobs = session.query(ClassificationJob).filter(
                ClassificationJob.status == "processing",
                or_(
                    ClassificationJob.started_at.is_(None),
                    ClassificationJob.started_at < threshold,
                    ClassificationJob.started_at > now
                )
            ).all()

            for job in stale_jobs:
                job.status = "pending"
                job.started_at = None
                job.completed_at = None
                job.error_message = None

            if stale_jobs:
                logger.info("분류 워커: 고아 작업 %d건을 대기로 되돌렸습니다", len(stale_jobs))
                session.commit()
        finally:
            session.close()

    async def process_next_job(self) -> bool:
        session = self.Session()
        job_id: Optional[str] = None
        try:
            job = session.query(ClassificationJob).filter(
                ClassificationJob.status == "pending"
            ).order_by(
                ClassificationJob.priority.desc(),
                ClassificationJob.created_at.asc()
            ).first()

            if not job:
                return False

            job.status = "processing"
            job.started_at = now_kst()
            session.commit()
            job_id = job.job_id
            logger.info("🔄 분류 작업 시작: %s (%s)", job.username, job.classification_type)
            return await self._execute_job(job_id)
        finally:
            session.close()

    async def _execute_job(self, job_id: str) -> bool:
        session = self.Session()
        try:
            job = session.query(ClassificationJob).filter(ClassificationJob.job_id == job_id).first()
            if not job:
                logger.warning("분류 작업 %s 를 찾을 수 없습니다", job_id)
                return False

            influencer_service = InfluencerService(session)
            profile = influencer_service.get_profile_by_username(job.username)
            if not profile:
                job.status = "failed"
                job.error_message = "프로필을 찾을 수 없습니다."
                job.completed_at = now_kst()
                session.commit()
                logger.error("❌ 분류 작업 실패 - 프로필 없음: %s", job.username)
                return True

            reels = influencer_service.get_reels_by_profile_id(profile.id)
            if not reels:
                job.status = "failed"
                job.error_message = "릴스 데이터를 찾을 수 없습니다."
                job.completed_at = now_kst()
                session.commit()
                logger.error("❌ 분류 작업 실패 - 릴스 없음: %s", job.username)
                return True

            openai_service = OpenAIService(session)
            try:
                # 새로운 개별 릴스 기반 분류 방식
                if job.classification_type == "combined":
                    # 구독동기와 카테고리를 모두 분류
                    classification_types = ["subscription_motivation", "category"]
                else:
                    # 특정 타입만 분류
                    classification_types = [job.classification_type]

                logger.info(f"개별 릴스 분류 시작: {job.username}, 타입: {classification_types}")
                prompt_type = None
                if isinstance(job.job_metadata, dict):
                    prompt_type = job.job_metadata.get("prompt_type")
                combined_result = await openai_service.process_all_reels_for_user(
                    job.username,
                    job.id,
                    classification_types,
                    prompt_type=prompt_type,
                )

                # 오류 확인
                if "error" in combined_result:
                    raise Exception(combined_result["error"])
                    
            except Exception as exc:  # noqa: BLE001
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = now_kst()
                session.commit()
                logger.error("❌ 분류 작업 실패(OpenAI): %s - %s", job.username, exc)
                return True

            try:
                aggregated_results = combined_result.get("aggregated_results", {})

                # 집계된 결과를 분석 테이블에 저장
                saved_payloads: dict[str, dict[str, Any]] = {}
                for aggregated_type, summary in aggregated_results.items():
                    if not summary or isinstance(summary, dict) and summary.get("error"):
                        continue
                    try:
                        influencer_service.save_analysis_result(
                            profile.id,
                            aggregated_type,
                            summary,
                            "per_reel_classification",
                        )
                        saved_payloads[aggregated_type] = summary
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "집계 결과 저장 실패(%s): %s", aggregated_type, exc
                        )

                if saved_payloads:
                    try:
                        influencer_service.save_analysis_result(
                            profile.id,
                            "combined",
                            saved_payloads,
                            "per_reel_classification",
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.error("통합 집계 저장 실패: %s", exc)

                job.status = "completed"
                job.completed_at = now_kst()
                job.error_message = None
                session.commit()
                
                # 통계 로깅
                total_reels = combined_result.get("total_reels", 0)
                logger.info(
                    "✅ 분류 작업 완료: %s (릴스 %d개)",
                    job.username,
                    total_reels,
                )
                return True
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = now_kst()
                session.commit()
                logger.error("❌ 분류 결과 저장 실패: %s - %s", job.username, exc)
                return True
        finally:
            session.close()


_worker_instance: Optional[ClassificationWorker] = None


async def start_classification_worker() -> None:
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = ClassificationWorker()

    if _worker_instance.is_active():
        return

    _worker_instance.start_background()


def stop_classification_worker() -> None:
    global _worker_instance
    if _worker_instance:
        _worker_instance.stop()


def get_classification_worker_status() -> dict:
    global _worker_instance
    if _worker_instance:
        return {
            "is_running": _worker_instance.is_running,
            "status": "running" if _worker_instance.is_running else "stopped",
            "thread_alive": _worker_instance.is_active(),
        }
    return {
        "is_running": False,
        "status": "not_initialized",
        "thread_alive": False,
    }
