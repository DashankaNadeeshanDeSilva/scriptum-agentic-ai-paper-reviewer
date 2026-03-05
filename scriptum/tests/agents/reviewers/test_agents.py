"""Tests for the three concrete reviewer agents.

Tests that each agent has the correct identity, tools, and perspective.
Full pipeline tests are in test_base.py (shared logic).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.core.base import AgentConfig, AgentStatusEnum
from agents.reviewers.adjacent_expert import AdjacentExpertAgent
from agents.reviewers.core_expert import CoreExpertAgent
from agents.reviewers.methods_specialist import MethodsSpecialistAgent
from agents.reviewers.prompts import (
    ADJACENT_EXPERT_SYSTEM,
    CORE_EXPERT_SYSTEM,
    METHODS_SPECIALIST_SYSTEM,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


def _all_responses():
    return [
        json.dumps({"key_prior_works": [], "competing_approaches": [], "methodological_context": [], "red_flags": [], "research_summary": "OK"}),
        json.dumps({"summary": "OK", "technical_analysis": {}, "context_in_literature": "", "key_observations": [], "questions_for_authors": []}),
        json.dumps({"scores": {"novelty": 7.0, "methodology": 7.0, "significance": 7.0, "presentation": 7.0, "reproducibility": 7.0}, "evidence": [], "strengths": ["Good"], "weaknesses": ["OK"]}),
        json.dumps({"feedback": {"novelty": "Good"}, "recommendation": "minor_revision", "confidence": 0.7, "summary": "Solid work."}),
    ]


# ---------------------------------------------------------------------------
# Core Expert
# ---------------------------------------------------------------------------


class TestCoreExpert:
    def test_default_agent_type(self) -> None:
        agent = CoreExpertAgent()
        assert agent._config.agent_type == "core_expert"

    def test_system_prompt(self) -> None:
        agent = CoreExpertAgent()
        assert agent.system_prompt == CORE_EXPERT_SYSTEM
        assert "domain specialist" in agent.system_prompt.lower()

    def test_perspective(self) -> None:
        agent = CoreExpertAgent()
        assert "domain" in agent.perspective.lower()

    def test_focus_areas(self) -> None:
        agent = CoreExpertAgent()
        assert "novelty" in agent.focus_areas
        assert "methodology" in agent.focus_areas

    def test_custom_config(self) -> None:
        config = AgentConfig(agent_type="core_expert", provider="anthropic", model="claude-3")
        agent = CoreExpertAgent(config)
        assert agent._config.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_full_pipeline(self, sample_task_input) -> None:
        agent = CoreExpertAgent()
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            side_effect=[_make_llm_response(r) for r in _all_responses()]
        )
        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(CoreExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert result["reviewer_type"] == "core_expert"
        assert result["recommendation"] == "minor_revision"


# ---------------------------------------------------------------------------
# Adjacent Expert
# ---------------------------------------------------------------------------


class TestAdjacentExpert:
    def test_default_agent_type(self) -> None:
        agent = AdjacentExpertAgent()
        assert agent._config.agent_type == "adjacent_expert"

    def test_system_prompt(self) -> None:
        agent = AdjacentExpertAgent()
        assert agent.system_prompt == ADJACENT_EXPERT_SYSTEM
        assert "cross-disciplinary" in agent.system_prompt.lower()

    def test_perspective(self) -> None:
        agent = AdjacentExpertAgent()
        assert "related" in agent.perspective.lower()

    def test_focus_areas(self) -> None:
        agent = AdjacentExpertAgent()
        assert "significance" in agent.focus_areas
        assert "presentation" in agent.focus_areas

    @pytest.mark.asyncio
    async def test_full_pipeline(self, sample_task_input) -> None:
        agent = AdjacentExpertAgent()
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            side_effect=[_make_llm_response(r) for r in _all_responses()]
        )
        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(AdjacentExpertAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert result["reviewer_type"] == "adjacent_expert"
        assert result["recommendation"] == "minor_revision"


# ---------------------------------------------------------------------------
# Methods Specialist
# ---------------------------------------------------------------------------


class TestMethodsSpecialist:
    def test_default_agent_type(self) -> None:
        agent = MethodsSpecialistAgent()
        assert agent._config.agent_type == "methods_specialist"

    def test_system_prompt(self) -> None:
        agent = MethodsSpecialistAgent()
        assert agent.system_prompt == METHODS_SPECIALIST_SYSTEM
        assert "methodologist" in agent.system_prompt.lower()

    def test_perspective(self) -> None:
        agent = MethodsSpecialistAgent()
        assert "methodolog" in agent.perspective.lower()

    def test_focus_areas(self) -> None:
        agent = MethodsSpecialistAgent()
        assert "methodology" in agent.focus_areas
        assert "reproducibility" in agent.focus_areas

    @pytest.mark.asyncio
    async def test_full_pipeline(self, sample_task_input) -> None:
        agent = MethodsSpecialistAgent()
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            side_effect=[_make_llm_response(r) for r in _all_responses()]
        )
        with (
            patch("agents.core.adapters.langgraph.LLMClient", return_value=mock_llm),
            patch.object(MethodsSpecialistAgent, "_create_tools", return_value=[]),
        ):
            await agent.initialize()
            result = await agent.execute(sample_task_input)

        assert result["reviewer_type"] == "methods_specialist"
        assert result["recommendation"] == "minor_revision"


# ---------------------------------------------------------------------------
# Tool creation tests
# ---------------------------------------------------------------------------


class TestToolCreation:
    def test_core_expert_tool_set(self) -> None:
        """Core expert should attempt perplexity, arxiv, semantic_scholar, rag."""
        agent = CoreExpertAgent()
        # We can't test actual tool creation without API keys, but
        # we can verify the _create_tools method exists and is callable
        with patch.dict("sys.modules", {
            "tools.research.perplexity": None,
            "tools.research.arxiv": None,
            "tools.research.semantic_scholar": None,
            "tools.knowledge.rag": None,
        }):
            tools = agent._create_tools()
            assert tools == []  # All imports fail gracefully

    def test_adjacent_expert_tool_set(self) -> None:
        agent = AdjacentExpertAgent()
        with patch.dict("sys.modules", {
            "tools.research.perplexity": None,
            "tools.research.google_search": None,
            "tools.knowledge.rag": None,
        }):
            tools = agent._create_tools()
            assert tools == []

    def test_methods_specialist_tool_set(self) -> None:
        agent = MethodsSpecialistAgent()
        with patch.dict("sys.modules", {
            "tools.research.perplexity": None,
            "tools.research.semantic_scholar": None,
            "tools.knowledge.rag": None,
        }):
            tools = agent._create_tools()
            assert tools == []


# ---------------------------------------------------------------------------
# Independence verification
# ---------------------------------------------------------------------------


class TestIndependence:
    @pytest.mark.asyncio
    async def test_agents_dont_share_state(self, sample_task_input) -> None:
        """Verify that two agents don't share any mutable state."""
        agent1 = CoreExpertAgent()
        agent2 = AdjacentExpertAgent()

        agent1.set_context({"domain": "NLP"})
        agent2.set_context({"domain": "CV"})

        assert agent1._context != agent2._context

    def test_agents_have_different_perspectives(self) -> None:
        agents = [CoreExpertAgent(), AdjacentExpertAgent(), MethodsSpecialistAgent()]
        perspectives = [a.perspective for a in agents]
        # All unique
        assert len(set(perspectives)) == 3

    def test_agents_have_different_focus_areas(self) -> None:
        agents = [CoreExpertAgent(), AdjacentExpertAgent(), MethodsSpecialistAgent()]
        focus_sets = [tuple(a.focus_areas) for a in agents]
        assert len(set(focus_sets)) == 3
