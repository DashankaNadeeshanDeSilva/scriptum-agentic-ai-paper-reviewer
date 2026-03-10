"""Review API endpoints.

Handles the full review lifecycle: creation, status tracking, report retrieval,
cancellation, and user feedback submission.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_request_id
from backend.api.v1.files import UPLOAD_DIR
from backend.core.exceptions import ReviewNotFoundError, ReviewStateError
from backend.models.review import Feedback, File, Review
from backend.schemas.review import (
    FeedbackRequest,
    ReviewListResponse,
    ReviewStatusResponse,
    ReviewSummary,
    StartReviewRequest,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _load_journal_config(journal_name: str) -> dict | None:
    """Load journal configuration from config/journals/*.yaml by name."""
    journals_dir = Path(__file__).resolve().parents[3] / "config" / "journals"
    if not journals_dir.exists():
        return None

    # Try exact filename match first (normalised)
    normalised = journal_name.lower().replace(" ", "_").replace("-", "_")
    for yaml_path in journals_dir.glob("*.yaml"):
        if yaml_path.stem == normalised:
            with open(yaml_path) as f:
                return yaml.safe_load(f)

    # Try matching by name field inside YAML
    for yaml_path in journals_dir.glob("*.yaml"):
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            if data and data.get("name", "").lower() == journal_name.lower():
                return data
        except Exception:
            continue

    return None


def _extract_review_criteria(journal_config: dict | None) -> dict[str, float]:
    """Extract category -> weight mapping from journal config."""
    if not journal_config:
        return {}
    criteria = journal_config.get("review_criteria", {})
    return {
        cat: info.get("weight", 0.0) for cat, info in criteria.items() if isinstance(info, dict)
    }


async def _create_agents():
    """Lazily create and initialise all 4 agent instances.

    Imports are deferred to avoid pulling in heavy dependencies at module level.
    """
    from agents.meta_reviewer import MetaReviewerAgent
    from agents.reviewers import (
        AdjacentExpertAgent,
        CoreExpertAgent,
        MethodsSpecialistAgent,
    )

    meta = MetaReviewerAgent()
    core = CoreExpertAgent()
    adjacent = AdjacentExpertAgent()
    methods = MethodsSpecialistAgent()

    await meta.initialize()
    await core.initialize()
    await adjacent.initialize()
    await methods.initialize()

    return meta, core, adjacent, methods


async def _run_review_background(
    review_id: UUID,
    journal_config: dict | None,
    domain_general: str,
    domain_specific: str,
    review_criteria: dict[str, float],
) -> None:
    """Background task that creates agents and runs the review pipeline."""
    from backend.services.orchestrator import run_review_pipeline

    try:
        meta, core, adjacent, methods = await _create_agents()
        try:
            await run_review_pipeline(
                review_id=review_id,
                meta_reviewer=meta,
                core_expert=core,
                adjacent_expert=adjacent,
                methods_specialist=methods,
                journal_config=journal_config or {},
                domain_general=domain_general,
                domain_specific=domain_specific,
                review_criteria=review_criteria,
            )
        finally:
            await meta.cleanup()
            await core.cleanup()
            await adjacent.cleanup()
            await methods.cleanup()
    except Exception as exc:
        logger.exception("Background review task failed: review={} error={}", review_id, exc)


@router.post("", status_code=201)
async def start_review(
    body: StartReviewRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict:
    """Start a new paper review.

    Accepts file IDs, journal name, domain info, and optional LLM overrides.
    Creates a Review record, links uploaded files, and triggers the
    orchestrator as a background task.
    """
    # Validate that uploaded files exist on disk
    file_paths: list[dict] = []
    for file_id in body.file_ids:
        storage_dir = UPLOAD_DIR / str(file_id)
        if not storage_dir.exists():
            raise HTTPException(status_code=404, detail=f"Uploaded file not found: {file_id}")
        stored_files = list(storage_dir.iterdir())
        if not stored_files:
            raise HTTPException(status_code=404, detail=f"Uploaded file directory empty: {file_id}")
        f = stored_files[0]
        ext = f.suffix.lower()
        file_paths.append(
            {
                "file_id": file_id,
                "filename": f.name,
                "file_type": {".pdf": "pdf", ".tex": "latex", ".bib": "bibtex"}.get(ext, "unknown"),
                "storage_path": str(f),
                "size_bytes": f.stat().st_size,
            }
        )

    # Ensure at least one PDF
    has_pdf = any(fp["file_type"] == "pdf" for fp in file_paths)
    if not has_pdf:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")

    # Load journal config
    journal_config = _load_journal_config(body.journal_name)
    review_criteria = _extract_review_criteria(journal_config)

    # Create Review record
    review = Review(
        status="pending",
        journal_name=body.journal_name,
        domain_general=body.domain_general,
        domain_specific=body.domain_specific,
        llm_provider=body.llm_provider,
        llm_model=body.llm_model,
    )
    db.add(review)
    await db.flush()  # Get the generated review.id

    # Create File records linked to this review
    for fp in file_paths:
        file_record = File(
            id=fp["file_id"],
            review_id=review.id,
            file_type=fp["file_type"],
            filename=fp["filename"],
            storage_path=fp["storage_path"],
            size_bytes=fp["size_bytes"],
        )
        db.add(file_record)

    # Commit is handled by the get_db dependency's context manager

    # Schedule the review pipeline as a background task
    background_tasks.add_task(
        _run_review_background,
        review_id=review.id,
        journal_config=journal_config,
        domain_general=body.domain_general,
        domain_specific=body.domain_specific,
        review_criteria=review_criteria,
    )

    logger.info("Review started: review_id={} journal={}", review.id, body.journal_name)

    return {
        "review_id": str(review.id),
        "status": "pending",
        "message": "Review created. Processing will begin shortly.",
    }


@router.get("", response_model=ReviewListResponse)
async def list_reviews(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ReviewListResponse:
    """List all reviews with pagination."""
    # Count total
    count_stmt = select(func.count(Review.id))
    total = (await db.execute(count_stmt)).scalar_one()

    # Fetch page
    stmt = select(Review).order_by(Review.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    summaries = []
    for r in reviews:
        recommendation = None
        if r.final_report and isinstance(r.final_report, dict):
            recommendation = r.final_report.get("recommendation")

        summaries.append(
            ReviewSummary(
                review_id=r.id,
                status=r.status,
                paper_title=r.paper_title,
                journal_name=r.journal_name,
                domain_general=r.domain_general,
                domain_specific=r.domain_specific,
                llm_provider=r.llm_provider,
                llm_model=r.llm_model,
                recommendation=recommendation,
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
        )

    return ReviewListResponse(reviews=summaries, total=total)


@router.get("/{review_id}", response_model=ReviewStatusResponse)
async def get_review_status(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> ReviewStatusResponse:
    """Get the current status and progress of a review."""
    stmt = select(Review).where(Review.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise ReviewNotFoundError(review_id)

    # Map status to progress and step
    progress_map = {
        "pending": (0.0, "waiting"),
        "processing": (0.1, "document_processing"),
        "desk_check": (0.2, "desk_check"),
        "reviewing": (0.4, "reviewing"),
        "aggregating": (0.8, "aggregation"),
        "completed": (1.0, "complete"),
        "failed": (0.0, "failed"),
        "cancelled": (0.0, "cancelled"),
    }
    progress, step = progress_map.get(review.status, (0.0, "unknown"))

    return ReviewStatusResponse(
        review_id=review.id,
        status=review.status,
        current_step=step,
        progress_percent=progress * 100,
        agent_statuses={},
        estimated_time_remaining=None,
    )


@router.get("/{review_id}/report")
async def get_review_report(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict:
    """Get the final review report once complete."""
    stmt = select(Review).where(Review.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise ReviewNotFoundError(review_id)

    if review.status != "completed":
        raise ReviewStateError(f"Review is not yet complete. Current status: {review.status}")

    if not review.final_report:
        raise ReviewNotFoundError("Report data not found.")

    return {"review_id": str(review.id), "status": "completed", "report": review.final_report}


@router.delete("/{review_id}")
async def cancel_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict:
    """Cancel an in-progress review or delete a completed one."""
    stmt = select(Review).where(Review.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise ReviewNotFoundError(review_id)

    if review.status in ("completed", "failed", "cancelled"):
        # Already terminal — mark as cancelled
        stmt_update = update(Review).where(Review.id == review_id).values(status="cancelled")
        await db.execute(stmt_update)
        return {"review_id": str(review_id), "status": "cancelled", "message": "Review cancelled."}

    # Mark as cancelled (the pipeline will check status before each stage in future)
    stmt_update = update(Review).where(Review.id == review_id).values(status="cancelled")
    await db.execute(stmt_update)

    logger.info("Review cancelled: review_id={}", review_id)
    return {"review_id": str(review_id), "status": "cancelled", "message": "Review cancelled."}


@router.post("/{review_id}/feedback")
async def submit_feedback(
    review_id: UUID,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict:
    """Submit user feedback on a completed review."""
    # Verify review exists and is completed
    stmt = select(Review).where(Review.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise ReviewNotFoundError(review_id)

    if review.status != "completed":
        raise ReviewStateError(
            f"Feedback can only be submitted for completed reviews. Current status: {review.status}"
        )

    feedback = Feedback(
        review_id=review_id,
        rating=body.rating,
        category_ratings=body.category_ratings,
        comments=body.comments,
    )
    db.add(feedback)

    logger.info("Feedback submitted: review_id={} rating={}", review_id, body.rating)
    return {"review_id": str(review_id), "message": "Feedback submitted. Thank you!"}
