"""LangGraph framework adapter for SCRIPTUM agents.

Bridges :class:`AgentInterface` to LangGraph's ``StateGraph`` execution.
Concrete agents (Phase 3) subclass ``LangGraphAdapter`` and override
individual node methods to customise the review pipeline.
"""

from __future__ import annotations

import asyncio
import operator
from collections.abc import AsyncGenerator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger

from scriptum_ai.agents.core.base import (
    AgentConfig,
    AgentInterface,
    AgentStatusEnum,
    ProgressEvent,
    ReviewResult,
    ToolInterface,
)
from scriptum_ai.backend.core.llm import LLMClient

# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


class ReviewState(TypedDict, total=False):
    """Typed state that flows through the review graph.

    List fields use ``Annotated[..., operator.add]`` so that each node
    *appends* to lists rather than overwriting them.
    """

    # Input (set once in initial state)
    task: dict[str, Any]
    context: dict[str, Any]

    # Accumulated across nodes
    research_findings: Annotated[list[dict[str, Any]], operator.add]
    analysis: dict[str, Any]
    scores: dict[str, float]
    feedback: dict[str, str]
    evidence: Annotated[list[dict[str, Any]], operator.add]
    strengths: Annotated[list[str], operator.add]
    weaknesses: Annotated[list[str], operator.add]
    recommendation: str
    progress_events: Annotated[list[dict[str, Any]], operator.add]


# ---------------------------------------------------------------------------
# Node step names (used for progress tracking)
# ---------------------------------------------------------------------------

