"""Tests for pipeline cancellation support in the orchestrator."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.orchestrator import (
    _PipelineCancelled,
    _check_cancelled,
    _get_cancel_event,
    _is_cancelled,
    remove_event_queue,
    request_cancellation,
    run_review_pipeline,
)


# ---------------------------------------------------------------------------
# Cancellation registry
# ---------------------------------------------------------------------------


class TestCancellationRegistry:
    def test_get_cancel_event_creates_event(self):
        review_id = uuid.uuid4()
        event = _get_cancel_event(review_id)
        assert isinstance(event, asyncio.Event)
        assert not event.is_set()
        # Cleanup
        remove_event_queue(review_id)

    def test_request_cancellation_sets_event(self):
        review_id = uuid.uuid4()
        _get_cancel_event(review_id)
        request_cancellation(review_id)
        assert _is_cancelled(review_id)
        # Cleanup
        remove_event_queue(review_id)

    def test_is_cancelled_false_before_request(self):
        review_id = uuid.uuid4()
        _get_cancel_event(review_id)
        assert not _is_cancelled(review_id)
        # Cleanup
        remove_event_queue(review_id)

    def test_is_cancelled_false_for_unknown_review(self):
        assert not _is_cancelled(uuid.uuid4())

    def test_request_cancellation_noop_for_unknown_review(self):
        # Should not raise
        request_cancellation(uuid.uuid4())

    def test_remove_event_queue_cleans_cancel_event(self):
        review_id = uuid.uuid4()
        _get_cancel_event(review_id)
        request_cancellation(review_id)
        assert _is_cancelled(review_id)
        remove_event_queue(review_id)
        assert not _is_cancelled(review_id)


# ---------------------------------------------------------------------------
# _check_cancelled
# ---------------------------------------------------------------------------


class TestCheckCancelled:
    def test_raises_when_cancelled(self):
        review_id = uuid.uuid4()
        _get_cancel_event(review_id)
        request_cancellation(review_id)

        with pytest.raises(_PipelineCancelled):
            _check_cancelled(review_id)

        # Cleanup
        remove_event_queue(review_id)

    def test_does_not_raise_when_not_cancelled(self):
        review_id = uuid.uuid4()
        _get_cancel_event(review_id)

        # Should not raise
        _check_cancelled(review_id)

        # Cleanup
        remove_event_queue(review_id)

    def test_does_not_raise_for_unknown_review(self):
        # Should not raise
        _check_cancelled(uuid.uuid4())


# ---------------------------------------------------------------------------
# Pipeline integration with cancellation
# ---------------------------------------------------------------------------


class TestPipelineCancellation:
    async def test_pipeline_sets_cancelled_status(self):
        """When cancellation is requested during a stage, the pipeline
        should catch _PipelineCancelled and set status to 'cancelled'."""
        review_id = uuid.uuid4()

        # Create mock agents
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock()

        # Mock _run_pipeline_stages to simulate cancellation after it starts
        async def fake_stages(**kwargs):
            # Simulate cancellation being requested
            request_cancellation(review_id)
            _check_cancelled(review_id)

        with (
            patch("backend.services.orchestrator.async_session_factory") as mock_session_factory,
            patch("backend.services.orchestrator._run_pipeline_stages", side_effect=fake_stages),
            patch("backend.services.orchestrator._emit", new_callable=AsyncMock) as mock_emit,
            patch("backend.services.orchestrator._emit_sentinel", new_callable=AsyncMock),
            patch("backend.services.orchestrator._update_status", new_callable=AsyncMock) as mock_update,
        ):
            # Setup session mock
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await run_review_pipeline(
                review_id,
                meta_reviewer=mock_agent,
                core_expert=mock_agent,
                adjacent_expert=mock_agent,
                methods_specialist=mock_agent,
            )

            # Should have set status to cancelled
            mock_update.assert_awaited_once_with(mock_session, review_id, "cancelled")

            # Should have emitted a cancellation event
            cancel_calls = [
                call for call in mock_emit.call_args_list
                if call.args[1].step == "cancelled"
            ]
            assert len(cancel_calls) == 1
            assert "cancelled" in cancel_calls[0].args[1].message.lower()

        # Cleanup
        remove_event_queue(review_id)

    async def test_pipeline_emits_sentinel_after_cancellation(self):
        """Sentinel should be emitted even when pipeline is cancelled."""
        review_id = uuid.uuid4()
        mock_agent = MagicMock()

        async def fake_stages(**kwargs):
            request_cancellation(review_id)
            _check_cancelled(review_id)

        with (
            patch("backend.services.orchestrator.async_session_factory") as mock_session_factory,
            patch("backend.services.orchestrator._run_pipeline_stages", side_effect=fake_stages),
            patch("backend.services.orchestrator._emit", new_callable=AsyncMock),
            patch("backend.services.orchestrator._emit_sentinel", new_callable=AsyncMock) as mock_sentinel,
            patch("backend.services.orchestrator._update_status", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await run_review_pipeline(
                review_id,
                meta_reviewer=mock_agent,
                core_expert=mock_agent,
                adjacent_expert=mock_agent,
                methods_specialist=mock_agent,
            )

            mock_sentinel.assert_awaited_once_with(review_id)

        # Cleanup
        remove_event_queue(review_id)
