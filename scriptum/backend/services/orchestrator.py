"""Review orchestration service for SCRIPTUM.

Implements the 6-stage review pipeline:
  1. Parse Document
  2. Meta Reviewer Desk Check
  3. Gate Check
  4. Parallel Independent Review (3 agents)
  5. Meta Reviewer Aggregation
  6. Report Generation & Persistence

Runs as a FastAPI BackgroundTask. Emits ReviewEvent objects to an
asyncio.Queue that the WebSocket endpoint consumes.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import time as _time

from agents.core.base import AgentInterface, ReviewResult, ReviewTask
from backend.core.config import get_settings
from backend.core.database import async_session_factory
from backend.core.exceptions import AgentTimeoutError
from backend.core.metrics import get_metrics_collector
from backend.models.review import File, Review, ReviewerResult
from backend.schemas.review import (
    DeskCheckResult,
    ReviewerReport,
    ReviewEvent,
    ReviewReport,
    ReviewScore,
)
# Lazy imports to avoid pulling in docling at module level:
#   from backend.services.document import DocumentProcessingError, process_document
#   from tools.document.models import ParsedDocument
# These are imported inside _stage_parse_document() instead.

# ---------------------------------------------------------------------------
# Event registry: review_id -> asyncio.Queue
# WebSocket endpoint reads from these queues.
# ---------------------------------------------------------------------------

_event_queues: dict[uuid.UUID, asyncio.Queue[ReviewEvent | None]] = {}
_cancel_events: dict[uuid.UUID, asyncio.Event] = {}


def get_event_queue(review_id: uuid.UUID) -> asyncio.Queue[ReviewEvent | None]:
    """Get or create the event queue for a review.

    Returns an asyncio.Queue that yields ReviewEvent objects.
    A ``None`` sentinel signals the end of the stream.
    """
    if review_id not in _event_queues:
        _event_queues[review_id] = asyncio.Queue()
    return _event_queues[review_id]


def remove_event_queue(review_id: uuid.UUID) -> None:
    """Remove the event queue for a review (cleanup)."""
    _event_queues.pop(review_id, None)
    _cancel_events.pop(review_id, None)


def request_cancellation(review_id: uuid.UUID) -> None:
    """Signal that a review pipeline should be cancelled.

    The pipeline checks this flag between stages and aborts gracefully.
    """
    event = _cancel_events.get(review_id)
    if event is not None:
        event.set()
        logger.info("Cancellation requested for review={}", review_id)


def _get_cancel_event(review_id: uuid.UUID) -> asyncio.Event:
    """Get or create the cancellation event for a review."""
    if review_id not in _cancel_events:
        _cancel_events[review_id] = asyncio.Event()
    return _cancel_events[review_id]


def _is_cancelled(review_id: uuid.UUID) -> bool:
    """Check whether cancellation has been requested for a review."""
    event = _cancel_events.get(review_id)
    return event is not None and event.is_set()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _PipelineCancelled(Exception):
    """Raised internally when a pipeline detects a cancellation request."""


def _check_cancelled(review_id: uuid.UUID) -> None:
    """Raise ``_PipelineCancelled`` if cancellation was requested."""
    if _is_cancelled(review_id):
        raise _PipelineCancelled(f"Review {review_id} cancelled")


async def _emit(review_id: uuid.UUID, event: ReviewEvent) -> None:
    """Put an event onto the review's queue."""
    queue = get_event_queue(review_id)
    await queue.put(event)
    logger.debug("Event emitted: review={} type={} step={}", review_id, event.type, event.step)


async def _update_status(session: AsyncSession, review_id: uuid.UUID, status: str) -> None:
    """Update the review status in the database."""
    stmt = update(Review).where(Review.id == review_id).values(status=status)
    await session.execute(stmt)
    await session.commit()


