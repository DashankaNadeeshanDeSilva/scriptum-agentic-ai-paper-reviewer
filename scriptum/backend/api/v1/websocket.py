"""WebSocket handlers for real-time review progress streaming.

Provides a WebSocket endpoint that streams review events (progress updates,
step completions, errors) from the orchestrator to the frontend.
"""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter(tags=["websocket"])


@router.websocket("/reviews/{review_id}")
async def review_progress_ws(
    websocket: WebSocket,
    review_id: UUID,
) -> None:
    """Stream real-time review progress updates via WebSocket.

    Message types sent to the client:
      - progress: {type, step, agent, progress, message}
      - step_complete: {type, step, result}
      - complete: {type, report_id}
      - error: {type, message}
    """
    await websocket.accept()
    logger.info("WebSocket connected", review_id=str(review_id))

    try:
        # TODO: Subscribe to review events from orchestrator
        # TODO: Stream ReviewEvent objects as JSON messages
        # For now, send a placeholder message and keep connection alive
        await websocket.send_json({
            "type": "info",
            "message": f"Connected to review {review_id}. Waiting for events...",
        })

        # Keep connection open until client disconnects
        while True:
            # Wait for any client messages (e.g., cancel requests)
            data = await websocket.receive_text()
            logger.debug("WebSocket received", review_id=str(review_id), data=data)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", review_id=str(review_id))
