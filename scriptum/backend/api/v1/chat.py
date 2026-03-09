"""Chat endpoints for conversing with the meta reviewer about a completed review.

Provides REST endpoint for chat history and a WebSocket endpoint that streams
LLM responses token-by-token, persisting both user and assistant messages.
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.core.llm import LLMClient, LLMError
from backend.models.review import ChatMessage, Review

router = APIRouter(tags=["chat"])
ws_router = APIRouter(tags=["chat"])

# Maximum context messages to include in the LLM prompt
MAX_CONTEXT_MESSAGES = 50


def _build_system_prompt(review: Review) -> str:
    """Build a system prompt that gives the LLM context about the review."""
    report_summary = ""
    if review.final_report:
        report = review.final_report
        report_summary = (
            f"\nRecommendation: {report.get('recommendation', 'N/A')}\n"
            f"Confidence: {report.get('confidence', 'N/A')}\n"
            f"Key strengths: {', '.join(report.get('key_strengths', []))}\n"
            f"Key weaknesses: {', '.join(report.get('key_weaknesses', []))}\n"
        )

    return (
        "You are SCRIPTUM's Meta Reviewer — an AI academic paper review assistant. "
        "You have already reviewed the user's paper and produced a detailed report. "
        "The user is now asking follow-up questions about the review.\n\n"
        f"Paper title: {review.paper_title or 'Unknown'}\n"
        f"Journal: {review.journal_name or 'Not specified'}\n"
        f"Domain: {review.domain_general or ''} / {review.domain_specific or ''}\n"
        f"{report_summary}\n"
        "Answer questions about the review thoughtfully and concisely. "
        "If the user asks about something not covered in the review, "
        "acknowledge it and provide your best analysis. "
        "Be constructive and helpful."
    )


@router.get("/reviews/{review_id}/chat/history")
async def get_chat_history(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return the chat history for a review."""
    # Verify review exists
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.review_id == review_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@ws_router.websocket("/reviews/{review_id}/chat")
async def review_chat_ws(
    websocket: WebSocket,
    review_id: UUID,
) -> None:
    """WebSocket endpoint for streaming chat with the meta reviewer.

    Client sends: {"content": "user message text"}
    Server sends:
      - {"type": "token", "content": "..."} for each streamed token
      - {"type": "complete"} when the response is finished
      - {"type": "error", "message": "..."} on failure
    """
    await websocket.accept()
    logger.info("Chat WebSocket connected", review_id=str(review_id))

    # Get a fresh DB session for the WS lifetime
    from backend.core.database import async_session_factory

    async with async_session_factory() as db:
        # Verify review exists and is completed
        review = await db.get(Review, review_id)
        if not review:
            await websocket.send_json({"type": "error", "message": "Review not found"})
            await websocket.close()
            return

        if review.status != "completed":
            await websocket.send_json(
                {"type": "error", "message": "Review must be completed before chatting"}
            )
            await websocket.close()
            return

        system_prompt = _build_system_prompt(review)

        try:
            llm = LLMClient()
        except LLMError as e:
            await websocket.send_json({"type": "error", "message": f"LLM not configured: {e}"})
            await websocket.close()
            return

        try:
            while True:
                # Wait for user message
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                    user_content = data.get("content", "").strip()
                except (json.JSONDecodeError, AttributeError):
                    user_content = raw.strip()

                if not user_content:
                    continue

                # Persist user message
                user_msg = ChatMessage(
                    review_id=review_id,
                    role="user",
                    content=user_content,
                )
                db.add(user_msg)
                await db.commit()

                # Load recent chat history for context
                result = await db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.review_id == review_id)
                    .order_by(ChatMessage.created_at)
                    .limit(MAX_CONTEXT_MESSAGES)
                )
                history = result.scalars().all()

                # Build messages for LLM
                llm_messages: list[dict[str, str]] = [
                    {"role": "system", "content": system_prompt},
                ]
                for msg in history:
                    llm_messages.append({"role": msg.role, "content": msg.content})

                # Stream response
                full_response = ""
                try:
                    async for token in llm.stream(llm_messages, temperature=0.4, max_tokens=2048):
                        full_response += token
                        await websocket.send_json({"type": "token", "content": token})

                    # Persist assistant message
                    assistant_msg = ChatMessage(
                        review_id=review_id,
                        role="assistant",
                        content=full_response,
                    )
                    db.add(assistant_msg)
                    await db.commit()

                    await websocket.send_json({"type": "complete"})

                except LLMError as e:
                    logger.error("Chat LLM error: {}", e)
                    await websocket.send_json({"type": "error", "message": str(e)})

        except WebSocketDisconnect:
            logger.info("Chat WebSocket disconnected", review_id=str(review_id))
        except Exception:
            logger.exception("Chat WebSocket error", review_id=str(review_id))