async def _get_file_paths(session: AsyncSession, review_id: uuid.UUID) -> list[dict[str, Any]]:
    """Retrieve file metadata for a review."""
    stmt = select(File).where(File.review_id == review_id)
    result = await session.execute(stmt)
    files = result.scalars().all()
    return [
        {
            "id": f.id,
            "file_type": f.file_type,
            "storage_path": f.storage_path,
            "filename": f.filename,
        }
        for f in files
    ]


def _review_result_to_reviewer_report(result: ReviewResult) -> ReviewerReport:
    """Convert internal ReviewResult dataclass to API ReviewerReport schema."""
    return ReviewerReport(
        reviewer_type=result.reviewer_type,
        scores=result.scores,
        feedback=result.feedback,
        evidence=[
            {
                "claim": e.claim,
                "source": e.source,
                "quote": e.quote,
                "relevance": e.relevance,
            }
            for e in result.evidence
        ],
        recommendation=result.recommendation,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def run_review_pipeline(
    review_id: uuid.UUID,
    *,
    meta_reviewer: AgentInterface,
    core_expert: AgentInterface,
    adjacent_expert: AgentInterface,
    methods_specialist: AgentInterface,
    journal_config: dict[str, Any] | None = None,
    domain_general: str = "",
    domain_specific: str = "",
    review_criteria: dict[str, float] | None = None,
) -> None:
    """Execute the full 6-stage review pipeline.

    This function is designed to be called from a FastAPI BackgroundTask.
    It opens its own database session and emits events to an asyncio.Queue.

    Parameters
    ----------
    review_id:
        UUID of the review record (must already exist in the database).
    meta_reviewer:
        Initialized AgentInterface for the meta reviewer.
    core_expert / adjacent_expert / methods_specialist:
        Initialized AgentInterface instances for each reviewer agent.
    journal_config:
        Journal-specific configuration (e.g., scope, formatting rules).
    domain_general / domain_specific:
        Domain context for the review.
    review_criteria:
        Category -> weight mapping for scoring.
    """
    journal_config = journal_config or {}
    review_criteria = review_criteria or {}

    # Register a cancellation event for this pipeline run
    _get_cancel_event(review_id)

    try:
        async with async_session_factory() as session:
            await _run_pipeline_stages(
                session=session,
                review_id=review_id,
                meta_reviewer=meta_reviewer,
                core_expert=core_expert,
                adjacent_expert=adjacent_expert,
                methods_specialist=methods_specialist,
                journal_config=journal_config,
                domain_general=domain_general,
                domain_specific=domain_specific,
                review_criteria=review_criteria,
            )
    except _PipelineCancelled:
        logger.info("Pipeline cancelled: review={}", review_id)
        try:
            async with async_session_factory() as session:
                await _update_status(session, review_id, "cancelled")
        except Exception:
            logger.exception("Failed to update review status to 'cancelled': review={}", review_id)
        await _emit(
            review_id,
            ReviewEvent(type="error", step="cancelled", message="Review cancelled by user."),
        )
    except Exception as exc:
        logger.exception("Pipeline failed with unhandled error: review={}", review_id)
        # Attempt to save failure state
        try:
            async with async_session_factory() as session:
                await _update_status(session, review_id, "failed")
        except Exception:
            logger.exception("Failed to update review status to 'failed': review={}", review_id)

        await _emit(
            review_id,
            ReviewEvent(type="error", message=f"Pipeline failed: {exc}"),
        )
    finally:
        # Send sentinel to signal end of stream
        await _emit_sentinel(review_id)


async def _emit_sentinel(review_id: uuid.UUID) -> None:
    """Send None sentinel to signal end of event stream."""
    queue = get_event_queue(review_id)
    await queue.put(None)


async def _run_pipeline_stages(
    *,
    session: AsyncSession,
    review_id: uuid.UUID,
    meta_reviewer: AgentInterface,
    core_expert: AgentInterface,
    adjacent_expert: AgentInterface,
    methods_specialist: AgentInterface,
    journal_config: dict[str, Any],
    domain_general: str,
    domain_specific: str,
    review_criteria: dict[str, float],
) -> None:
    """Run all 6 pipeline stages sequentially."""
    _metrics = get_metrics_collector()
    _pipeline_start = _time.perf_counter()

    # -----------------------------------------------------------------------
    # Stage 1: Parse Document
    # -----------------------------------------------------------------------
    await _update_status(session, review_id, "processing")
    await _emit(
        review_id,
        ReviewEvent(type="progress", step="document_processing", progress=0.0, message="Parsing document..."),
    )

    _stage_start = _time.perf_counter()
    try:
        parsed_document = await _stage_parse_document(session, review_id)
    except Exception as exc:
        logger.error("Stage 1 (Parse Document) failed: review={} error={}", review_id, exc)
        await _update_status(session, review_id, "failed")
        await _emit(
            review_id,
            ReviewEvent(type="error", step="document_processing", message=f"Document parsing failed: {exc}"),
        )
        return

    # Save paper title if extracted
    if parsed_document.metadata.title:
        stmt = update(Review).where(Review.id == review_id).values(paper_title=parsed_document.metadata.title)
        await session.execute(stmt)
        await session.commit()

    await _emit(
        review_id,
        ReviewEvent(
            type="step_complete",
            step="document_processing",
            progress=0.15,
            message="Document parsed successfully.",
            result={"title": parsed_document.metadata.title, "sections": len(parsed_document.sections)},
        ),
    )

    await _metrics.record_stage_timing(session, review_id, "document_processing", (_time.perf_counter() - _stage_start) * 1000)
    await session.commit()

    _check_cancelled(review_id)

    # Build ReviewTask for agents
    review_task = ReviewTask(
        paper=parsed_document,
        journal_config=journal_config,
        domain_general=domain_general,
        domain_specific=domain_specific,
        review_criteria=review_criteria,
    )
    task_dict = review_task.to_dict()

    # -----------------------------------------------------------------------
    # Stage 2: Meta Reviewer Desk Check
    # -----------------------------------------------------------------------
    await _update_status(session, review_id, "desk_check")
    await _emit(
        review_id,
        ReviewEvent(type="progress", step="desk_check", agent="meta_reviewer", progress=0.2, message="Running desk check..."),
    )

    _stage_start = _time.perf_counter()
    try:
        desk_check_result = await _stage_desk_check(meta_reviewer, task_dict)
    except Exception as exc:
        logger.error("Stage 2 (Desk Check) failed: review={} error={}", review_id, exc)
        await _update_status(session, review_id, "failed")
        await _emit(
            review_id,
            ReviewEvent(type="error", step="desk_check", agent="meta_reviewer", message=f"Desk check failed: {exc}"),
        )
        return

    # Persist desk check result
    stmt = update(Review).where(Review.id == review_id).values(desk_check_result=desk_check_result.model_dump())
    await session.execute(stmt)
    await session.commit()

    await _emit(
        review_id,
        ReviewEvent(
            type="step_complete",
            step="desk_check",
            agent="meta_reviewer",
            progress=0.3,
            message="Desk check complete.",
            result=desk_check_result.model_dump(),
        ),
    )

    await _metrics.record_stage_timing(session, review_id, "desk_check", (_time.perf_counter() - _stage_start) * 1000)
    await session.commit()

    _check_cancelled(review_id)

    # -----------------------------------------------------------------------
    # Stage 3: Gate Check
    # -----------------------------------------------------------------------
    if not desk_check_result.passed:
        logger.info("Desk check FAILED for review={}: {}", review_id, desk_check_result.issues)
        await _update_status(session, review_id, "failed")
        await _emit(
            review_id,
            ReviewEvent(
                type="error",
                step="gate_check",
                message="Desk check failed. Paper does not meet requirements.",
                result={"issues": desk_check_result.issues},
            ),
        )
        return

    logger.info("Desk check PASSED for review={}", review_id)

    # -----------------------------------------------------------------------
    # Stage 4: Parallel Independent Review
    # -----------------------------------------------------------------------
    await _update_status(session, review_id, "reviewing")
    await _emit(
        review_id,
        ReviewEvent(type="progress", step="reviewing", progress=0.35, message="Starting independent reviews..."),
    )

    _stage_start = _time.perf_counter()
    reviewer_agents = {
        "core_expert": core_expert,
        "adjacent_expert": adjacent_expert,
        "methods_specialist": methods_specialist,
    }

    completed_results, failed_agents = await _stage_parallel_review(
        review_id=review_id,
        reviewer_agents=reviewer_agents,
        task_dict=task_dict,
    )

    # Persist each successful reviewer result
    for result in completed_results:
        reviewer_row = ReviewerResult(
            review_id=review_id,
            reviewer_type=result.reviewer_type,
            scores=result.scores,
            feedback=result.feedback,
            evidence=[e.__dict__ if hasattr(e, "__dict__") else e for e in result.evidence] if result.evidence else [],
        )
        session.add(reviewer_row)
    await session.commit()

    # Check for total failure
    if not completed_results:
        logger.error("Stage 4 TOTAL FAILURE: all reviewers failed for review={}", review_id)
        await _update_status(session, review_id, "failed")
        await _emit(
            review_id,
            ReviewEvent(
                type="error",
                step="reviewing",
                message="All reviewer agents failed.",
                result={"failed_agents": list(failed_agents.keys())},
            ),
        )
        return

    # Warn about partial failures
    if failed_agents:
        logger.warning(
            "Stage 4 partial failure: review={} failed_agents={}",
            review_id,
            list(failed_agents.keys()),
        )
        await _emit(
            review_id,
            ReviewEvent(
                type="info",
                step="reviewing",
                message=f"Warning: {len(failed_agents)} reviewer(s) failed. Aggregating remaining results.",
                result={"failed_agents": list(failed_agents.keys())},
            ),
        )

    await _emit(
        review_id,
        ReviewEvent(
            type="step_complete",
            step="reviewing",
            progress=0.7,
            message=f"Reviews complete. {len(completed_results)}/{len(reviewer_agents)} succeeded.",
        ),
    )

    await _metrics.record_stage_timing(session, review_id, "reviewing", (_time.perf_counter() - _stage_start) * 1000)
    await session.commit()

    _check_cancelled(review_id)

    # -----------------------------------------------------------------------
    # Stage 5: Meta Reviewer Aggregation
    # -----------------------------------------------------------------------
    await _update_status(session, review_id, "aggregating")
    await _emit(
        review_id,
        ReviewEvent(
            type="progress",
            step="aggregation",
            agent="meta_reviewer",
            progress=0.75,
            message="Aggregating reviews...",
        ),
    )

    _stage_start = _time.perf_counter()
    try:
        final_report = await _stage_aggregation(
            meta_reviewer=meta_reviewer,
            review_id=review_id,
            completed_results=completed_results,
            desk_check_result=desk_check_result,
            review_criteria=review_criteria,
        )
    except Exception as exc:
        logger.error("Stage 5 (Aggregation) failed: review={} error={}", review_id, exc)
        await _update_status(session, review_id, "failed")
        await _emit(
            review_id,
            ReviewEvent(
                type="error",
                step="aggregation",
                agent="meta_reviewer",
                message=f"Aggregation failed: {exc}",
            ),
        )
        return

    await _emit(
        review_id,
        ReviewEvent(
            type="step_complete",
            step="aggregation",
            agent="meta_reviewer",
            progress=0.9,
            message="Aggregation complete.",
        ),
    )

    await _metrics.record_stage_timing(session, review_id, "aggregation", (_time.perf_counter() - _stage_start) * 1000)
    await session.commit()

    _check_cancelled(review_id)

    # -----------------------------------------------------------------------
    # Stage 6: Report Generation & Persistence
    # -----------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    stmt = (
        update(Review)
        .where(Review.id == review_id)
        .values(
            final_report=final_report.model_dump(mode="json"),
            status="completed",
            completed_at=now,
        )
    )
    await session.execute(stmt)

    # Record total pipeline duration
    total_duration_ms = (_time.perf_counter() - _pipeline_start) * 1000
    await _metrics.record_stage_timing(session, review_id, "total", total_duration_ms)
    await session.commit()

    logger.info("Review pipeline COMPLETED: review={} duration_ms={:.0f}", review_id, total_duration_ms)

    await _emit(
        review_id,
        ReviewEvent(
            type="complete",
            step="report_generation",
            progress=1.0,
            message="Review complete.",
            report_id=review_id,
        ),
    )


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------


