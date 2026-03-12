"""WebSocket handlers for real-time review progress streaming.

Provides a WebSocket endpoint that streams review events (progress updates,
step completions, errors) from the orchestrator to the frontend.
"""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from scriptum_ai.backend.services.orchestrator import (
    get_event_queue,
    remove_event_queue,
    request_cancellation,
)

router = APIRouter(tags=["websocket"])


@router.websocket("/reviews/{review_id}")
async def review_progress_ws(
    websocket: WebSocket,
    review_id: UUID,
) -> None:
    """Stream real-time review progress updates via WebSocket.

    Reads ReviewEvent objects from the orchestrator's event queue and
    sends them as JSON to the connected client. A ``None`` sentinel
    from the queue signals the end of the stream.

    Message types sent to the client:
      - progress: {type, step, agent, progress, message}
      - step_complete: {type, step, result}
      - complete: {type, report_id}
      - error: {type, message}
      - info: {type, message}
    """
    await websocket.accept()
    logger.info("WebSocket connected", review_id=str(review_id))

    queue = get_event_queue(review_id)

    try:
        # Start two concurrent tasks:
        # 1. Read events from queue and send to client
        # 2. Listen for client messages (e.g., cancel requests)
        await asyncio.gather(
            _stream_events(websocket, review_id, queue),
            _listen_client(websocket, review_id),
        )
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", review_id=str(review_id))
    except Exception:
        logger.exception("WebSocket error", review_id=str(review_id))
    finally:
        # Clean up the queue when connection closes
        remove_event_queue(review_id)


async def _stream_events(
    websocket: WebSocket,
    review_id: UUID,
    queue: asyncio.Queue,
) -> None:
    """Read events from the orchestrator queue and send to the WebSocket client."""
    while True:
        event = await queue.get()

        # None sentinel means the pipeline has finished
        if event is None:
            logger.info("Event stream ended for review={}", review_id)
            break

        try:
            await websocket.send_json(event.model_dump(mode="json"))
        except Exception:
            logger.warning("Failed to send event to WebSocket: review={}", review_id)
            break


async def _listen_client(
    websocket: WebSocket,
    review_id: UUID,
) -> None:
    """Listen for messages from the WebSocket client.

    Currently handles: cancel requests. Other message types can be
    added here in the future.
    """
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("WebSocket received: review={} data={}", review_id, data)

            # Parse client messages
            try:
                message = json.loads(data)
                if message.get("action") == "cancel":
                    logger.info("Cancel requested via WebSocket: review={}", review_id)
                    request_cancellation(review_id)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        raise
    except Exception:
        # Client listener errors should not crash the event stream
        pass
