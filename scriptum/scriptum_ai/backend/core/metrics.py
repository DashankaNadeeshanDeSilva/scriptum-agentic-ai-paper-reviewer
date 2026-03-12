"""Metrics collection and querying for SCRIPTUM observability.

Records stage timings, LLM usage, and tool usage to the ``metrics`` table.
Provides aggregation queries for the dashboard and per-review breakdowns.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scriptum_ai.backend.models.review import Metric, Review


class MetricsCollector:
    """Async metrics collector that writes to the Metric table."""

    async def record(
        self,
        session: AsyncSession,
        metric_name: str,
        metric_value: float,
        review_id: UUID | None = None,
    ) -> None:
        """Record a single metric value."""
        metric = Metric(
            metric_name=metric_name,
            metric_value=metric_value,
            review_id=review_id,
        )
        session.add(metric)
        await session.flush()
        logger.debug("Metric recorded: {}={} review={}", metric_name, metric_value, review_id)

    async def record_stage_timing(
        self,
        session: AsyncSession,
        review_id: UUID,
        stage: str,
        duration_ms: float,
    ) -> None:
        """Record timing for a pipeline stage."""
        await self.record(session, f"stage.{stage}.duration_ms", duration_ms, review_id)

    async def record_llm_usage(
        self,
        session: AsyncSession,
        review_id: UUID,
        agent_name: str,
        tokens: int,
        cost_usd: float,
        latency_ms: float,
    ) -> None:
        """Record LLM usage metrics for an agent."""
        await self.record(session, f"agent.{agent_name}.llm_tokens", float(tokens), review_id)
        await self.record(session, f"agent.{agent_name}.llm_cost_usd", cost_usd, review_id)
        await self.record(session, f"agent.{agent_name}.response_time_ms", latency_ms, review_id)

    async def record_tool_usage(
        self,
        session: AsyncSession,
        review_id: UUID,
        tool_name: str,
        success: bool,
    ) -> None:
        """Record a tool invocation."""
        suffix = "usage_count" if success else "error_count"
        await self.record(session, f"tool.{tool_name}.{suffix}", 1.0, review_id)

    # ------------------------------------------------------------------
    # Aggregation queries
    # ------------------------------------------------------------------

    async def get_dashboard_stats(self, session: AsyncSession) -> dict[str, Any]:
        """Return aggregated stats for the dashboard."""
        # Total reviews and status counts
        total_stmt = select(func.count(Review.id))
        total = (await session.execute(total_stmt)).scalar_one()

        completed_stmt = select(func.count(Review.id)).where(Review.status == "completed")
        completed = (await session.execute(completed_stmt)).scalar_one()

        failed_stmt = select(func.count(Review.id)).where(Review.status == "failed")
        failed = (await session.execute(failed_stmt)).scalar_one()

        in_progress_stmt = select(func.count(Review.id)).where(
            Review.status.in_(["pending", "processing", "desk_check", "reviewing", "aggregating"])
        )
        in_progress = (await session.execute(in_progress_stmt)).scalar_one()

        # Average review duration (from stage timings)
        avg_duration_stmt = select(func.avg(Metric.metric_value)).where(
            Metric.metric_name == "stage.total.duration_ms"
        )
        avg_duration = (await session.execute(avg_duration_stmt)).scalar_one()

        # Total LLM cost
        cost_stmt = select(func.sum(Metric.metric_value)).where(
            Metric.metric_name.like("agent.%.llm_cost_usd")
        )
        total_cost = (await session.execute(cost_stmt)).scalar_one()

        # Completion rate
        completion_rate = (completed / total * 100) if total > 0 else 0.0

        return {
            "total_reviews": total,
            "completed_reviews": completed,
            "failed_reviews": failed,
            "in_progress_reviews": in_progress,
            "completion_rate": round(completion_rate, 1),
            "avg_review_duration_ms": round(avg_duration, 1) if avg_duration else None,
            "total_llm_cost_usd": round(total_cost, 4) if total_cost else 0.0,
        }

    async def get_review_metrics(self, session: AsyncSession, review_id: UUID) -> dict[str, Any]:
        """Return all metrics for a specific review."""
        stmt = select(Metric).where(Metric.review_id == review_id).order_by(Metric.recorded_at)
        result = await session.execute(stmt)
        metrics = result.scalars().all()

        grouped: dict[str, list[dict]] = {}
        for m in metrics:
            grouped.setdefault(m.metric_name, []).append(
                {
                    "value": m.metric_value,
                    "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
                }
            )

        return {"review_id": str(review_id), "metrics": grouped}

    async def get_cost_summary(self, session: AsyncSession) -> dict[str, Any]:
        """Return LLM cost breakdown."""
        stmt = (
            select(
                Metric.metric_name,
                func.sum(Metric.metric_value).label("total"),
                func.count(Metric.id).label("count"),
            )
            .where(Metric.metric_name.like("agent.%.llm_cost_usd"))
            .group_by(Metric.metric_name)
        )

        result = await session.execute(stmt)
        rows = result.all()

        breakdown = {}
        total = 0.0
        for row in rows:
            agent = row.metric_name.replace("agent.", "").replace(".llm_cost_usd", "")
            breakdown[agent] = {"total_cost_usd": round(row.total, 4), "invocations": row.count}
            total += row.total

        # Token totals
        token_stmt = select(func.sum(Metric.metric_value)).where(
            Metric.metric_name.like("agent.%.llm_tokens")
        )
        total_tokens = (await session.execute(token_stmt)).scalar_one()

        return {
            "total_cost_usd": round(total, 4),
            "total_tokens": int(total_tokens) if total_tokens else 0,
            "by_agent": breakdown,
        }


# Module-level singleton
_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Return the singleton MetricsCollector instance."""
    return _collector


@contextmanager
def stage_timer():
    """Context manager that measures elapsed time in milliseconds.

    Usage::

        with stage_timer() as t:
            await do_work()
        duration_ms = t()
    """
    start = time.perf_counter()
    elapsed = [0.0]

    def _get_elapsed() -> float:
        return elapsed[0]

    try:
        yield _get_elapsed
    finally:
        elapsed[0] = (time.perf_counter() - start) * 1000