async def _stage_parse_document(
    session: AsyncSession,
    review_id: uuid.UUID,
) -> Any:
    """Stage 1: Parse the uploaded document(s).

    Retrieves file paths from the database and processes the primary document
    (first PDF found, or first file if no PDF).

    Returns a ``ParsedDocument`` (imported lazily to avoid docling at module level).
    """
    from backend.services.document import DocumentProcessingError, process_document

    files = await _get_file_paths(session, review_id)
    if not files:
        raise DocumentProcessingError("No files found for this review.")

    # Prefer PDF, fall back to first file
    primary_file = next(
        (f for f in files if f["file_type"] == "pdf"),
        files[0],
    )

    storage_path = primary_file["storage_path"]
    if not storage_path:
        raise DocumentProcessingError(f"File has no storage path: {primary_file['filename']}")

    parsed = await process_document(
        file_path=storage_path,
        file_type=primary_file.get("file_type"),
        resolve_refs=False,
    )
    return parsed


async def _stage_desk_check(
    meta_reviewer: AgentInterface,
    task_dict: dict[str, Any],
) -> DeskCheckResult:
    """Stage 2: Run the meta reviewer's desk check.

    The meta reviewer evaluates scope alignment and formatting.
    Returns a DeskCheckResult.
    """
    input_data = {
        "mode": "desk_check",
        "task": task_dict,
    }
    result = await meta_reviewer.execute(input_data)

    # Parse the agent output into DeskCheckResult
    return DeskCheckResult(
        passed=result.get("passed", False),
        scope_check=result.get("scope_check", {}),
        formatting_check=result.get("formatting_check", {}),
        formatting_confidence=result.get("formatting_confidence", 0.5),
        issues=result.get("issues", []),
    )


