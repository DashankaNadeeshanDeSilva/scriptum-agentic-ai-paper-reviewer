"""Tests for the MetricsCollector service."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from scriptum_ai.backend.core.database import Base
from scriptum_ai.backend.core.metrics import MetricsCollector, get_metrics_collector, stage_timer
from scriptum_ai.backend.models.review import Metric, Review


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite session with schema."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def review_id(db):
    """Create a review and return its ID."""
    review = Review(status="completed", journal_name="test")
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review.id


class TestMetricsCollector:
    async def test_record_basic(self, db):
        collector = MetricsCollector()
        await collector.record(db, "test.metric", 42.0)
        await db.commit()

        from sqlalchemy import select

        result = await db.execute(select(Metric).where(Metric.metric_name == "test.metric"))
        metric = result.scalar_one()
        assert metric.metric_value == 42.0
        assert metric.review_id is None

    async def test_record_with_review_id(self, db, review_id):
        collector = MetricsCollector()
        await collector.record(db, "test.metric", 10.0, review_id=review_id)
        await db.commit()

        from sqlalchemy import select

        result = await db.execute(select(Metric).where(Metric.review_id == review_id))
        metric = result.scalar_one()
        assert metric.metric_value == 10.0

    async def test_record_stage_timing(self, db, review_id):
        collector = MetricsCollector()
        await collector.record_stage_timing(db, review_id, "desk_check", 1234.5)
        await db.commit()

        from sqlalchemy import select

        result = await db.execute(
            select(Metric).where(Metric.metric_name == "stage.desk_check.duration_ms")
        )
        metric = result.scalar_one()
        assert metric.metric_value == 1234.5

    async def test_record_llm_usage(self, db, review_id):
        collector = MetricsCollector()
        await collector.record_llm_usage(db, review_id, "core_expert", 500, 0.05, 2000.0)
        await db.commit()

        from sqlalchemy import select

        result = await db.execute(
            select(Metric).where(Metric.metric_name == "agent.core_expert.llm_tokens")
        )
        metric = result.scalar_one()
        assert metric.metric_value == 500.0

    async def test_record_tool_usage_success(self, db, review_id):
        collector = MetricsCollector()
        await collector.record_tool_usage(db, review_id, "arxiv", True)
        await db.commit()

        from sqlalchemy import select

        result = await db.execute(
            select(Metric).where(Metric.metric_name == "tool.arxiv.usage_count")
        )
        assert result.scalar_one().metric_value == 1.0

    async def test_record_tool_usage_failure(self, db, review_id):
        collector = MetricsCollector()
        await collector.record_tool_usage(db, review_id, "arxiv", False)
        await db.commit()

        from sqlalchemy import select

        result = await db.execute(
            select(Metric).where(Metric.metric_name == "tool.arxiv.error_count")
        )
        assert result.scalar_one().metric_value == 1.0

    async def test_get_dashboard_stats_empty(self, db):
        collector = MetricsCollector()
        stats = await collector.get_dashboard_stats(db)
        assert stats["total_reviews"] == 0
        assert stats["completion_rate"] == 0.0

    async def test_get_dashboard_stats_with_data(self, db, review_id):
        collector = MetricsCollector()
        await collector.record_stage_timing(db, review_id, "total", 5000.0)
        await collector.record_llm_usage(db, review_id, "core_expert", 100, 0.01, 500.0)
        await db.commit()

        stats = await collector.get_dashboard_stats(db)
        assert stats["total_reviews"] == 1
        assert stats["completed_reviews"] == 1
        assert stats["total_llm_cost_usd"] == 0.01

    async def test_get_review_metrics(self, db, review_id):
        collector = MetricsCollector()
        await collector.record_stage_timing(db, review_id, "desk_check", 100.0)
        await collector.record_stage_timing(db, review_id, "reviewing", 2000.0)
        await db.commit()

        result = await collector.get_review_metrics(db, review_id)
        assert result["review_id"] == str(review_id)
        assert "stage.desk_check.duration_ms" in result["metrics"]
        assert "stage.reviewing.duration_ms" in result["metrics"]

    async def test_get_cost_summary_empty(self, db):
        collector = MetricsCollector()
        result = await collector.get_cost_summary(db)
        assert result["total_cost_usd"] == 0
        assert result["total_tokens"] == 0

    async def test_get_cost_summary_with_data(self, db, review_id):
        collector = MetricsCollector()
        await collector.record_llm_usage(db, review_id, "core_expert", 500, 0.05, 1000.0)
        await collector.record_llm_usage(db, review_id, "adjacent_expert", 300, 0.03, 800.0)
        await db.commit()

        result = await collector.get_cost_summary(db)
        assert result["total_cost_usd"] == 0.08
        assert result["total_tokens"] == 800
        assert "core_expert" in result["by_agent"]
        assert "adjacent_expert" in result["by_agent"]


class TestGetMetricsCollector:
    def test_returns_singleton(self):
        c1 = get_metrics_collector()
        c2 = get_metrics_collector()
        assert c1 is c2


class TestStageTimer:
    def test_measures_elapsed_time(self):
        import time

        with stage_timer() as elapsed:
            time.sleep(0.01)
        assert elapsed() >= 10.0  # at least 10ms
