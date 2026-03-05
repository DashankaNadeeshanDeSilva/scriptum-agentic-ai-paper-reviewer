"""Tests for the agent abstraction layer (agents.core).

Covers data classes, ToolInterface, LangGraphAdapter, and the factory.
All LLM calls and external tools are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.core.base import (
    AgentConfig,
    AgentStatusEnum,
    Evidence,
    ProgressEvent,
    ReviewResult,
    ReviewTask,
    ToolInterface,
)


# =========================================================================
# Data class tests
# =========================================================================


class TestAgentConfig:
    def test_defaults(self) -> None:
        cfg = AgentConfig()
        assert cfg.agent_type == ""
        assert cfg.provider is None
        assert cfg.model is None
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 4096
        assert cfg.timeout == 300
        assert cfg.tools_enabled == []

    def test_custom_values(self) -> None:
        cfg = AgentConfig(
            agent_type="core_expert",
            provider="anthropic",
            model="claude-opus-4-6",
            tools_enabled=["arxiv", "rag"],
        )
        assert cfg.agent_type == "core_expert"
        assert cfg.tools_enabled == ["arxiv", "rag"]


class TestReviewTask:
    def test_defaults(self) -> None:
        task = ReviewTask()
        assert task.paper is None
        assert task.journal_config == {}
        assert task.domain_general == ""
        assert task.review_criteria == {}

    def test_to_dict_with_paper(self) -> None:
        mock_paper = MagicMock()
        mock_paper.to_dict.return_value = {"metadata": {"title": "Test"}}

        task = ReviewTask(
            paper=mock_paper,
            domain_general="CS",
            review_criteria={"novelty": 0.25},
        )
        d = task.to_dict()
        assert d["paper"] == {"metadata": {"title": "Test"}}
        assert d["domain_general"] == "CS"
        assert d["review_criteria"] == {"novelty": 0.25}

    def test_to_dict_without_paper(self) -> None:
        task = ReviewTask()
        d = task.to_dict()
        assert d["paper"] == {}


class TestEvidence:
    def test_creation(self) -> None:
        e = Evidence(
            claim="The method is novel",
            source="arxiv:2301.12345",
            quote="We propose a new approach...",
            relevance=0.9,
        )
        assert e.claim == "The method is novel"
        assert e.relevance == 0.9


class TestReviewResult:
    def test_defaults(self) -> None:
        r = ReviewResult()
        assert r.recommendation == "major_revision"
        assert r.confidence == 0.0
        assert r.scores == {}
        assert r.evidence == []

    def test_to_dict(self) -> None:
        r = ReviewResult(
            reviewer_type="core_expert",
            scores={"novelty": 8.0, "methodology": 7.5},
            feedback={"novelty": "Strong contribution"},
            evidence=[
                Evidence(claim="Novel", source="paper:section:1", relevance=0.8)
            ],
            recommendation="minor_revision",
            confidence=0.85,
            strengths=["Clear writing"],
            weaknesses=["Limited experiments"],
        )
        d = r.to_dict()
        assert d["reviewer_type"] == "core_expert"
        assert d["scores"]["novelty"] == 8.0
        assert d["recommendation"] == "minor_revision"
        assert d["confidence"] == 0.85
        assert len(d["evidence"]) == 1
        assert d["evidence"][0]["source"] == "paper:section:1"
        assert d["strengths"] == ["Clear writing"]
        assert d["weaknesses"] == ["Limited experiments"]


class TestProgressEvent:
    def test_defaults(self) -> None:
        pe = ProgressEvent()
        assert pe.event_type == "progress"
        assert pe.progress == 0.0

    def test_to_dict(self) -> None:
        pe = ProgressEvent(
            event_type="step_complete",
            step="research",
            agent="core_expert",
            progress=0.25,
            message="Done",
        )
        d = pe.to_dict()
        assert d["event_type"] == "step_complete"
        assert d["step"] == "research"
        assert d["progress"] == 0.25


class TestAgentStatusEnum:
    def test_values(self) -> None:
        assert AgentStatusEnum.IDLE == "idle"
        assert AgentStatusEnum.RESEARCHING == "researching"
        assert AgentStatusEnum.FAILED == "failed"

    def test_is_string(self) -> None:
        assert isinstance(AgentStatusEnum.COMPLETED, str)


# =========================================================================
# ToolInterface tests
# =========================================================================


class TestToolInterface:
    def test_concrete_tool_implementation(self) -> None:
        """Verify a concrete tool satisfying the ABC works."""

        class DummyTool(ToolInterface):
            @property
            def name(self) -> str:
                return "dummy"

            @property
            def description(self) -> str:
                return "A test tool"

            async def execute(self, **kwargs):
                return {"result": "ok"}

        tool = DummyTool()
        assert tool.name == "dummy"
        assert tool.description == "A test tool"

    @pytest.mark.asyncio
    async def test_tool_execute(self) -> None:
        class EchoTool(ToolInterface):
            @property
            def name(self) -> str:
                return "echo"

            @property
            def description(self) -> str:
                return "Echoes input"

            async def execute(self, **kwargs):
                return kwargs

        tool = EchoTool()
        result = await tool.execute(query="hello")
        assert result == {"query": "hello"}


# =========================================================================
# LangGraphAdapter tests
# =========================================================================


class TestLangGraphAdapter:
    """Test the LangGraph adapter lifecycle and execution."""

    @pytest.mark.asyncio
    @patch("agents.core.adapters.langgraph.LLMClient")
    async def test_initialize_creates_llm_and_graph(
        self, mock_llm_cls: MagicMock
    ) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter(
            config=AgentConfig(agent_type="core_expert")
        )
        assert adapter.get_status() == AgentStatusEnum.IDLE

        await adapter.initialize()

        mock_llm_cls.assert_called_once()
        assert adapter._graph is not None
        assert adapter.get_status() == AgentStatusEnum.IDLE

    @pytest.mark.asyncio
    @patch("agents.core.adapters.langgraph.LLMClient")
    async def test_execute_runs_graph_and_returns_result(
        self, mock_llm_cls: MagicMock
    ) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter(
            config=AgentConfig(agent_type="core_expert", timeout=30)
        )
        await adapter.initialize()

        result = await adapter.execute({"paper": {"title": "Test Paper"}})

        assert isinstance(result, dict)
        assert result["reviewer_type"] == "core_expert"
        assert "scores" in result
        assert "recommendation" in result
        assert "strengths" in result
        assert "weaknesses" in result
        assert adapter.get_status() == AgentStatusEnum.COMPLETED

    @pytest.mark.asyncio
    @patch("agents.core.adapters.langgraph.LLMClient")
    async def test_stream_yields_progress_events(
        self, mock_llm_cls: MagicMock
    ) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter(
            config=AgentConfig(agent_type="methods_specialist")
        )
        await adapter.initialize()

        events = []
        async for event in adapter.stream({"paper": {}}):
            events.append(event)

        # 4 nodes = 4 events
        assert len(events) == 4
        # Each event should have step info
        steps_seen = {e.get("step", "") for e in events}
        assert "research" in steps_seen
        assert "generate_feedback" in steps_seen

    @pytest.mark.asyncio
    @patch("agents.core.adapters.langgraph.LLMClient")
    async def test_execute_without_initialize_raises(
        self, mock_llm_cls: MagicMock
    ) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter()
        with pytest.raises(RuntimeError, match="not initialised"):
            await adapter.execute({"paper": {}})

    @pytest.mark.asyncio
    @patch("agents.core.adapters.langgraph.LLMClient")
    async def test_cleanup_resets_state(
        self, mock_llm_cls: MagicMock
    ) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter()
        await adapter.initialize()
        assert adapter._graph is not None

        await adapter.cleanup()
        assert adapter._graph is None
        assert adapter._tools == []
        assert adapter.get_status() == AgentStatusEnum.IDLE

    @patch("agents.core.adapters.langgraph.LLMClient")
    def test_get_tools_returns_list(self, mock_llm_cls: MagicMock) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter()
        assert adapter.get_tools() == []

    @patch("agents.core.adapters.langgraph.LLMClient")
    def test_set_context_stores_context(
        self, mock_llm_cls: MagicMock
    ) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter

        adapter = LangGraphAdapter()
        ctx = {"journal": "Nature", "domain": "biology"}
        adapter.set_context(ctx)
        assert adapter._context == ctx

    @pytest.mark.asyncio
    @patch("agents.core.adapters.langgraph.LLMClient")
    async def test_initialize_failure_sets_failed_status(
        self, mock_llm_cls: MagicMock
    ) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter

        mock_llm_cls.side_effect = Exception("LLM init failed")
        adapter = LangGraphAdapter()

        with pytest.raises(Exception, match="LLM init failed"):
            await adapter.initialize()

        assert adapter.get_status() == AgentStatusEnum.FAILED


# =========================================================================
# Factory tests
# =========================================================================


class TestAgentFactory:
    @patch("agents.core.factory.get_settings")
    def test_creates_langgraph_adapter(self, mock_gs: MagicMock) -> None:
        from agents.core.adapters.langgraph import LangGraphAdapter
        from agents.core.factory import create_agent

        mock_gs.return_value = MagicMock()
        mock_gs.return_value.agents.framework = "langgraph"

        agent = create_agent(AgentConfig(agent_type="core_expert"))
        assert isinstance(agent, LangGraphAdapter)

    @patch("agents.core.factory.get_settings")
    def test_crewai_raises_not_implemented(self, mock_gs: MagicMock) -> None:
        from agents.core.factory import create_agent

        mock_gs.return_value = MagicMock()
        mock_gs.return_value.agents.framework = "crewai"

        with pytest.raises(NotImplementedError, match="CrewAI"):
            create_agent()

    @patch("agents.core.factory.get_settings")
    def test_smolagents_raises_not_implemented(
        self, mock_gs: MagicMock
    ) -> None:
        from agents.core.factory import create_agent

        mock_gs.return_value = MagicMock()
        mock_gs.return_value.agents.framework = "smolagents"

        with pytest.raises(NotImplementedError, match="SmolAgents"):
            create_agent()

    @patch("agents.core.factory.get_settings")
    def test_unknown_framework_raises_value_error(
        self, mock_gs: MagicMock
    ) -> None:
        from agents.core.factory import create_agent

        mock_gs.return_value = MagicMock()
        mock_gs.return_value.agents.framework = "tensorflow_agents"

        with pytest.raises(ValueError, match="Unknown agent framework"):
            create_agent()
