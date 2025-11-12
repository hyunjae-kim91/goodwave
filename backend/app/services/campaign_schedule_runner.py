import asyncio
import logging
import threading
from datetime import datetime, timedelta, date
from typing import Optional

from app.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

KST_OFFSET = timedelta(hours=9)


def now_kst() -> datetime:
    return datetime.utcnow() + KST_OFFSET


class CampaignScheduleRunner:
    def __init__(self) -> None:
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._last_run_date: Optional[date] = None

    async def start(self) -> None:
        if self.is_running:
            logger.info("캠페인 스케줄러가 이미 실행 중입니다")
            return

        self.is_running = True
        logger.info("🗓️ 캠페인 스케줄러 시작")

        while self.is_running:
            try:
                await self._run_if_needed()
            except Exception as exc:  # noqa: BLE001
                logger.error("캠페인 스케줄러 실행 오류: %s", exc)
            await asyncio.sleep(3600)  # 1시간마다 확인

    async def _run_if_needed(self) -> None:
        """매 시간마다 실행하여 각 스케줄의 설정된 시간에 맞는 것만 처리"""
        kst_now = now_kst()
        today = kst_now.date()
        
        # 매 시간마다 실행 (스케줄러 내부에서 각 스케줄의 시간을 체크)
        logger.info("🎯 캠페인 스케줄 체크 (날짜: %s, 시간: %s KST)", today.isoformat(), kst_now.strftime('%H:%M:%S'))
        scheduler = SchedulerService()
        await scheduler.run_scheduled_collection()
        
        # 날짜가 바뀌면 last_run_date 업데이트
        if self._last_run_date != today:
            self._last_run_date = today

    def _run_forever(self) -> None:
        try:
            asyncio.run(self.start())
        except Exception as exc:  # noqa: BLE001
            logger.error("캠페인 스케줄러 스레드 오류: %s", exc)
        finally:
            self.is_running = False
            self._thread = None

    def start_background(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.info("캠페인 스케줄러 스레드가 이미 실행 중입니다")
            return

        self._thread = threading.Thread(
            target=self._run_forever,
            name="campaign-schedule-runner",
            daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self.is_running = False
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5)
        self._thread = None
        logger.info("⏹️ 캠페인 스케줄러 중지")

    def is_active(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())


_runner_instance: Optional[CampaignScheduleRunner] = None


async def start_campaign_schedule_runner() -> None:
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = CampaignScheduleRunner()

    if _runner_instance.is_active():
        return

    _runner_instance.start_background()


def stop_campaign_schedule_runner() -> None:
    global _runner_instance
    if _runner_instance:
        _runner_instance.stop()


def get_campaign_schedule_status() -> dict:
    global _runner_instance
    if _runner_instance:
        return {
            "is_running": _runner_instance.is_running,
            "status": "running" if _runner_instance.is_running else "stopped",
            "thread_alive": _runner_instance.is_active(),
        }
    return {
        "is_running": False,
        "status": "not_initialized",
        "thread_alive": False,
    }
