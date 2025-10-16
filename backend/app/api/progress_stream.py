import asyncio
import json
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from ..services.progress_service import progress_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/progress/stream")
async def progress_stream(session_id: str = Query(...)):
    """SSE 진행 상황 스트림"""
    async def event_stream():
        queue = await progress_service.add_client(session_id)
        
        try:
            # 초기 연결 메시지
            initial_data = {
                "event": "connected",
                "data": {"message": f"진행 상황 모니터링 시작: {session_id}"},
                "timestamp": str(asyncio.get_event_loop().time())
            }
            yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"
            
            # 진행 상황 메시지들을 계속 전송
            while True:
                try:
                    # 5초 타임아웃으로 메시지 대기
                    message = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 연결 유지를 위한 heartbeat
                    heartbeat = {
                        "event": "heartbeat",
                        "data": {"message": "연결 유지"},
                        "timestamp": str(asyncio.get_event_loop().time())
                    }
                    yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"
                    
        except asyncio.CancelledError:
            logger.info(f"SSE 스트림 취소됨: {session_id}")
        except Exception as e:
            logger.error(f"SSE 스트림 오류: {e}")
        finally:
            await progress_service.remove_client(session_id, queue)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )