"""Tests for the MetaReviewerAgent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.core.base import AgentConfig, AgentStatusEnum
from agents.meta_reviewer.agent import MetaReviewerAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


def _scope_ok_json() -> str:
    return json.dumps({
        "in_scope": True,
        "reasoning": "Paper is on Transformer architectures, within NLP scope.",
        "confidence": 0.9,
        "scope_match_areas": ["NLP", "deep learning"],
        "scope_concerns": [],
    })


def _scope_fail_json() -> str:
    return json.dumps({
        "in_scope": False,
        "reasoning": "Paper is about geology, not NLP.",
        "confidence": 0.95,
        "scope_match_areas": [],
        "scope_concerns": ["Topic is geology, not language processing"],
    })


def _formatting_ok_json() -> str:
    return json.dumps({
        "passes": True,
        "issues": [
            {"rule": "page_limit", "status": "pass", "detail": "11 pages within 14 limit"},
        ],
        "confidence": 0.85,
        "missing_sections": [],
    })


def _formatting_fail_json() -> str:
    return json.dumps({
        "passes": False,
        "issues": [
            {"rule": "page_limit", "status": "fail", "detail": "20 pages exceeds 14 limit"},
            {"rule": "required_sections", "status": "fail", "detail": "Missing Related Work section"},
        ],
        "confidence": 0.8,
        "missing_sections": ["Related Work"],
    })


def _analysis_json() -> str:
    return json.dumps({
        "consensus": [{"category": "novelty", "agreed_assessment": "High novelty", "avg_score": 7.5}],
        "conflicts": [
            {
                "category": "reproducibility",
                "scores": {"core_expert": 6.5, "adjacent_expert": 5.0},
                "nature": "Disagreement on code availability impact",
            }
        ],
        "unique_insights": [],
    })


def _synthesis_json() -> str:
    return json.dumps({
        "weighted_scores": {
            "novelty": 7.5,
            "methodology": 7.3,
            "significance": 8.2,
            "presentation": 7.3,
            "reproducibility": 6.2,
        },
        "overall_score": 7.3,
        "conflict_resolutions": [
            {
                "category": "reproducibility",
                "final_score": 6.2,
                "resolution_reasoning": "Methods specialist has strongest expertise here.",
            }
        ],
        "recommendation": "accept",
        "confidence": "high",
    })


def _report_json() -> str:
    return json.dumps({
        "recommendation": "accept",
        "confidence": "high",
        "key_strengths": ["Novel architecture", "Strong results", "Broad impact"],
        "key_weaknesses": ["Reproducibility concerns"],
        "detailed_feedback": {
            "novelty": "Highly novel attention-only approach.",
            "methodology": "Sound experimental methodology.",
        },
        "suggested_improvements": ["Release code and trained models"],
        "executive_summary": "Strong paper with novel contributions. Recommend accept.",
    })


# ---------------------------------------------------------------------------
# Test helpers for patching
# ---------------------------------------------------------------------------


def _patch_llm_and_tools(
    meta_config,
    mock_rag_tool,
    mock_perplexity_tool,
    mock_google_tool,
    llm_responses: list[str],
):
    """Return context managers that patch LLMClient and tool factory."""
    call_count = {"i": 0}
    responses = llm_responses

    async def mock_complete(*args, **kwargs):
        idx = min(call_count["i"], len(responses) - 1)
        call_count["i"] += 1
        return _make_llm_response(responses[idx])

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(side_effect=mock_complete)

    tool_list = [mock_rag_tool, mock_perplexity_tool, mock_google_tool]

    llm_patch = patch(
        "agents.meta_reviewer.agent.LLMClient",
        return_value=mock_llm,
    )
    tools_patch = patch(
        "agents.meta_reviewer.agent.create_meta_reviewer_tools",
        return_value=tool_list,
    )
    return llm_patch, tools_patch, mock_llm


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


class TestInitialization:
    @pytest.mark.asyncio
    async def test_initialize_creates_llm_and_graphs(
        self, meta_config, mock_rag_tool, mock_perplexity_tool, mock_google_tool
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config, mock_rag_tool, mock_perplexity_tool, mock_google_tool, []
        )
        with llm_p, tools_p:
            await agent.initialize()

        assert agent._llm is not None
        assert agent._desk_check_graph is not None
        assert agent._aggregation_graph is not None
        assert len(agent.get_tools()) == 3
        assert agent.get_status() == AgentStatusEnum.IDLE

    @pytest.mark.asyncio
    async def test_cleanup_resets_state(
        self, meta_config, mock_rag_tool, mock_perplexity_tool, mock_google_tool
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config, mock_rag_tool, mock_perplexity_tool, mock_google_tool, []
        )
        with llm_p, tools_p:
            await agent.initialize()
            await agent.cleanup()

        assert agent._llm is None
        assert agent._tools == []
        assert agent._desk_check_graph is None
        assert agent._aggregation_graph is None
        assert agent.get_status() == AgentStatusEnum.IDLE

    @pytest.mark.asyncio
    async def test_desk_check_not_initialized_raises(self, meta_config) -> None:
        agent = MetaReviewerAgent(meta_config)
        with pytest.raises(RuntimeError, match="not initialised"):
            await agent.desk_check({"task": {}})

    @pytest.mark.asyncio
    async def test_aggregate_not_initialized_raises(self, meta_config) -> None:
        agent = MetaReviewerAgent(meta_config)
        with pytest.raises(RuntimeError, match="not initialised"):
            await agent.aggregate({"reviewer_results": []})


# ---------------------------------------------------------------------------
# Desk check tests
# ---------------------------------------------------------------------------


class TestDeskCheck:
    @pytest.mark.asyncio
    async def test_happy_path_passes(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
        sample_journal_config,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, mock_llm = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_scope_ok_json(), _formatting_ok_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})
            result = await agent.desk_check({
                "task": {"paper": sample_paper_dict, "journal_config": sample_journal_config}
            })

        assert result["passed"] is True
        assert result["scope_check"]["in_scope"] is True
        assert result["formatting_check"]["passes"] is True
        assert result["formatting_confidence"] > 0
        assert result["issues"] == []

    @pytest.mark.asyncio
    async def test_scope_fails(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_scope_fail_json(), _formatting_ok_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})
            result = await agent.desk_check({"task": {"paper": sample_paper_dict}})

        assert result["passed"] is False
        assert result["scope_check"]["in_scope"] is False
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_formatting_fails(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_scope_ok_json(), _formatting_fail_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})
            result = await agent.desk_check({"task": {"paper": sample_paper_dict}})

        assert result["passed"] is False
        assert len(result["issues"]) >= 1

    @pytest.mark.asyncio
    async def test_both_fail(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_scope_fail_json(), _formatting_fail_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})
            result = await agent.desk_check({"task": {"paper": sample_paper_dict}})

        assert result["passed"] is False
        assert len(result["issues"]) >= 2

    @pytest.mark.asyncio
    async def test_tools_fail_gracefully(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
        sample_journal_config,
    ) -> None:
        # Make all tools raise exceptions
        mock_rag_tool.execute = AsyncMock(side_effect=Exception("RAG down"))
        mock_rag_tool.store = AsyncMock(side_effect=Exception("RAG down"))
        mock_perplexity_tool.execute = AsyncMock(side_effect=Exception("API down"))
        mock_google_tool.execute = AsyncMock(side_effect=Exception("API down"))

        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_scope_ok_json(), _formatting_ok_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})
            result = await agent.desk_check({
                "task": {"paper": sample_paper_dict, "journal_config": sample_journal_config}
            })

        # Should still produce a result despite tool failures
        assert "passed" in result
        assert "scope_check" in result

    @pytest.mark.asyncio
    async def test_stores_research_in_rag(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_scope_ok_json(), _formatting_ok_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})
            await agent.desk_check({"task": {"paper": sample_paper_dict}})

        # Verify RAG store was called with discovered snippets
        mock_rag_tool.store.assert_called()

    @pytest.mark.asyncio
    async def test_json_parse_error_handled(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        # Return invalid JSON for scope, valid for formatting
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            ["not valid json {{{", _formatting_ok_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})
            result = await agent.desk_check({"task": {"paper": sample_paper_dict}})

        # Should return a default result, not crash
        assert "passed" in result
        assert result["scope_check"]["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Aggregation tests
# ---------------------------------------------------------------------------


class TestAggregation:
    @pytest.mark.asyncio
    async def test_happy_path(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_reviewer_results,
        sample_review_criteria,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_analysis_json(), _synthesis_json(), _report_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            result = await agent.aggregate({
                "reviewer_results": sample_reviewer_results,
                "review_criteria": sample_review_criteria,
            })

        assert result["recommendation"] == "accept"
        assert result["confidence"] == "high"
        assert len(result["key_strengths"]) > 0
        assert len(result["scores"]) > 0
        assert "executive_summary" in result

    @pytest.mark.asyncio
    async def test_conflict_resolution(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_reviewer_results,
        sample_review_criteria,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, mock_llm = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_analysis_json(), _synthesis_json(), _report_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            result = await agent.aggregate({
                "reviewer_results": sample_reviewer_results,
                "review_criteria": sample_review_criteria,
            })

        # LLM was called 3 times (analyze, synthesize, report)
        assert mock_llm.complete.await_count == 3

    @pytest.mark.asyncio
    async def test_reject_recommendation(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_reviewer_results,
        sample_review_criteria,
    ) -> None:
        reject_synthesis = json.dumps({
            "weighted_scores": {"novelty": 3.0, "methodology": 2.5},
            "overall_score": 2.8,
            "conflict_resolutions": [],
            "recommendation": "reject",
            "confidence": "high",
        })
        reject_report = json.dumps({
            "recommendation": "reject",
            "confidence": "high",
            "key_strengths": [],
            "key_weaknesses": ["Fundamental flaws in methodology"],
            "detailed_feedback": {"methodology": "Critical errors in analysis"},
            "suggested_improvements": ["Complete rewrite needed"],
            "executive_summary": "Paper has fundamental flaws. Reject.",
        })

        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_analysis_json(), reject_synthesis, reject_report],
        )
        with llm_p, tools_p:
            await agent.initialize()
            result = await agent.aggregate({
                "reviewer_results": sample_reviewer_results,
                "review_criteria": sample_review_criteria,
            })

        assert result["recommendation"] == "reject"

    @pytest.mark.asyncio
    async def test_json_parse_error_in_aggregation(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_reviewer_results,
        sample_review_criteria,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            ["invalid json", "invalid json", "invalid json"],
        )
        with llm_p, tools_p:
            await agent.initialize()
            result = await agent.aggregate({
                "reviewer_results": sample_reviewer_results,
                "review_criteria": sample_review_criteria,
            })

        # Should return defaults, not crash
        assert result["recommendation"] == "major_revision"
        assert result["confidence"] == "low"

    @pytest.mark.asyncio
    async def test_empty_reviewer_results(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_analysis_json(), _synthesis_json(), _report_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            result = await agent.aggregate({
                "reviewer_results": [],
                "review_criteria": {},
            })

        # Should still produce a result
        assert "recommendation" in result


# ---------------------------------------------------------------------------
# Execute routing tests
# ---------------------------------------------------------------------------


class TestExecuteRouting:
    @pytest.mark.asyncio
    async def test_routes_desk_check(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_scope_ok_json(), _formatting_ok_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})
            result = await agent.execute({
                "mode": "desk_check",
                "task": {"paper": sample_paper_dict},
            })

        assert "passed" in result  # desk check output

    @pytest.mark.asyncio
    async def test_routes_aggregate(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_reviewer_results,
        sample_review_criteria,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_analysis_json(), _synthesis_json(), _report_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            result = await agent.execute({
                "mode": "aggregate",
                "reviewer_results": sample_reviewer_results,
                "review_criteria": sample_review_criteria,
            })

        assert "recommendation" in result  # aggregation output

    @pytest.mark.asyncio
    async def test_unknown_mode_raises(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [],
        )
        with llm_p, tools_p:
            await agent.initialize()
            with pytest.raises(ValueError, match="Unknown"):
                await agent.execute({"mode": "invalid"})


# ---------------------------------------------------------------------------
# Streaming tests
# ---------------------------------------------------------------------------


class TestStreaming:
    @pytest.mark.asyncio
    async def test_stream_desk_check_emits_events(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_paper_dict,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_scope_ok_json(), _formatting_ok_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()
            agent.set_context({"journal_name": "Nature"})

            events = []
            async for event in agent.stream({
                "mode": "desk_check",
                "task": {"paper": sample_paper_dict},
            }):
                events.append(event)

        # 3 nodes = 3 events
        assert len(events) == 3
        assert events[-1].get("progress", 0) == 1.0

    @pytest.mark.asyncio
    async def test_stream_aggregation_emits_events(
        self,
        meta_config,
        mock_rag_tool,
        mock_perplexity_tool,
        mock_google_tool,
        sample_reviewer_results,
        sample_review_criteria,
    ) -> None:
        agent = MetaReviewerAgent(meta_config)
        llm_p, tools_p, _ = _patch_llm_and_tools(
            meta_config,
            mock_rag_tool,
            mock_perplexity_tool,
            mock_google_tool,
            [_analysis_json(), _synthesis_json(), _report_json()],
        )
        with llm_p, tools_p:
            await agent.initialize()

            events = []
            async for event in agent.stream({
                "mode": "aggregate",
                "reviewer_results": sample_reviewer_results,
                "review_criteria": sample_review_criteria,
            }):
                events.append(event)

        assert len(events) == 3
        assert events[-1].get("progress", 0) == 1.0


# ---------------------------------------------------------------------------
# Context and introspection
# ---------------------------------------------------------------------------


class TestContextAndIntrospection:
    def test_set_context(self, meta_config) -> None:
        agent = MetaReviewerAgent(meta_config)
        agent.set_context({"journal_name": "NeurIPS", "domain": "ML"})
        assert agent._context["journal_name"] == "NeurIPS"

    def test_default_status_is_idle(self, meta_config) -> None:
        agent = MetaReviewerAgent(meta_config)
        assert agent.get_status() == AgentStatusEnum.IDLE

    def test_default_config(self) -> None:
        agent = MetaReviewerAgent()
        assert agent._config.agent_type == "meta_reviewer"
