"""Tests for BaseReviewer shared pipeline logic.

Tests use CoreExpertAgent as the concrete class since BaseReviewer
is abstract and cannot be instantiated directly.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.core.base import AgentStatusEnum
from agents.reviewers.core_expert import CoreExpertAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


def _research_json() -> str:
    return json.dumps({
        "key_prior_works": [
            {"title": "Prior Work", "relevance": "Relevant", "source": "arxiv"}
        ],
        "competing_approaches": [],
        "methodological_context": [],
        "red_flags": [],
        "research_summary": "Found relevant prior work.",
    })


def _analysis_json() -> str:
    return json.dumps({
        "summary": "Novel transformer architecture.",
        "technical_analysis": {
            "approach": "Sound",
            "theoretical_foundation": "Solid",
            "experimental_design": "Well-designed",
            "results_validity": "Valid",
        },
        "context_in_literature": "Advances the field.",
        "key_observations": [
            {"observation": "Novel attention", "section_reference": "Section 3", "importance": "high"}
        ],
        "questions_for_authors": ["What about longer sequences?"],
    })


def _evaluate_json() -> str:
    return json.dumps({
        "scores": {
            "novelty": 8.0,
            "methodology": 7.5,
            "significance": 8.0,
            "presentation": 7.0,
            "reproducibility": 6.5,
        },
        "evidence": [
            {
                "claim": "Novel attention mechanism",
                "source": "paper:section:3",
                "quote": "We propose multi-head attention",
                "relevance": 0.9,
            }
        ],
        "strengths": ["Highly original architecture", "Strong empirical results"],
        "weaknesses": ["Limited reproducibility details"],
    })


def _feedback_json() -> str:
    return json.dumps({
        "feedback": {
            "novelty": "Highly novel transformer architecture.",
            "methodology": "Sound experimental design.",
            "significance": "Major impact on NLP.",
            "presentation": "Well-written but dense.",
            "reproducibility": "Needs code release.",
        },
        "recommendation": "accept",
        "confidence": 0.85,
        "summary": "Strong paper recommended for acceptance.",
    })


def _all_responses():
    return [_research_json(), _analysis_json(), _evaluate_json(), _feedback_json()]


def _make_mock_llm(responses):
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(
        side_effect=[_make_llm_response(r) for r in responses]
    )
    return mock_llm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInitialization:
    @pytest.mark.asyncio
    async def test_initialize_sets_idle(self, core_expert_config) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm([])
        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
        assert agent.get_status() == AgentStatusEnum.IDLE

    @pytest.mark.asyncio
    async def test_cleanup_resets_state(self, core_expert_config) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm([])
        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            await agent.cleanup()
        assert agent.get_status() == AgentStatusEnum.IDLE
        assert agent.get_tools() == []

    @pytest.mark.asyncio
    async def test_execute_before_init_raises(self, core_expert_config, sample_task_input) -> None:
        agent = CoreExpertAgent(core_expert_config)
        with pytest.raises(RuntimeError, match="not initialised"):
            await agent.execute(sample_task_input)


class TestResearchNode:
    @pytest.mark.asyncio
    async def test_research_gathers_from_tools(
        self, core_expert_config, sample_task_input,
        mock_perplexity_tool, mock_arxiv_tool, mock_rag_tool,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        tools = [mock_perplexity_tool, mock_arxiv_tool, mock_rag_tool]
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=tools),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        mock_perplexity_tool.execute.assert_called_once()
        mock_arxiv_tool.execute.assert_called_once()
        mock_rag_tool.execute.assert_called_once()
        assert "scores" in result

    @pytest.mark.asyncio
    async def test_research_handles_tool_failure(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        failing_tool = AsyncMock()
        failing_tool.name = "perplexity"
        failing_tool.description = "Perplexity"
        failing_tool.execute = AsyncMock(side_effect=RuntimeError("API down"))

        mock_llm = _make_mock_llm(_all_responses())
        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[failing_tool]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert "scores" in result
        assert "recommendation" in result

    @pytest.mark.asyncio
    async def test_research_with_no_tools(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert result["reviewer_type"] == "core_expert"


class TestAnalyzeNode:
    @pytest.mark.asyncio
    async def test_analyze_calls_llm(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            await agent.execute(sample_task_input)

        # 4 LLM calls: research, analyze, evaluate, feedback
        assert mock_llm.complete.call_count == 4

    @pytest.mark.asyncio
    async def test_analyze_handles_json_error(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        responses = [_research_json(), "not valid json", _evaluate_json(), _feedback_json()]
        mock_llm = _make_mock_llm(responses)

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert "scores" in result


class TestEvaluateNode:
    @pytest.mark.asyncio
    async def test_evaluate_produces_scores(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert result["scores"]["novelty"] == 8.0
        assert result["scores"]["methodology"] == 7.5
        assert len(result["strengths"]) >= 1
        assert len(result["weaknesses"]) >= 1

    @pytest.mark.asyncio
    async def test_evaluate_uses_default_criteria_when_missing(
        self, core_expert_config, sample_paper_dict,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        task_input = {"paper": sample_paper_dict}
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(task_input)

        assert "scores" in result

    @pytest.mark.asyncio
    async def test_evaluate_handles_llm_failure(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        responses = [_research_json(), _analysis_json(), "broken json", _feedback_json()]
        mock_llm = _make_mock_llm(responses)

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        for score in result["scores"].values():
            assert score == 5.0


class TestGenerateFeedbackNode:
    @pytest.mark.asyncio
    async def test_feedback_produces_recommendation(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert result["recommendation"] == "accept"
        assert "novelty" in result["feedback"]

    @pytest.mark.asyncio
    async def test_feedback_handles_llm_failure(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        responses = [_research_json(), _analysis_json(), _evaluate_json(), "broken json"]
        mock_llm = _make_mock_llm(responses)

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert result["recommendation"] == "major_revision"


class TestStreaming:
    @pytest.mark.asyncio
    async def test_stream_yields_progress_events(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            events = []
            async for event in agent.stream(sample_task_input):
                events.append(event)

        assert len(events) == 4
        steps = [e.get("step") for e in events]
        assert "research" in steps
        assert "generate_feedback" in steps


class TestResultExtraction:
    @pytest.mark.asyncio
    async def test_result_has_reviewer_type(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert result["reviewer_type"] == "core_expert"

    @pytest.mark.asyncio
    async def test_result_matches_review_result_schema(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        required_keys = {
            "reviewer_type", "scores", "feedback", "evidence",
            "recommendation", "confidence", "strengths", "weaknesses",
        }
        assert required_keys.issubset(set(result.keys()))


class TestContextAndIntrospection:
    @pytest.mark.asyncio
    async def test_set_context_is_accessible(self, core_expert_config) -> None:
        agent = CoreExpertAgent(core_expert_config)
        agent.set_context({"domain_general": "CS", "review_criteria": {"novelty": 0.5}})
        assert agent._context["domain_general"] == "CS"

    def test_get_status_before_init(self, core_expert_config) -> None:
        agent = CoreExpertAgent(core_expert_config)
        assert agent.get_status() == AgentStatusEnum.IDLE

    @pytest.mark.asyncio
    async def test_status_is_completed_after_execute(
        self, core_expert_config, sample_task_input,
    ) -> None:
        agent = CoreExpertAgent(core_expert_config)
        mock_llm = _make_mock_llm(_all_responses())

        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            await agent.execute(sample_task_input)

        assert agent.get_status() == AgentStatusEnum.COMPLETED
