"""Tests for the review orchestration service.

Tests verify the full 6-stage pipeline, desk check failure path,
single reviewer failure (graceful degradation), and all reviewer failure.
All agents and database interactions are mocked.

The orchestrator uses lazy imports for docling-dependent modules, so no
module-level mocking is needed here.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.core.base import AgentInterface, Evidence, ReviewResult
from backend.schemas.review import DeskCheckResult, ReviewEvent
from backend.services.orchestrator import (
    _emit,
    _review_result_to_reviewer_report,
    _stage_desk_check,
    _stage_parallel_review,
    get_event_queue,
    remove_event_queue,
    run_review_pipeline,
)
from tools.document.models import DocumentMetadata, ParsedDocument, Section

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parsed_document() -> ParsedDocument:
    """Create a minimal ParsedDocument for testing."""
    return ParsedDocument(
        metadata=DocumentMetadata(
            title="Test Paper: A Novel Approach",
            authors=["Alice", "Bob"],
            abstract="We propose a new method.",
            source_format="pdf",
            parse_time_seconds=1.5,
        ),
        sections=[
            Section(heading="Introduction", level=1, text="This paper explores..."),
            Section(heading="Methods", level=1, text="We use a novel approach..."),
        ],
        full_text_markdown="# Test Paper\n\nThis paper explores...",
    )


def _make_mock_agent(
    return_value: dict | None = None, side_effect: Exception | None = None
) -> AsyncMock:
    """Create a mock AgentInterface with configurable execute return."""
    agent = AsyncMock(spec=AgentInterface)
    if side_effect:
        agent.execute.side_effect = side_effect
    else:
        agent.execute.return_value = return_value or {}
    return agent


def _make_desk_check_pass() -> dict:
    """Return value for a passing desk check."""
    return {
        "passed": True,
        "scope_check": {"in_scope": True},
        "formatting_check": {"valid": True},
        "formatting_confidence": 0.85,
        "issues": [],
    }


def _make_desk_check_fail() -> dict:
    """Return value for a failing desk check."""
    return {
        "passed": False,
        "scope_check": {"in_scope": False},
        "formatting_check": {"valid": True},
        "formatting_confidence": 0.6,
        "issues": ["Paper is out of scope for this journal."],
    }


def _make_reviewer_result(reviewer_type: str) -> dict:
    """Return value for a successful reviewer agent execution."""
    return {
        "scores": {"novelty": 7.0, "methodology": 8.0, "clarity": 6.5},
        "feedback": {"novelty": "Good idea.", "methodology": "Sound approach."},
        "recommendation": "minor_revision",
        "confidence": 0.8,
        "strengths": ["Novel contribution", "Clear writing"],
        "weaknesses": ["Limited evaluation"],
    }


def _make_aggregation_result() -> dict:
    """Return value for the meta reviewer aggregation."""
    return {
        "recommendation": "minor_revision",
        "confidence": "high",
        "key_strengths": ["Novel approach", "Solid methodology"],
        "key_weaknesses": ["Limited evaluation scope"],
        "scores": {"novelty": 7.5, "methodology": 8.0, "clarity": 7.0},
        "detailed_feedback": {"overall": "A solid contribution with room for improvement."},
        "suggested_improvements": ["Extend evaluation to more datasets"],
    }


async def _collect_events(review_id: uuid.UUID, timeout: float = 5.0) -> list[ReviewEvent]:
    """Collect all events from a review's queue until sentinel or timeout."""
    queue = get_event_queue(review_id)
    events = []
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=timeout)
            if event is None:
                break
            events.append(event)
    except TimeoutError:
        pass
    return events


# ---------------------------------------------------------------------------
# Mock database session factory
# ---------------------------------------------------------------------------


def _mock_session_factory():
    """Create a mock async session that simulates database operations."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    # Mock file used in Stage 1 (document parsing)
    mock_file = MagicMock()
    mock_file.id = uuid.uuid4()
    mock_file.file_type = "pdf"
    mock_file.storage_path = "/tmp/test_paper.pdf"
    mock_file.filename = "test_paper.pdf"

    async def smart_execute(stmt):
        result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [mock_file]
        result.scalars.return_value = scalars_mock
        return result

    session.execute = AsyncMock(side_effect=smart_execute)

    return session


def _make_session_context(session):
    """Wrap a mock session in an async context manager for async_session_factory."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# Event Queue Tests
# ---------------------------------------------------------------------------


