"""Core Expert reviewer agent.

Deep domain specialist focused on novelty, technical depth, and significance.
Uses arXiv, Semantic Scholar, Perplexity, and RAG for thorough literature
coverage in the paper's exact subfield.
"""

from __future__ import annotations

from loguru import logger

from scriptum_ai.agents.core.base import AgentConfig, ToolInterface
from scriptum_ai.agents.reviewers.base import BaseReviewer
from scriptum_ai.agents.reviewers.prompts import CORE_EXPERT_SYSTEM


class CoreExpertAgent(BaseReviewer):
    """Reviewer with deep domain expertise.

    Tool set: perplexity, arxiv, semantic_scholar, rag
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(config or AgentConfig(agent_type="core_expert"))

    # ------------------------------------------------------------------
    # Abstract property implementations
    # ------------------------------------------------------------------

    @property
    def system_prompt(self) -> str:
        return CORE_EXPERT_SYSTEM

    @property
    def perspective(self) -> str:
        return (
            "Senior domain specialist with deep expertise in the paper's "
            "exact subfield, focused on whether the contribution genuinely "
            "advances the state of the art."
        )

    @property
    def focus_areas(self) -> list[str]:
        return ["novelty", "significance", "methodology"]

    # ------------------------------------------------------------------
    # Tool override — domain-focused research tools
    # ------------------------------------------------------------------

    def _create_tools(self) -> list[ToolInterface]:
        """Create core expert tool set: perplexity, arxiv, semantic_scholar, rag."""
        tool_factories: dict[str, type] = {}

        try:
            from scriptum_ai.tools.research.perplexity import PerplexityTool

            tool_factories["perplexity"] = PerplexityTool
        except ImportError:
            pass
        try:
            from scriptum_ai.tools.research.arxiv import ArxivTool

            tool_factories["arxiv"] = ArxivTool
        except ImportError:
            pass
        try:
            from scriptum_ai.tools.research.semantic_scholar import SemanticScholarTool

            tool_factories["semantic_scholar"] = SemanticScholarTool
        except ImportError:
            pass
        try:
            from scriptum_ai.tools.knowledge.rag import RAGTool

            tool_factories["rag"] = RAGTool
        except ImportError:
            pass

        enabled = self._config.tools_enabled or list(tool_factories.keys())
        tools: list[ToolInterface] = []
        for name in enabled:
            factory = tool_factories.get(name)
            if factory is not None:
                try:
                    tools.append(factory())
                except Exception as exc:
                    logger.warning("Failed to create tool '{}': {}", name, exc)
        return tools
