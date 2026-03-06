"""Tests for global exception handlers in main.py.

Verifies that ScriptumError subtypes, validation errors, and unhandled
exceptions produce consistent JSON error responses.

Uses the ``client`` fixture from conftest.py (in-memory SQLite + ASGI client).
"""

import uuid

import pytest

from backend.models.review import Review


class TestGlobalExceptionHandlers:
    """Verify that the global handlers return consistent JSON."""

    async def test_review_not_found_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/reviews/{fake_id}")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "ReviewNotFoundError"
        assert "message" in body

    async def test_review_feedback_not_found_returns_404(self, client):
        """Submitting feedback on a non-existent review returns 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/reviews/{fake_id}/feedback",
            json={"rating": 5, "comments": "good"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "ReviewNotFoundError"

    async def test_validation_error_returns_422(self, client):
        """Invalid body should return consistent 422 format."""
        resp = await client.post(
            "/api/v1/reviews",
            json={},  # Missing required fields
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"] == "ValidationError"
        assert "details" in body

    async def test_error_response_has_request_id(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/reviews/{fake_id}")
        body = resp.json()
        assert "request_id" in body

    async def test_review_report_not_complete_returns_409(self, client, db_session):
        """A pending review's report request returns 409."""
        review = Review(status="pending", journal_name="test")
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        resp = await client.get(f"/api/v1/reviews/{review.id}/report")
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "ReviewStateError"

    async def test_feedback_on_pending_review_returns_409(self, client, db_session):
        """Feedback on a non-completed review returns 409."""
        review = Review(status="processing", journal_name="test")
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        resp = await client.post(
            f"/api/v1/reviews/{review.id}/feedback",
            json={"rating": 5, "comments": "good"},
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "ReviewStateError"

    async def test_health_check_unaffected(self, client):
        """Health check should still return 200."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_invalid_uuid_returns_422(self, client):
        """Non-UUID review ID should return validation error."""
        resp = await client.get("/api/v1/reviews/not-a-uuid")
        assert resp.status_code == 422

    async def test_cancel_nonexistent_review_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/v1/reviews/{fake_id}")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "ReviewNotFoundError"

    async def test_error_response_format_is_consistent(self, client):
        """All error responses must have error, message, request_id keys."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/reviews/{fake_id}")
        body = resp.json()
        assert set(body.keys()) == {"error", "message", "request_id"}
