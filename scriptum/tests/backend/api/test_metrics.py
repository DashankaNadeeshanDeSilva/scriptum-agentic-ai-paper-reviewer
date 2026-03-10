"""Tests for the metrics API endpoints."""

import uuid

from backend.models.review import Metric, Review


class TestMetricsDashboardEndpoint:
    async def test_dashboard_empty_db(self, client):
        resp = await client.get("/api/v1/metrics/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_reviews"] == 0
        assert body["completion_rate"] == 0.0

    async def test_dashboard_with_reviews(self, client, db_session):
        r1 = Review(status="completed", journal_name="test")
        r2 = Review(status="failed", journal_name="test")
        r3 = Review(status="processing", journal_name="test")
        db_session.add_all([r1, r2, r3])
        await db_session.commit()

        resp = await client.get("/api/v1/metrics/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_reviews"] == 3
        assert body["completed_reviews"] == 1
        assert body["failed_reviews"] == 1
        assert body["in_progress_reviews"] == 1


class TestReviewMetricsEndpoint:
    async def test_review_metrics_empty(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/metrics/reviews/{fake_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["metrics"] == {}

    async def test_review_metrics_with_data(self, client, db_session):
        review = Review(status="completed", journal_name="test")
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        m1 = Metric(
            metric_name="stage.desk_check.duration_ms", metric_value=500.0, review_id=review.id
        )
        m2 = Metric(
            metric_name="stage.reviewing.duration_ms", metric_value=3000.0, review_id=review.id
        )
        db_session.add_all([m1, m2])
        await db_session.commit()

        resp = await client.get(f"/api/v1/metrics/reviews/{review.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "stage.desk_check.duration_ms" in body["metrics"]
        assert body["metrics"]["stage.desk_check.duration_ms"][0]["value"] == 500.0


class TestCostSummaryEndpoint:
    async def test_costs_empty(self, client):
        resp = await client.get("/api/v1/metrics/costs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_cost_usd"] == 0
        assert body["total_tokens"] == 0

    async def test_costs_with_data(self, client, db_session):
        review = Review(status="completed", journal_name="test")
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        m1 = Metric(
            metric_name="agent.core_expert.llm_cost_usd", metric_value=0.05, review_id=review.id
        )
        m2 = Metric(
            metric_name="agent.core_expert.llm_tokens", metric_value=500.0, review_id=review.id
        )
        m3 = Metric(
            metric_name="agent.adjacent_expert.llm_cost_usd", metric_value=0.03, review_id=review.id
        )
        m4 = Metric(
            metric_name="agent.adjacent_expert.llm_tokens", metric_value=300.0, review_id=review.id
        )
        db_session.add_all([m1, m2, m3, m4])
        await db_session.commit()

        resp = await client.get("/api/v1/metrics/costs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_cost_usd"] == 0.08
        assert body["total_tokens"] == 800
        assert "core_expert" in body["by_agent"]

    async def test_invalid_uuid_returns_422(self, client):
        resp = await client.get("/api/v1/metrics/reviews/not-a-uuid")
        assert resp.status_code == 422
