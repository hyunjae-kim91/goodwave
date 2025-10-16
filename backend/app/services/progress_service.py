import asyncio
import json
import logging
import time
from typing import Dict, Set
from fastapi import Request
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

class ProgressService:
    def __init__(self):
        self._clients: Dict[str, Set[asyncio.Queue]] = {}
        
    async def add_client(self, session_id: str) -> asyncio.Queue:
        """SSE 클라이언트 추가"""
        if session_id not in self._clients:
            self._clients[session_id] = set()
            
        queue = asyncio.Queue()
        self._clients[session_id].add(queue)
        
        logger.info(f"SSE 클라이언트 추가: {session_id}, 총 {len(self._clients[session_id])}개 연결")
        return queue
    
    async def remove_client(self, session_id: str, queue: asyncio.Queue):
        """SSE 클라이언트 제거"""
        if session_id in self._clients and queue in self._clients[session_id]:
            self._clients[session_id].remove(queue)
            if not self._clients[session_id]:
                del self._clients[session_id]
        logger.info(f"SSE 클라이언트 제거: {session_id}")
    
    async def send_progress(self, session_id: str, event_type: str, data: dict):
        """특정 세션의 모든 클라이언트에게 진행 상황 전송"""
        if session_id not in self._clients:
            return
            
        message = {
            "event": event_type,
            "data": data,
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
        # 연결이 끊어진 큐들을 제거하기 위한 임시 리스트
        dead_queues = []
        
        for queue in self._clients[session_id].copy():
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"SSE 메시지 전송 실패: {e}")
                dead_queues.append(queue)
        
        # 끊어진 연결 정리
        for queue in dead_queues:
            await self.remove_client(session_id, queue)
        
        logger.info(f"진행 상황 전송: {session_id} - {event_type}: {data}")

    async def send_detail_progress(self, session_id: str, data_type: str, status: str, completed: int, total: int, message: str = None):
        """세부 진행상황 전송 (프로필, 게시물, 릴스별)"""
        progress_data = {
            "data_type": data_type,  # "profile", "posts", "reels"
            "status": status,        # "pending", "running", "completed", "failed"
            "completed": completed,
            "total": total,
            "percentage": round((completed / total * 100) if total > 0 else 0, 1),
            "message": message
        }
        
        await self.send_progress(session_id, "detail_progress", progress_data)
    
    def update_progress(self, session_id: str, event_type: str, progress_percent: int, message: str):
        """동기적으로 진행 상황 업데이트 (기존 코드 호환성을 위해)"""
        try:
            # 간단한 로깅으로 대체 (SSE 전송은 별도로 처리)
            logger.info(f"Progress Update: {session_id} - {event_type}: {progress_percent}% - {message}")
            
            # 클라이언트가 연결되어 있는 경우에만 메시지 전송 시도
            if session_id in self._clients and self._clients[session_id]:
                message_data = {
                    "event": event_type,
                    "data": {
                        "progress": progress_percent,
                        "message": message
                    },
                    "timestamp": str(time.time())
                }
                
                # 각 클라이언트 큐에 메시지 추가 (논블로킹)
                for queue in list(self._clients[session_id]):
                    try:
                        if not queue.full():
                            queue.put_nowait(message_data)
                    except Exception:
                        # 큐가 가득 찼거나 닫힌 경우 무시
                        pass
        except Exception as e:
            logger.error(f"진행 상황 업데이트 실패: {e}")

# 글로벌 인스턴스
progress_service = ProgressService()