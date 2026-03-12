"""End-to-end integration tests for the review lifecycle.

Tests the full flow: upload → start review → check status → get report → submit feedback.
Agents are mocked (no real LLM calls). The orchestrator pipeline is simulated.
"""

import io
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from sqlalchemy import update

from scriptum_ai.backend.models.review import Metric, Review


class TestReviewLifecycleIntegration:
    """Full upload → review → report → feedback lifecycle."""

    async def test_upload_file(self, client, tmp_upload_dir):
        """Step 1: Upload a PDF file."""
        pdf_content = b"%PDF-1.4 test content"
        resp = await client.post(
            "/api/v1/files/upload",
            files={"files": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["filename"] == "test.pdf"
        assert body[0]["file_type"] == "pdf"
        return body[0]["file_id"]

    async def test_full_review_lifecycle(self, client, db_session, tmp_upload_dir):
        """Steps 1-5: Full lifecycle with mocked background task."""
        # Step 1: Upload
        pdf_content = b"%PDF-1.4 integration test"
        upload_resp = await client.post(
            "/api/v1/files/upload",
            files={"files": ("paper.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
        assert upload_resp.status_code == 200
        file_id = upload_resp.json()[0]["file_id"]

        # Step 2: Start review (mock the background task so it doesn't actually run)
        with patch(
            "scriptum_ai.backend.api.v1.reviews._run_review_background", new_callable=AsyncMock
        ):
            start_resp = await client.post(
                "/api/v1/reviews",
                json={
                    "file_ids": [file_id],
                    "journal_name": "NeurIPS",
                    "domain_general": "Machine Learning",
                    "domain_specific": "Transformers",
                },
            )
        assert start_resp.status_code == 201
        review_id = start_resp.json()["review_id"]

        # Step 3: Check status (should be pending since background task was mocked)
        status_resp = await client.get(f"/api/v1/reviews/{review_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "pending"

        # Simulate pipeline completion by updating the review directly
        fake_report = {
            "review_id": review_id,
            "recommendation": "minor_revision",
            "confidence": "high",
            "key_strengths": ["Novel approach"],
            "key_weaknesses": ["Limited evaluation"],
            "scores": [],
            "detailed_feedback": {},
            "suggested_improvements": ["Add more baselines"],
            "individual_reviews": [],
            "desk_check": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
        stmt = (
            update(Review)
            .where(Review.id == uuid.UUID(review_id))
            .values(
                status="completed",
                final_report=fake_report,
                completed_at=datetime.now(UTC),
            )
        )
        await db_session.execute(stmt)
        await db_session.commit()

        # Step 4: Get report
        report_resp = await client.get(f"/api/v1/reviews/{review_id}/report")
        assert report_resp.status_code == 200
        report = report_resp.json()
        assert report["report"]["recommendation"] == "minor_revision"

        # Step 5: Submit feedback
        feedback_resp = await client.post(
            f"/api/v1/reviews/{review_id}/feedback",
            json={"rating": 4, "comments": "Helpful review!"},
        )
        assert feedback_resp.status_code == 200

    async def test_list_reviews_shows_created_review(self, client, db_session, tmp_upload_dir):
        """After creating a review, it appears in the list endpoint."""
        pdf_content = b"%PDF-1.4 list test"
        upload_resp = await client.post(
            "/api/v1/files/upload",
            files={"files": ("list_test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
        file_id = upload_resp.json()[0]["file_id"]

        with patch(
            "scriptum_ai.backend.api.v1.reviews._run_review_background", new_callable=AsyncMock
        ):
            await client.post(
                "/api/v1/reviews",
                json={
                    "file_ids": [file_id],
                    "journal_name": "AAAI",
                    "domain_general": "AI",
                    "domain_specific": "Planning",
                },
            )

        list_resp = await client.get("/api/v1/reviews")
        assert list_resp.status_code == 200
        body = list_resp.json()
        assert body["total"] >= 1
        assert any(r["journal_name"] == "AAAI" for r in body["reviews"])

    async def test_cancel_review(self, client, db_session, tmp_upload_dir):
        """Cancel an in-progress review."""
        pdf_content = b"%PDF-1.4 cancel test"
        upload_resp = await client.post(
            "/api/v1/files/upload",
            files={"files": ("cancel.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
        file_id = upload_resp.json()[0]["file_id"]

        with patch(
            "scriptum_ai.backend.api.v1.reviews._run_review_background", new_callable=AsyncMock
        ):
            start_resp = await client.post(
                "/api/v1/reviews",
                json={
                    "file_ids": [file_id],
                    "journal_name": "Nature",
                    "domain_general": "Biology",
                    "domain_specific": "Genomics",
                },
            )
        review_id = start_resp.json()["review_id"]

        cancel_resp = await client.delete(f"/api/v1/reviews/{review_id}")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        # Verify status is updated
        status_resp = await client.get(f"/api/v1/reviews/{review_id}")
        assert status_resp.json()["status"] == "cancelled"

    async def test_metrics_endpoint_returns_data_after_review(
        self, client, db_session, tmp_upload_dir
    ):
        """After a review, metrics dashboard should reflect it."""
        # Create a completed review
        review = Review(status="completed", journal_name="test", completed_at=datetime.now(UTC))
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        # Add some metrics
        m = Metric(metric_name="stage.total.duration_ms", metric_value=5000.0, review_id=review.id)
        db_session.add(m)
        await db_session.commit()

        resp = await client.get("/api/v1/metrics/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_reviews"] >= 1
        assert body["completed_reviews"] >= 1


class TestUploadValidation:
    """File upload edge cases."""

    async def test_upload_non_pdf_rejected_at_upload(self, client, tmp_upload_dir):
        """Uploading a non-PDF/TeX/BibTeX file is rejected at upload time."""
        txt_content = b"This is not a PDF"
        upload_resp = await client.post(
            "/api/v1/files/upload",
            files={"files": ("notes.txt", io.BytesIO(txt_content), "text/plain")},
        )
        # The upload endpoint validates extensions
        assert upload_resp.status_code == 422 or upload_resp.status_code == 400

    async def test_start_review_with_nonexistent_file(self, client, tmp_upload_dir):
        """Starting review with a fake file ID returns 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            "/api/v1/reviews",
            json={
                "file_ids": [fake_id],
                "journal_name": "Test",
                "domain_general": "Test",
                "domain_specific": "Test",
            },
        )
        assert resp.status_code == 404


class TestSettingsIntegration:
    """Settings endpoint smoke tests."""

    async def test_get_settings(self, client):
        resp = await client.get("/api/v1/settings")
        assert resp.status_code == 200
        body = resp.json()
        assert "llm" in body

    async def test_update_settings_roundtrip(self, client):
        resp = await client.put(
            "/api/v1/settings",
            json={"agents": {"timeout": 600}},
        )
        assert resp.status_code == 200