STEP_RESEARCH = "research"
STEP_ANALYZE = "analyze"
STEP_EVALUATE = "evaluate"
STEP_GENERATE = "generate_feedback"


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class LangGraphAdapter(AgentInterface):
    """Adapts :class:`AgentInterface` to a LangGraph ``StateGraph``.

    The default graph has four sequential nodes::

        research → analyze → evaluate → generate_feedback → END

    Each node is an instance method that Phase 3 agents override to inject
    agent-specific prompts and logic. The base implementations are
    lightweight placeholders that pass state through.

    Args:
        config: Agent configuration (type, LLM overrides, tools, timeout).
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        self._config = config or AgentConfig()
        self._llm: LLMClient | None = None
        self._tools: list[ToolInterface] = []
        self._graph: Any = None  # compiled StateGraph
        self._status: AgentStatusEnum = AgentStatusEnum.IDLE
        self._context: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # AgentInterface — lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create the LLM client, instantiate tools, and compile the graph."""
        try:
            self._status = AgentStatusEnum.INITIALIZING
            self._llm = LLMClient(
                provider=self._config.provider,
                model=self._config.model,
            )
            self._tools = self._create_tools()
            self._graph = self._build_graph()
            self._status = AgentStatusEnum.IDLE
            logger.info(
                "LangGraphAdapter initialised (agent_type={})",
                self._config.agent_type,
            )
        except Exception as exc:
            self._status = AgentStatusEnum.FAILED
            logger.error("Failed to initialise agent: {}", exc)
            raise

    async def cleanup(self) -> None:
        """Release resources held by the adapter."""
        self._llm = None
        self._tools = []
        self._graph = None
        self._status = AgentStatusEnum.IDLE

    # ------------------------------------------------------------------
    # AgentInterface — execution
    # ------------------------------------------------------------------

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run the full review graph and return a :class:`ReviewResult`-compatible dict."""
        if self._graph is None:
            raise RuntimeError("Agent not initialised — call initialize() first")

        initial_state = self._prepare_initial_state(input_data)

        try:
            final_state = await asyncio.wait_for(
                self._graph.ainvoke(initial_state),
                timeout=self._config.timeout,
            )
            self._status = AgentStatusEnum.COMPLETED
            return self._extract_result(final_state)
        except TimeoutError:
            self._status = AgentStatusEnum.FAILED
            raise RuntimeError(f"Agent execution timed out after {self._config.timeout}s") from None
        except Exception:
            self._status = AgentStatusEnum.FAILED
            raise

    async def stream(self, input_data: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        """Stream progress events from graph execution.

        Yields one :class:`ProgressEvent`-like dict per graph node.
        """
        if self._graph is None:
            raise RuntimeError("Agent not initialised — call initialize() first")

        initial_state = self._prepare_initial_state(input_data)

        async for event in self._graph.astream(initial_state):
            yield self._format_stream_event(event)

        self._status = AgentStatusEnum.COMPLETED

    # ------------------------------------------------------------------
    # AgentInterface — introspection
    # ------------------------------------------------------------------

    def get_tools(self) -> list[ToolInterface]:
        return list(self._tools)

    def get_status(self) -> AgentStatusEnum:
        return self._status

    def set_context(self, context: dict[str, Any]) -> None:
        self._context = context

    # ------------------------------------------------------------------
    # Graph construction (override in subclasses)
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        """Build and compile the default 4-node review graph.

        Subclasses can override this to alter the graph topology, or
        override individual node methods to change behaviour while
        keeping the same topology.
        """
        graph = StateGraph(ReviewState)

        graph.add_node(STEP_RESEARCH, self._research_node)
        graph.add_node(STEP_ANALYZE, self._analyze_node)
        graph.add_node(STEP_EVALUATE, self._evaluate_node)
        graph.add_node(STEP_GENERATE, self._generate_feedback_node)

        graph.set_entry_point(STEP_RESEARCH)
        graph.add_edge(STEP_RESEARCH, STEP_ANALYZE)
        graph.add_edge(STEP_ANALYZE, STEP_EVALUATE)
        graph.add_edge(STEP_EVALUATE, STEP_GENERATE)
        graph.add_edge(STEP_GENERATE, END)

        return graph.compile()

    # ------------------------------------------------------------------
    # Graph nodes (override in Phase 3 agents)
    # ------------------------------------------------------------------

    async def _research_node(self, state: ReviewState) -> dict[str, Any]:
        """Search external sources for relevant prior work.

        Base implementation is a pass-through. Phase 3 agents override
        this to call research tools (arXiv, Semantic Scholar, etc.).
        """
        self._status = AgentStatusEnum.RESEARCHING
        logger.debug("research node (base pass-through)")
        return {
            "research_findings": [],
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_RESEARCH,
                    agent=self._config.agent_type,
                    progress=0.25,
                    message="Research phase complete",
                ).to_dict()
            ],
        }

    async def _analyze_node(self, state: ReviewState) -> dict[str, Any]:
        """Analyse the paper content using the LLM.

        Base implementation is a pass-through. Phase 3 agents override
        this to send analysis prompts to the LLM.
        """
        self._status = AgentStatusEnum.ANALYZING
        logger.debug("analyze node (base pass-through)")
        return {
            "analysis": {},
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_ANALYZE,
                    agent=self._config.agent_type,
                    progress=0.50,
                    message="Analysis phase complete",
                ).to_dict()
            ],
        }

    async def _evaluate_node(self, state: ReviewState) -> dict[str, Any]:
        """Score the paper on review criteria using the LLM.

        Base implementation returns empty scores. Phase 3 agents
        override to produce real category scores.
        """
        self._status = AgentStatusEnum.EVALUATING
        logger.debug("evaluate node (base pass-through)")
        return {
            "scores": {},
            "evidence": [],
            "strengths": [],
            "weaknesses": [],
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_EVALUATE,
                    agent=self._config.agent_type,
                    progress=0.75,
                    message="Evaluation phase complete",
                ).to_dict()
            ],
        }

    async def _generate_feedback_node(self, state: ReviewState) -> dict[str, Any]:
        """Generate structured feedback and recommendation.

        Base implementation returns defaults. Phase 3 agents override
        to produce real feedback from the LLM.
        """
        self._status = AgentStatusEnum.GENERATING
        logger.debug("generate_feedback node (base pass-through)")
        return {
            "feedback": {},
            "recommendation": "major_revision",
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_GENERATE,
                    agent=self._config.agent_type,
                    progress=1.0,
                    message="Feedback generation complete",
                ).to_dict()
            ],
        }

    # ------------------------------------------------------------------
    # Tool creation
    # ------------------------------------------------------------------

    def _create_tools(self) -> list[ToolInterface]:
        """Instantiate tools enabled for this agent.

        Imports are deferred to avoid circular imports and to only
        load tools that are actually needed. Phase 3 agents may
        override this to register agent-specific tools.
        """
        tool_factories: dict[str, type] = {}

        # Safely try importing research tools (may not be implemented yet)
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
            from scriptum_ai.tools.research.perplexity import PerplexityTool

            tool_factories["perplexity"] = PerplexityTool
        except ImportError:
            pass
        try:
            from scriptum_ai.tools.research.google_search import GoogleSearchTool

            tool_factories["google_search"] = GoogleSearchTool
        except ImportError:
            pass
        try:
            from scriptum_ai.tools.research.crossref import CrossRefTool

            tool_factories["crossref"] = CrossRefTool
        except ImportError:
            pass
        try:
            from scriptum_ai.tools.knowledge.rag import RAGTool

            tool_factories["rag"] = RAGTool
        except ImportError:
            pass

        # If tools_enabled is empty, enable all available tools
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

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _prepare_initial_state(self, input_data: dict[str, Any]) -> ReviewState:
        """Build the initial graph state from execute/stream input."""
        return ReviewState(
            task=input_data,
            context=self._context,
            research_findings=[],
            analysis={},
            scores={},
            feedback={},
            evidence=[],
            strengths=[],
            weaknesses=[],
            recommendation="",
            progress_events=[],
        )

    def _extract_result(self, state: dict[str, Any]) -> dict[str, Any]:
        """Convert final graph state to a :class:`ReviewResult`-compatible dict."""
        result = ReviewResult(
            reviewer_type=self._config.agent_type,
            scores=state.get("scores", {}),
            feedback=state.get("feedback", {}),
            evidence=[],
            recommendation=state.get("recommendation", "major_revision"),
            confidence=0.0,
            strengths=state.get("strengths", []),
            weaknesses=state.get("weaknesses", []),
        )
        # Convert evidence dicts back to Evidence objects are not needed here;
        # we just pass the raw dicts through as they are already serialisable.
        return result.to_dict()

    def _format_stream_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Format a raw LangGraph stream event into a progress dict.

        LangGraph's ``astream`` yields ``{node_name: {partial_state_update}}``.
        We extract progress_events from the update and add the node name.
        """
        for node_name, update in event.items():
            progress_events = update.get("progress_events", [])
            if progress_events:
                return progress_events[-1]  # latest event from this node
            return ProgressEvent(
                event_type="progress",
                step=node_name,
                agent=self._config.agent_type,
                message=f"Completed {node_name}",
            ).to_dict()
        return {}