async def _stage_parallel_review(
    *,
    review_id: uuid.UUID,
    reviewer_agents: dict[str, AgentInterface],
    task_dict: dict[str, Any],
) -> tuple[list[ReviewResult], dict[str, str]]:
    """Stage 4: Run all reviewer agents in parallel.

    Each agent is INDEPENDENT -- no shared state. Individual failures
    are caught so that remaining agents can still complete.

    Returns
    -------
    tuple of (completed_results, failed_agents)
        completed_results: list of successful ReviewResult objects.
        failed_agents: dict mapping agent_name -> error_message for failures.
    """
    input_data = task_dict
    timeout_seconds = float(get_settings().agents.timeout)

    async def _run_single_reviewer(agent_name: str, agent: AgentInterface) -> ReviewResult | Exception:
        """Execute a single reviewer, returning Exception on failure."""
        try:
            await _emit(
                review_id,
                ReviewEvent(
                    type="progress",
                    step="reviewing",
                    agent=agent_name,
                    progress=0.4,
                    message=f"{agent_name} is reviewing...",
                ),
            )
            try:
                result_dict = await asyncio.wait_for(agent.execute(input_data), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise AgentTimeoutError(agent_name, timeout_seconds)
            review_result = ReviewResult(
                reviewer_type=agent_name,
                scores=result_dict.get("scores", {}),
                feedback=result_dict.get("feedback", {}),
                recommendation=result_dict.get("recommendation", "major_revision"),
                confidence=result_dict.get("confidence", 0.0),
                strengths=result_dict.get("strengths", []),
                weaknesses=result_dict.get("weaknesses", []),
            )
            await _emit(
                review_id,
                ReviewEvent(
                    type="step_complete",
                    step="reviewing",
                    agent=agent_name,
                    message=f"{agent_name} completed review.",
                ),
            )
            return review_result
        except Exception as exc:
            logger.error("Reviewer {} failed for review={}: {}", agent_name, review_id, exc)
            await _emit(
                review_id,
                ReviewEvent(
                    type="error",
                    step="reviewing",
                    agent=agent_name,
                    message=f"{agent_name} failed: {exc}",
                ),
            )
            return exc

    # Run all reviewers concurrently
    tasks = [
        _run_single_reviewer(name, agent)
        for name, agent in reviewer_agents.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    completed_results: list[ReviewResult] = []
    failed_agents: dict[str, str] = {}

    for name, result in zip(reviewer_agents.keys(), results):
        if isinstance(result, Exception):
            failed_agents[name] = str(result)
        else:
            completed_results.append(result)

    return completed_results, failed_agents


async def _stage_aggregation(
    *,
    meta_reviewer: AgentInterface,
    review_id: uuid.UUID,
    completed_results: list[ReviewResult],
    desk_check_result: DeskCheckResult,
    review_criteria: dict[str, float] | None = None,
) -> ReviewReport:
    """Stage 5: Meta Reviewer aggregates all completed reviewer reports.

    Identifies consensus, resolves conflicts, synthesizes scores,
    and produces the final ReviewReport.
    """
    # Convert ReviewResult dataclasses to dicts for the agent
    reviewer_reports_data = [r.to_dict() for r in completed_results]

    input_data = {
        "mode": "aggregate",
        "reviewer_results": reviewer_reports_data,
        "review_criteria": review_criteria or {}
    }

    result = await meta_reviewer.execute(input_data)

    # Build individual ReviewerReport schemas from completed results
    individual_reviews = [_review_result_to_reviewer_report(r) for r in completed_results]

    # Build aggregated scores
    # MetaReviewerAgent returns scores as list of {"category", "score", "reviewer_scores"}
    # or as a dict of {category: score}. Handle both formats.
    scores = []
    raw_scores = result.get("scores", [])
    if isinstance(raw_scores, list):
        for item in raw_scores:
            category = item.get("category", "")
            score_val = item.get("score", 0.0)
            reviewer_scores = {}
            for rr in completed_results:
                if category in rr.scores:
                    reviewer_scores[rr.reviewer_type] = rr.scores[category]
            scores.append(
                ReviewScore(category=category, score=score_val, reviewer_scores=reviewer_scores)
            )
    elif isinstance(raw_scores, dict):
        for category, score_val in raw_scores.items():
            reviewer_scores = {}
            for rr in completed_results:
                if category in rr.scores:
                    reviewer_scores[rr.reviewer_type] = rr.scores[category]
            scores.append(
                ReviewScore(category=category, score=score_val, reviewer_scores=reviewer_scores)
            )

    return ReviewReport(
        review_id=review_id,
        recommendation=result.get("recommendation", "major_revision"),
        confidence=result.get("confidence", "medium"),
        key_strengths=result.get("key_strengths", []),
        key_weaknesses=result.get("key_weaknesses", []),
        scores=scores,
        detailed_feedback=result.get("detailed_feedback", {}),
        suggested_improvements=result.get("suggested_improvements", []),
        individual_reviews=individual_reviews,
        desk_check=desk_check_result,
        created_at=datetime.now(timezone.utc),
    )
