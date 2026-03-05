"""Methods Specialist reviewer agent.

Focuses on experimental design, statistical validity, reproducibility,
and methodological rigour. Uses Perplexity, Semantic Scholar, and RAG
to access methodological standards and benchmarks.
"""

from __future__ import annotations

from agents.core.base import AgentConfig, ToolInterface
from agents.reviewers.base import BaseReviewer
from agents.reviewers.prompts import METHODS_SPECIALIST_SYSTEM
from loguru import logger


class MethodsSpecialistAgent(BaseReviewer):
    """Reviewer focused on methodological rigour.

    Tool set: perplexity, semantic_scholar, rag
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        super().__init__(config or AgentConfig(agent_type="methods_specialist"))

    # ------------------------------------------------------------------
    # Abstract property implementations
    # ------------------------------------------------------------------

    @property
    def system_prompt(self) -> str:
        return METHODS_SPECIALIST_SYSTEM

    @property
    def perspective(self) -> str:
        return (
            "Statistician and methodologist who scrutinises experimental "
            "design, statistical analysis, reproducibility, and the "
            "validity of conclusions drawn from data."
        )

    @property
    def focus_areas(self) -> list[str]:
        return ["methodology", "reproducibility", "significance"]

    # ------------------------------------------------------------------
    # Tool override — methods-focused tools
    # ------------------------------------------------------------------

    def _create_tools(self) -> list[ToolInterface]:
        """Create methods specialist tool set: perplexity, semantic_scholar, rag."""
        tool_factories: dict[str, type] = {}

        try:
            from tools.research.perplexity import PerplexityTool
            tool_factories["perplexity"] = PerplexityTool
        except ImportError:
            pass
        try:
            from tools.research.semantic_scholar import SemanticScholarTool
            tool_factories["semantic_scholar"] = SemanticScholarTool
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
