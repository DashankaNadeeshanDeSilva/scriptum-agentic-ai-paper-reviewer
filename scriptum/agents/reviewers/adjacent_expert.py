"""Adjacent Expert reviewer agent.

Cross-disciplinary perspective focused on broader significance, presentation
clarity, and potential impact beyond the paper's immediate subfield.
Uses Perplexity, Google Search, and RAG for wide-ranging context.
"""

from __future__ import annotations

from agents.core.base import AgentConfig, ToolInterface
from agents.reviewers.base import BaseReviewer
from agents.reviewers.prompts import ADJACENT_EXPERT_SYSTEM
from loguru import logger


class AdjacentExpertAgent(BaseReviewer):
    """Reviewer with cross-disciplinary perspective.

    Tool set: perplexity, google_search, rag
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(config or AgentConfig(agent_type="adjacent_expert"))

    # ------------------------------------------------------------------
    # Abstract property implementations
    # ------------------------------------------------------------------

    @property
    def system_prompt(self) -> str:
        return ADJACENT_EXPERT_SYSTEM

    @property
    def perspective(self) -> str:
        return (
            "Researcher from a related but different field, evaluating "
            "whether the paper's contributions are accessible, impactful, "
            "and relevant beyond the narrow subfield."
        )

    @property
    def focus_areas(self) -> list[str]:
        return ["significance", "presentation", "novelty"]

    # ------------------------------------------------------------------
    # Tool override — broad search tools
    # ------------------------------------------------------------------

    def _create_tools(self) -> list[ToolInterface]:
        """Create adjacent expert tool set: perplexity, google_search, rag."""
        tool_factories: dict[str, type] = {}

        try:
            from tools.research.perplexity import PerplexityTool
            tool_factories["perplexity"] = PerplexityTool
        except ImportError:
            pass
        try:
            from tools.research.google_search import GoogleSearchTool
            tool_factories["google_search"] = GoogleSearchTool
        except ImportError:
            pass
        try:
            from tools.knowledge.rag import RAGTool
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
