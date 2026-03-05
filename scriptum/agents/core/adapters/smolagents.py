"""SmolAgents framework adapter stub.

Planned for a future release. Currently raises ``NotImplementedError``
on instantiation so the factory fails fast with a clear message.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from agents.core.base import (
    AgentConfig,
    AgentInterface,
    AgentStatusEnum,
    ToolInterface,
)


class SmolAgentsAdapter(AgentInterface):
    """SmolAgents adapter — not yet implemented."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        raise NotImplementedError(
            "SmolAgents adapter is planned for a future release. "
            "Set agents.framework to 'langgraph' in config.yaml."
        )

    async def initialize(self) -> None:
        raise NotImplementedError  # pragma: no cover

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError  # pragma: no cover

    async def stream(
        self, input_data: dict[str, Any]
    ) -> AsyncGenerator[dict[str, Any], None]:
        raise NotImplementedError  # pragma: no cover
        yield {}  # pragma: no cover

    async def cleanup(self) -> None:
        raise NotImplementedError  # pragma: no cover

    def get_tools(self) -> list[ToolInterface]:
        raise NotImplementedError  # pragma: no cover

    def get_status(self) -> AgentStatusEnum:
        raise NotImplementedError  # pragma: no cover

    def set_context(self, context: dict[str, Any]) -> None:
        raise NotImplementedError  # pragma: no cover
