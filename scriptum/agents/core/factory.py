"""Agent factory for creating agent instances based on configuration.

Reads the ``agents.framework`` setting to select the appropriate adapter
(LangGraph, CrewAI, or SmolAgents) and returns an uninitialised agent.
The caller must await ``agent.initialize()`` before use.
"""

from __future__ import annotations

from agents.core.base import AgentConfig, AgentInterface
from backend.core.config import get_settings


def create_agent(config: AgentConfig | None = None) -> AgentInterface:
    """Create an agent instance using the configured framework.

    Args:
        config: Optional agent configuration. If ``None``, defaults are used.

    Returns:
        An uninitialised :class:`AgentInterface` implementation.

    Raises:
        ValueError: If the configured framework is not supported.
    """
    settings = get_settings()
    framework = settings.agents.framework

    if framework == "langgraph":
        from agents.core.adapters.langgraph import LangGraphAdapter

        return LangGraphAdapter(config=config)

    if framework == "crewai":
        from agents.core.adapters.crewai import CrewAIAdapter

        return CrewAIAdapter(config=config)

    if framework == "smolagents":
        from agents.core.adapters.smolagents import SmolAgentsAdapter

        return SmolAgentsAdapter(config=config)

    raise ValueError(
        f"Unknown agent framework: '{framework}'. Supported values: langgraph, crewai, smolagents."
    )
