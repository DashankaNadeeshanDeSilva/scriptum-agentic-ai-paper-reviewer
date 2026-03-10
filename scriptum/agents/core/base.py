"""Agent interface, base abstractions, and shared data models.

Defines the abstract base class that all agents must implement,
regardless of the underlying framework (LangGraph, CrewAI, SmolAgents).
Also contains the data classes that flow through the review pipeline and
the ``ToolInterface`` ABC that all agent tools must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentStatusEnum(StrEnum):
    """Lifecycle status of an agent."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    EVALUATING = "evaluating"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class AgentConfig:
    """Configuration for an agent instance.

    Passed to adapters/factories. ``provider`` and ``model`` override the
    global LLM settings for this specific agent.
    """

    agent_type: str = ""  # core_expert | adjacent_expert | methods_specialist | meta_reviewer
    provider: str | None = None
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 300  # seconds
    tools_enabled: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline data models (plain dataclasses — ephemeral, never cross API)
# ---------------------------------------------------------------------------


@dataclass
class ReviewTask:
    """Input to an agent's execute/stream methods.

    Carries the parsed document plus review context (journal, domain, criteria).
    ``paper`` is imported lazily to avoid circular imports with ``tools.document``.
    """

    paper: Any = None  # tools.document.models.ParsedDocument
    journal_config: dict[str, Any] = field(default_factory=dict)
    domain_general: str = ""
    domain_specific: str = ""
    review_criteria: dict[str, float] = field(default_factory=dict)  # category -> weight

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for graph state."""
        paper_dict = self.paper.to_dict() if self.paper and hasattr(self.paper, "to_dict") else {}
        return {
            "paper": paper_dict,
            "journal_config": self.journal_config,
            "domain_general": self.domain_general,
            "domain_specific": self.domain_specific,
            "review_criteria": self.review_criteria,
        }


@dataclass
class Evidence:
    """A piece of evidence supporting a claim in the review."""

    claim: str = ""
    source: str = ""  # e.g. "paper:section:3", "arxiv:2301.12345"
    quote: str = ""  # direct quote from source
    relevance: float = 0.0  # 0.0–1.0


@dataclass
class ReviewResult:
    """Output from an agent's execute method.

    Aggregated by the Meta Reviewer in Phase 3.
    """

    reviewer_type: str = ""
    scores: dict[str, float] = field(default_factory=dict)  # category -> score (1-10)
    feedback: dict[str, str] = field(default_factory=dict)  # category -> feedback text
    evidence: list[Evidence] = field(default_factory=list)
    recommendation: str = "major_revision"  # accept | minor_revision | major_revision | reject
    confidence: float = 0.0  # 0.0–1.0
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict matching the ReviewerReport API schema."""
        return {
            "reviewer_type": self.reviewer_type,
            "scores": self.scores,
            "feedback": self.feedback,
            "evidence": [
                {
                    "claim": e.claim,
                    "source": e.source,
                    "quote": e.quote,
                    "relevance": e.relevance,
                }
                for e in self.evidence
            ],
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }


@dataclass
class ProgressEvent:
    """Progress event emitted during streaming execution.

    Sent over WebSocket to the frontend in Phase 3/4.
    """

    event_type: str = "progress"  # progress | step_complete | error | info
    step: str = ""  # research | analyze | evaluate | generate_feedback
    agent: str = ""  # agent_type identifier
    progress: float = 0.0  # 0.0–1.0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "step": self.step,
            "agent": self.agent,
            "progress": self.progress,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Tool interface
# ---------------------------------------------------------------------------


class ToolInterface(ABC):
    """Abstract base for tools that agents can use.

    Each tool has a name, description, and an async execute method.
    Research tools, RAG tools, and utility tools all implement this.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (e.g. 'arxiv', 'semantic_scholar', 'rag')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Run the tool with the given keyword arguments."""
        ...


# ---------------------------------------------------------------------------
# Agent interface
# ---------------------------------------------------------------------------


class AgentInterface(ABC):
    """Abstract base class for all SCRIPTUM agents.

    All concrete agent implementations must inherit from this class
    and implement the required methods. Framework adapters (LangGraph,
    CrewAI, SmolAgents) sit between this ABC and the concrete agents.
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

    @abstractmethod
    def get_tools(self) -> list[ToolInterface]:
        """Return the tools available to this agent."""
        ...

    @abstractmethod
    def get_status(self) -> AgentStatusEnum:
        """Return the agent's current lifecycle status."""
        ...

    @abstractmethod
    def set_context(self, context: dict[str, Any]) -> None:
        """Set additional context (journal config, domain, etc.)."""
        ...
