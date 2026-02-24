"""Agent interface and base abstractions.

Defines the abstract base class that all agents must implement,
regardless of the underlying framework (LangGraph, CrewAI, SmolAgents).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any


class AgentInterface(ABC):
    """Abstract base class for all SCRIPTUM agents.

    All concrete agent implementations must inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent with necessary resources."""
        ...

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's main task.

        Args:
            input_data: Input data for the agent to process.

        Returns:
            The agent's output as a dictionary.
        """
        ...

    @abstractmethod
    async def stream(self, input_data: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        """Stream the agent's execution progress.

        Args:
            input_data: Input data for the agent to process.

        Yields:
            Progress updates as the agent executes.
        """
        ...
        yield {}  # pragma: no cover

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources after execution."""
        ...