class TestEventQueue:
    def test_get_event_queue_creates_queue(self):
        review_id = uuid.uuid4()
        queue = get_event_queue(review_id)
        assert isinstance(queue, asyncio.Queue)
        # Same queue on second call
        assert get_event_queue(review_id) is queue
        remove_event_queue(review_id)

    def test_remove_event_queue(self):
        review_id = uuid.uuid4()
        get_event_queue(review_id)
        remove_event_queue(review_id)
        # Should create a new one
        queue2 = get_event_queue(review_id)
        assert isinstance(queue2, asyncio.Queue)
        remove_event_queue(review_id)

    def test_remove_nonexistent_queue_no_error(self):
        remove_event_queue(uuid.uuid4())  # Should not raise

    @pytest.mark.asyncio
    async def test_emit_puts_event_on_queue(self):
        review_id = uuid.uuid4()
        event = ReviewEvent(type="info", message="test")
        await _emit(review_id, event)
        queue = get_event_queue(review_id)
        received = await queue.get()
        assert received.type == "info"
        assert received.message == "test"
        remove_event_queue(review_id)


# ---------------------------------------------------------------------------
# Stage 2: Desk Check Tests
# ---------------------------------------------------------------------------


class TestStageDeskCheck:
    @pytest.mark.asyncio
    async def test_desk_check_pass(self):
        agent = _make_mock_agent(return_value=_make_desk_check_pass())
        result = await _stage_desk_check(agent, {"paper": {}})
        assert isinstance(result, DeskCheckResult)
        assert result.passed is True
        assert result.formatting_confidence == 0.85
        assert result.issues == []

    @pytest.mark.asyncio
    async def test_desk_check_fail(self):
        agent = _make_mock_agent(return_value=_make_desk_check_fail())
        result = await _stage_desk_check(agent, {"paper": {}})
        assert result.passed is False
        assert len(result.issues) == 1

    @pytest.mark.asyncio
    async def test_desk_check_agent_error(self):
        agent = _make_mock_agent(side_effect=RuntimeError("LLM timeout"))
        with pytest.raises(RuntimeError, match="LLM timeout"):
            await _stage_desk_check(agent, {})


# ---------------------------------------------------------------------------
# Stage 4: Parallel Review Tests
# ---------------------------------------------------------------------------


class TestStageParallelReview:
    @pytest.mark.asyncio
    async def test_all_reviewers_succeed(self):
        review_id = uuid.uuid4()
        agents = {
            "core_expert": _make_mock_agent(return_value=_make_reviewer_result("core_expert")),
            "adjacent_expert": _make_mock_agent(
                return_value=_make_reviewer_result("adjacent_expert")
            ),
            "methods_specialist": _make_mock_agent(
                return_value=_make_reviewer_result("methods_specialist")
            ),
        }

        completed, failed = await _stage_parallel_review(
            review_id=review_id,
            reviewer_agents=agents,
            task_dict={"paper": {}},
        )

        assert len(completed) == 3
        assert len(failed) == 0
        assert {r.reviewer_type for r in completed} == {
            "core_expert",
            "adjacent_expert",
            "methods_specialist",
        }
        remove_event_queue(review_id)

    @pytest.mark.asyncio
    async def test_single_reviewer_fails(self):
        review_id = uuid.uuid4()
        agents = {
            "core_expert": _make_mock_agent(return_value=_make_reviewer_result("core_expert")),
            "adjacent_expert": _make_mock_agent(side_effect=RuntimeError("LLM error")),
            "methods_specialist": _make_mock_agent(
                return_value=_make_reviewer_result("methods_specialist")
            ),
        }

        completed, failed = await _stage_parallel_review(
            review_id=review_id,
            reviewer_agents=agents,
            task_dict={"paper": {}},
        )

        assert len(completed) == 2
        assert len(failed) == 1
        assert "adjacent_expert" in failed
        remove_event_queue(review_id)

    @pytest.mark.asyncio
    async def test_all_reviewers_fail(self):
        review_id = uuid.uuid4()
        agents = {
            "core_expert": _make_mock_agent(side_effect=RuntimeError("error1")),
            "adjacent_expert": _make_mock_agent(side_effect=RuntimeError("error2")),
            "methods_specialist": _make_mock_agent(side_effect=RuntimeError("error3")),
        }

        completed, failed = await _stage_parallel_review(
            review_id=review_id,
            reviewer_agents=agents,
            task_dict={"paper": {}},
        )

        assert len(completed) == 0
        assert len(failed) == 3
        remove_event_queue(review_id)

    @pytest.mark.asyncio
    async def test_reviewer_results_have_correct_scores(self):
        review_id = uuid.uuid4()
        agents = {
            "core_expert": _make_mock_agent(return_value=_make_reviewer_result("core_expert")),
        }

        completed, _ = await _stage_parallel_review(
            review_id=review_id,
            reviewer_agents=agents,
            task_dict={"paper": {}},
        )

        assert len(completed) == 1
        result = completed[0]
        assert result.scores["novelty"] == 7.0
        assert result.recommendation == "minor_revision"
        assert result.confidence == 0.8
        remove_event_queue(review_id)


