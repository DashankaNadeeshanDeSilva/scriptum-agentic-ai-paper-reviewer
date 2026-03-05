"""Tests for the review API endpoints."""

import io
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from backend.models.review import Feedback, File, Review

pytestmark = pytest.mark.asyncio


async def _upload_pdf(client, content: bytes = b"%PDF-1.4 test") -> str:
    """Helper: upload a PDF and return the file_id."""
    files = [("files", ("paper.pdf", io.BytesIO(content), "application/pdf"))]
    resp = await client.post("/api/v1/files/upload", files=files)
    assert resp.status_code == 200
    return resp.json()[0]["file_id"]


class TestStartReview:
    """Tests for POST /api/v1/reviews."""

    async def test_start_review_success(self, client, db_session, monkeypatch):
        """Start a review with valid file IDs."""
        file_id = await _upload_pdf(client)

        # Mock _run_review_background to avoid actually running agents
        import backend.api.v1.reviews as reviews_mod

        async def _noop_background(*args, **kwargs):
            pass

        monkeypatch.setattr(reviews_mod, "_run_review_background", _noop_background)

        body = {
            "file_ids": [file_id],
            "journal_name": "neurips",
            "domain_general": "Machine Learning",
            "domain_specific": "Deep Learning",
        }
        resp = await client.post("/api/v1/reviews", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert "review_id" in data

        # Verify Review record in DB
        review_id = UUID(data["review_id"])
        stmt = select(Review).where(Review.id == review_id)
        result = await db_session.execute(stmt)
        review = result.scalar_one_or_none()
        assert review is not None
        assert review.journal_name == "neurips"
        assert review.domain_general == "Machine Learning"

    async def test_start_review_no_pdf(self, client, monkeypatch):
        """Reject review start without a PDF file."""
        # Upload only a .tex file
        files = [("files", ("paper.tex", io.BytesIO(b"\\documentclass{article}"), "text/plain"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        file_id = resp.json()[0]["file_id"]

        body = {
            "file_ids": [file_id],
            "journal_name": "neurips",
            "domain_general": "ML",
            "domain_specific": "DL",
        }
        resp = await client.post("/api/v1/reviews", json=body)
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    async def test_start_review_invalid_file_id(self, client):
        """Reject review start with non-existent file ID."""
        body = {
            "file_ids": [str(uuid4())],
            "journal_name": "neurips",
            "domain_general": "ML",
            "domain_specific": "DL",
        }
        resp = await client.post("/api/v1/reviews", json=body)
        assert resp.status_code == 404

    async def test_start_review_creates_file_records(self, client, db_session, monkeypatch):
        """start_review links uploaded files to the Review via File records."""
        file_id = await _upload_pdf(client)

        import backend.api.v1.reviews as reviews_mod

        async def _noop_background(*args, **kwargs):
            pass

        monkeypatch.setattr(reviews_mod, "_run_review_background", _noop_background)

        body = {
            "file_ids": [file_id],
            "journal_name": "neurips",
            "domain_general": "ML",
            "domain_specific": "DL",
        }
        resp = await client.post("/api/v1/reviews", json=body)
        assert resp.status_code == 201
        review_id = UUID(resp.json()["review_id"])

        # Verify File record linked to review
        stmt = select(File).where(File.review_id == review_id)
        result = await db_session.execute(stmt)
        files = result.scalars().all()
        assert len(files) == 1
        assert str(files[0].id) == file_id
        assert files[0].file_type == "pdf"

    async def test_start_review_missing_fields(self, client):
        """Reject request with missing required fields."""
        resp = await client.post("/api/v1/reviews", json={})
        assert resp.status_code == 422  # Pydantic validation error


class TestListReviews:
    """Tests for GET /api/v1/reviews."""

    async def test_list_reviews_empty(self, client):
        """Return empty list when no reviews exist."""
        resp = await client.get("/api/v1/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["reviews"] == []

    async def test_list_reviews_with_data(self, client, db_session):
        """Return reviews when they exist."""
        # Create a review directly in DB
        review = Review(
            status="completed",
            paper_title="Test Paper",
            journal_name="neurips",
            domain_general="ML",
            domain_specific="DL",
        )
        db_session.add(review)
        await db_session.commit()

        resp = await client.get("/api/v1/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["reviews"][0]["paper_title"] == "Test Paper"
        assert data["reviews"][0]["status"] == "completed"

    async def test_list_reviews_pagination(self, client, db_session):
        """Pagination with skip and limit."""
        for i in range(5):
            db_session.add(Review(status="completed", paper_title=f"Paper {i}"))
        await db_session.commit()

        resp = await client.get("/api/v1/reviews?skip=2&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["reviews"]) == 2


class TestGetReviewStatus:
    """Tests for GET /api/v1/reviews/{review_id}."""

    async def test_get_status_pending(self, client, db_session):
        """Get status of a pending review."""
        review = Review(status="pending")
        db_session.add(review)
        await db_session.commit()

        resp = await client.get(f"/api/v1/reviews/{review.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["progress_percent"] == 0.0
        assert data["current_step"] == "waiting"

    async def test_get_status_reviewing(self, client, db_session):
        """Get status of a review in reviewing phase."""
        review = Review(status="reviewing")
        db_session.add(review)
        await db_session.commit()

        resp = await client.get(f"/api/v1/reviews/{review.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "reviewing"
        assert resp.json()["progress_percent"] == 40.0

    async def test_get_status_not_found(self, client):
        """Return 404 for non-existent review."""
        resp = await client.get(f"/api/v1/reviews/{uuid4()}")
        assert resp.status_code == 404


class TestGetReviewReport:
    """Tests for GET /api/v1/reviews/{review_id}/report."""

    async def test_get_report_completed(self, client, db_session):
        """Return report for a completed review."""
        report_data = {"recommendation": "accept", "confidence": "high"}
        review = Review(status="completed", final_report=report_data)
        db_session.add(review)
        await db_session.commit()

        resp = await client.get(f"/api/v1/reviews/{review.id}/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report"]["recommendation"] == "accept"

    async def test_get_report_not_completed(self, client, db_session):
        """Return 409 if review is not yet complete."""
        review = Review(status="reviewing")
        db_session.add(review)
        await db_session.commit()

        resp = await client.get(f"/api/v1/reviews/{review.id}/report")
        assert resp.status_code == 409

    async def test_get_report_not_found(self, client):
        """Return 404 for non-existent review."""
        resp = await client.get(f"/api/v1/reviews/{uuid4()}/report")
        assert resp.status_code == 404


class TestCancelReview:
    """Tests for DELETE /api/v1/reviews/{review_id}."""

    async def test_cancel_pending_review(self, client, db_session):
        """Cancel a pending review."""
        review = Review(status="pending")
        db_session.add(review)
        await db_session.commit()

        resp = await client.delete(f"/api/v1/reviews/{review.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_cancel_completed_review(self, client, db_session):
        """Can cancel (mark cancelled) a completed review."""
        review = Review(status="completed")
        db_session.add(review)
        await db_session.commit()

        resp = await client.delete(f"/api/v1/reviews/{review.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_cancel_not_found(self, client):
        """Return 404 for non-existent review."""
        resp = await client.delete(f"/api/v1/reviews/{uuid4()}")
        assert resp.status_code == 404


class TestSubmitFeedback:
    """Tests for POST /api/v1/reviews/{review_id}/feedback."""

    async def test_submit_feedback_success(self, client, db_session):
        """Submit valid feedback for a completed review."""
        review = Review(status="completed")
        db_session.add(review)
        await db_session.commit()

        body = {
            "rating": 4,
            "category_ratings": {"novelty": 5, "methodology": 3},
            "comments": "Very helpful review.",
        }
        resp = await client.post(f"/api/v1/reviews/{review.id}/feedback", json=body)
        assert resp.status_code == 200
        assert "Thank you" in resp.json()["message"]

        # Verify Feedback record in DB
        stmt = select(Feedback).where(Feedback.review_id == review.id)
        result = await db_session.execute(stmt)
        fb = result.scalar_one()
        assert fb.rating == 4
        assert fb.comments == "Very helpful review."

    async def test_submit_feedback_not_completed(self, client, db_session):
        """Reject feedback for a non-completed review."""
        review = Review(status="reviewing")
        db_session.add(review)
        await db_session.commit()

        body = {"rating": 3}
        resp = await client.post(f"/api/v1/reviews/{review.id}/feedback", json=body)
        assert resp.status_code == 409

    async def test_submit_feedback_invalid_rating(self, client, db_session):
        """Reject feedback with out-of-range rating."""
        review = Review(status="completed")
        db_session.add(review)
        await db_session.commit()

        body = {"rating": 10}
        resp = await client.post(f"/api/v1/reviews/{review.id}/feedback", json=body)
        assert resp.status_code == 422

    async def test_submit_feedback_not_found(self, client):
        """Return 404 for non-existent review."""
        body = {"rating": 3}
        resp = await client.post(f"/api/v1/reviews/{uuid4()}/feedback", json=body)
        assert resp.status_code == 404
