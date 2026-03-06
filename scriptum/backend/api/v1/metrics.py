"""Metrics API endpoints for observability dashboard.

Provides aggregated stats, per-review metrics, and LLM cost breakdowns.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_request_id
from backend.core.metrics import get_metrics_collector

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dashboard")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict:
    """Aggregated metrics for the dashboard overview."""
    collector = get_metrics_collector()
    return await collector.get_dashboard_stats(db)


@router.get("/reviews/{review_id}")
async def get_review_metrics(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict:
    """Per-review metrics (stage timings, agent stats, token usage)."""
    collector = get_metrics_collector()
    return await collector.get_review_metrics(db, review_id)


@router.get("/costs")
async def get_cost_summary(
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict:
    """LLM cost breakdown by agent."""
    collector = get_metrics_collector()
    return await collector.get_cost_summary(db)