# ---------------------------------------------------------------------------
# ReviewResult to ReviewerReport conversion
# ---------------------------------------------------------------------------


class TestReviewResultConversion:
    def test_converts_correctly(self):
        result = ReviewResult(
            reviewer_type="core_expert",
            scores={"novelty": 8.0},
            feedback={"novelty": "Excellent"},
            evidence=[
                Evidence(claim="novel", source="paper:1", quote="We propose...", relevance=0.9)
            ],
            recommendation="accept",
            strengths=["Great work"],
            weaknesses=["Minor issues"],
        )
        report = _review_result_to_reviewer_report(result)
        assert report.reviewer_type == "core_expert"
        assert report.scores == {"novelty": 8.0}
        assert report.recommendation == "accept"
        assert len(report.evidence) == 1
        assert report.evidence[0]["claim"] == "novel"


# ---------------------------------------------------------------------------
# Full Pipeline Tests
# ---------------------------------------------------------------------------


class TestFullPipeline:
    @pytest.mark.asyncio
    @patch("backend.services.orchestrator.async_session_factory")
    @patch("backend.services.document.process_document")
    async def test_successful_pipeline(self, mock_process_doc, mock_session_factory):
        """Test the full happy path: all 6 stages complete successfully."""
        review_id = uuid.uuid4()

        session = _mock_session_factory()
        mock_session_factory.return_value = _make_session_context(session)

        mock_process_doc.return_value = _make_parsed_document()

        # Desk check passes, then aggregation
        meta_reviewer = _make_mock_agent()
        meta_reviewer.execute = AsyncMock(
            side_effect=[
                _make_desk_check_pass(),  # Stage 2: desk check
                _make_aggregation_result(),  # Stage 5: aggregation
            ]
        )

        core_expert = _make_mock_agent(return_value=_make_reviewer_result("core_expert"))
        adjacent_expert = _make_mock_agent(return_value=_make_reviewer_result("adjacent_expert"))
        methods_specialist = _make_mock_agent(
            return_value=_make_reviewer_result("methods_specialist")
        )

        # Run pipeline in background
        pipeline_task = asyncio.create_task(
            run_review_pipeline(
                review_id,
                meta_reviewer=meta_reviewer,
                core_expert=core_expert,
                adjacent_expert=adjacent_expert,
                methods_specialist=methods_specialist,
                domain_general="Computer Science",
                domain_specific="NLP",
            )
        )

        # Collect events
        events = await _collect_events(review_id)
        await pipeline_task

        # Verify events include key milestones
        event_types = [e.type for e in events]
        assert "progress" in event_types
        assert "step_complete" in event_types
        assert "complete" in event_types

        # Verify the complete event has the report_id
        complete_events = [e for e in events if e.type == "complete"]
        assert len(complete_events) == 1
        assert complete_events[0].report_id == review_id

        # Verify all 3 reviewers were called
        core_expert.execute.assert_called_once()
        adjacent_expert.execute.assert_called_once()
        methods_specialist.execute.assert_called_once()

        # Meta reviewer called twice (desk check + aggregation)
        assert meta_reviewer.execute.call_count == 2

        remove_event_queue(review_id)

    @pytest.mark.asyncio
    @patch("backend.services.orchestrator.async_session_factory")
    @patch("backend.services.document.process_document")
    async def test_desk_check_failure_stops_pipeline(self, mock_process_doc, mock_session_factory):
        """Test that a failed desk check stops the pipeline at Stage 3."""
        review_id = uuid.uuid4()

        session = _mock_session_factory()
        mock_session_factory.return_value = _make_session_context(session)

        mock_process_doc.return_value = _make_parsed_document()

        meta_reviewer = _make_mock_agent(return_value=_make_desk_check_fail())
        core_expert = _make_mock_agent()
        adjacent_expert = _make_mock_agent()
        methods_specialist = _make_mock_agent()

        pipeline_task = asyncio.create_task(
            run_review_pipeline(
                review_id,
                meta_reviewer=meta_reviewer,
                core_expert=core_expert,
                adjacent_expert=adjacent_expert,
                methods_specialist=methods_specialist,
            )
        )

        events = await _collect_events(review_id)
        await pipeline_task

        # Should have an error event about desk check failure
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) >= 1
        assert any(
            "desk check" in (e.message or "").lower() or "gate_check" == e.step
            for e in error_events
        )

        # Reviewers should NOT have been called
        core_expert.execute.assert_not_called()
        adjacent_expert.execute.assert_not_called()
        methods_specialist.execute.assert_not_called()

        # No complete event
        assert not any(e.type == "complete" for e in events)

        remove_event_queue(review_id)

    @pytest.mark.asyncio
    @patch("backend.services.orchestrator.async_session_factory")
    @patch("backend.services.document.process_document")
    async def test_single_reviewer_failure_continues(self, mock_process_doc, mock_session_factory):
        """Test that if one reviewer fails, the others' results are still aggregated."""
        review_id = uuid.uuid4()

        session = _mock_session_factory()
        mock_session_factory.return_value = _make_session_context(session)

        mock_process_doc.return_value = _make_parsed_document()

        meta_reviewer = _make_mock_agent()
        meta_reviewer.execute = AsyncMock(
            side_effect=[
                _make_desk_check_pass(),
                _make_aggregation_result(),
            ]
        )

        core_expert = _make_mock_agent(return_value=_make_reviewer_result("core_expert"))
        adjacent_expert = _make_mock_agent(side_effect=RuntimeError("LLM provider unavailable"))
        methods_specialist = _make_mock_agent(
            return_value=_make_reviewer_result("methods_specialist")
        )

        pipeline_task = asyncio.create_task(
            run_review_pipeline(
                review_id,
                meta_reviewer=meta_reviewer,
                core_expert=core_expert,
                adjacent_expert=adjacent_expert,
                methods_specialist=methods_specialist,
            )
        )

        events = await _collect_events(review_id)
        await pipeline_task

        # Should still complete successfully
        assert any(e.type == "complete" for e in events)

        # Should have a warning/info about partial failure
        info_events = [e for e in events if e.type == "info"]
        assert any("failed" in (e.message or "").lower() for e in info_events)

        # Should have an error event for the failed reviewer
        error_events = [e for e in events if e.type == "error" and e.agent == "adjacent_expert"]
        assert len(error_events) == 1

        # Aggregation still called with 2 results
        assert meta_reviewer.execute.call_count == 2

        remove_event_queue(review_id)

    @pytest.mark.asyncio
    @patch("backend.services.orchestrator.async_session_factory")
    @patch("backend.services.document.process_document")
    async def test_all_reviewers_fail_stops_pipeline(self, mock_process_doc, mock_session_factory):
        """Test that if all reviewers fail, the pipeline stops without aggregation."""
        review_id = uuid.uuid4()

        session = _mock_session_factory()
        mock_session_factory.return_value = _make_session_context(session)

        mock_process_doc.return_value = _make_parsed_document()

        meta_reviewer = _make_mock_agent(return_value=_make_desk_check_pass())

        core_expert = _make_mock_agent(side_effect=RuntimeError("error1"))
        adjacent_expert = _make_mock_agent(side_effect=RuntimeError("error2"))
        methods_specialist = _make_mock_agent(side_effect=RuntimeError("error3"))

        pipeline_task = asyncio.create_task(
            run_review_pipeline(
                review_id,
                meta_reviewer=meta_reviewer,
                core_expert=core_expert,
                adjacent_expert=adjacent_expert,
                methods_specialist=methods_specialist,
            )
        )

        events = await _collect_events(review_id)
        await pipeline_task

        # Should have error about all reviewers failing
        error_events = [e for e in events if e.type == "error"]
        assert any("all reviewer" in (e.message or "").lower() for e in error_events)

        # No complete event
        assert not any(e.type == "complete" for e in events)

        # Meta reviewer only called once (desk check), NOT for aggregation
        meta_reviewer.execute.assert_called_once()

        remove_event_queue(review_id)

    @pytest.mark.asyncio
    @patch("backend.services.orchestrator.async_session_factory")
    @patch("backend.services.document.process_document")
    async def test_document_parsing_failure(self, mock_process_doc, mock_session_factory):
        """Test that a document parsing failure stops the pipeline at Stage 1."""
        review_id = uuid.uuid4()

        session = _mock_session_factory()
        mock_session_factory.return_value = _make_session_context(session)

        mock_process_doc.side_effect = FileNotFoundError("Document not found")

        meta_reviewer = _make_mock_agent()
        core_expert = _make_mock_agent()
        adjacent_expert = _make_mock_agent()
        methods_specialist = _make_mock_agent()

        pipeline_task = asyncio.create_task(
            run_review_pipeline(
                review_id,
                meta_reviewer=meta_reviewer,
                core_expert=core_expert,
                adjacent_expert=adjacent_expert,
                methods_specialist=methods_specialist,
            )
        )

        events = await _collect_events(review_id)
        await pipeline_task

        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) >= 1
        assert any("document_processing" == e.step for e in error_events)

        # No agents should be called
        meta_reviewer.execute.assert_not_called()
        core_expert.execute.assert_not_called()

        remove_event_queue(review_id)

    @pytest.mark.asyncio
    @patch("backend.services.orchestrator.async_session_factory")
    @patch("backend.services.document.process_document")
    async def test_aggregation_failure(self, mock_process_doc, mock_session_factory):
        """Test that aggregation failure marks review as failed but individual reviews are saved."""
        review_id = uuid.uuid4()

        session = _mock_session_factory()
        mock_session_factory.return_value = _make_session_context(session)

        mock_process_doc.return_value = _make_parsed_document()

        meta_reviewer = _make_mock_agent()
        meta_reviewer.execute = AsyncMock(
            side_effect=[
                _make_desk_check_pass(),
                RuntimeError("Aggregation LLM timeout"),  # Stage 5 fails
            ]
        )

        core_expert = _make_mock_agent(return_value=_make_reviewer_result("core_expert"))
        adjacent_expert = _make_mock_agent(return_value=_make_reviewer_result("adjacent_expert"))
        methods_specialist = _make_mock_agent(
            return_value=_make_reviewer_result("methods_specialist")
        )

        pipeline_task = asyncio.create_task(
            run_review_pipeline(
                review_id,
                meta_reviewer=meta_reviewer,
                core_expert=core_expert,
                adjacent_expert=adjacent_expert,
                methods_specialist=methods_specialist,
            )
        )

        events = await _collect_events(review_id)
        await pipeline_task

        # Should have error about aggregation failure
        error_events = [e for e in events if e.type == "error"]
        assert any("aggregation" == e.step for e in error_events)

        # Individual reviews should have been saved (session.add called 3 times)
        assert session.add.call_count == 3

        # No complete event
        assert not any(e.type == "complete" for e in events)

        remove_event_queue(review_id)

    @pytest.mark.asyncio
    @patch("backend.services.orchestrator.async_session_factory")
    @patch("backend.services.document.process_document")
    async def test_pipeline_emits_progress_events(self, mock_process_doc, mock_session_factory):
        """Test that progress events are emitted at each stage transition."""
        review_id = uuid.uuid4()

        session = _mock_session_factory()
        mock_session_factory.return_value = _make_session_context(session)

        mock_process_doc.return_value = _make_parsed_document()

        meta_reviewer = _make_mock_agent()
        meta_reviewer.execute = AsyncMock(
            side_effect=[
                _make_desk_check_pass(),
                _make_aggregation_result(),
            ]
        )

        core_expert = _make_mock_agent(return_value=_make_reviewer_result("core_expert"))
        adjacent_expert = _make_mock_agent(return_value=_make_reviewer_result("adjacent_expert"))
        methods_specialist = _make_mock_agent(
            return_value=_make_reviewer_result("methods_specialist")
        )

        pipeline_task = asyncio.create_task(
            run_review_pipeline(
                review_id,
                meta_reviewer=meta_reviewer,
                core_expert=core_expert,
                adjacent_expert=adjacent_expert,
                methods_specialist=methods_specialist,
            )
        )

        events = await _collect_events(review_id)
        await pipeline_task

        # Verify progress events exist for key stages
        progress_events = [e for e in events if e.type == "progress"]
        progress_steps = {e.step for e in progress_events}
        assert "document_processing" in progress_steps
        assert "desk_check" in progress_steps
        assert "reviewing" in progress_steps
        assert "aggregation" in progress_steps

        # Verify step_complete events
        step_complete_events = [e for e in events if e.type == "step_complete"]
        complete_steps = {e.step for e in step_complete_events}
        assert "document_processing" in complete_steps
        assert "desk_check" in complete_steps
        assert "reviewing" in complete_steps
        assert "aggregation" in complete_steps

        remove_event_queue(review_id)
