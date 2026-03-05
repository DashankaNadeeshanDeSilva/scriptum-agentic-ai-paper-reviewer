"""Meta Reviewer tool factory.

The Meta Reviewer uses a restricted tool set: Perplexity (deep web search),
Google Search (broad web search), and RAG (journal guidelines retrieval).
It does NOT use arXiv, Semantic Scholar, or CrossRef — those are reserved
for the independent reviewer agents.
"""

from __future__ import annotations

from loguru import logger

from agents.core.base import ToolInterface

_META_REVIEWER_TOOLS = ["perplexity", "google_search", "rag"]


def create_meta_reviewer_tools(
    tools_enabled: list[str] | None = None,
) -> list[ToolInterface]:
    """Create the tool set for the Meta Reviewer agent.

    Args:
        tools_enabled: Restrict to these tool names. If *None*, all
            Meta Reviewer tools are enabled.

    Returns:
        List of instantiated tools. Empty on complete import failure.
    """
    enabled = tools_enabled or _META_REVIEWER_TOOLS

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

    tools: list[ToolInterface] = []
    for name in enabled:
        factory = tool_factories.get(name)
        if factory is not None:
            try:
                tools.append(factory())
            except Exception as exc:
                logger.warning("Failed to create Meta Reviewer tool '{}': {}", name, exc)
    return tools
