"""Review API endpoints.

Handles the full review lifecycle: creation, status tracking, report retrieval,
cancellation, and user feedback submission.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends

from backend.api.deps import get_request_id

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("")
async def start_review(
    request_id: str = Depends(get_request_id),
) -> dict:
    """Start a new paper review.

    Accepts file IDs, journal name, domain info, and optional LLM overrides.
    Triggers the review orchestrator as a background task.
    """
    # TODO: Parse StartReviewRequest body, validate file_ids exist
    # TODO: Create review record in DB
    # TODO: Trigger orchestrator background task
    review_id = uuid4()
    return {
        "review_id": str(review_id),
        "status": "pending",
        "message": "Review created. Processing will begin shortly.",
    }


@router.get("")
async def list_reviews(
    request_id: str = Depends(get_request_id),
) -> dict:
    """List all reviews for the current user."""
    # TODO: Query reviews from DB, filter by user
    return {
        "reviews": [],
        "total": 0,
    }


@router.get("/{review_id}")
async def get_review_status(
    review_id: UUID,
    request_id: str = Depends(get_request_id),
) -> dict:
    """Get the current status and progress of a review."""
    # TODO: Fetch review from DB by ID
    # TODO: Include agent statuses and progress
    return {
        "review_id": str(review_id),
        "status": "pending",
        "current_step": "not_started",
        "progress_percent": 0.0,
        "agent_statuses": {},
        "estimated_time_remaining": None,
    }


@router.get("/{review_id}/report")
async def get_review_report(
    review_id: UUID,
    request_id: str = Depends(get_request_id),
) -> dict:
    """Get the final review report once complete."""
    # TODO: Fetch final_report JSON from reviews table
    # TODO: Return 404 if not found, 409 if not yet complete
    return {
        "review_id": str(review_id),
        "status": "pending",
        "report": None,
        "message": "Report not yet available.",
    }


@router.delete("/{review_id}")
async def cancel_review(
    review_id: UUID,
    request_id: str = Depends(get_request_id),
) -> dict:
    """Cancel an in-progress review or delete a completed one."""
    # TODO: Cancel background orchestrator task if running
    # TODO: Update review status in DB
    return {
        "review_id": str(review_id),
        "status": "cancelled",
        "message": "Review cancelled.",
    }


@router.post("/{review_id}/feedback")
async def submit_feedback(
    review_id: UUID,
    request_id: str = Depends(get_request_id),
) -> dict:
    """Submit user feedback on a completed review.

    Accepts a rating (1-5), optional category ratings, and comments.
    """
    # TODO: Parse feedback body (rating, category_ratings, comments)
    # TODO: Store in feedback table
    return {
        "review_id": str(review_id),
        "message": "Feedback submitted. Thank you!",
    }
