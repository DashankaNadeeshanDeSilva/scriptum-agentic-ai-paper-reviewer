"""Meta Reviewer agent — desk check and review aggregation.

The Meta Reviewer operates in two distinct modes, each backed by its own
LangGraph ``StateGraph``:

**Desk Check** — screens a paper for journal scope alignment and formatting
compliance before it reaches the independent reviewers.

**Aggregation** — synthesizes the independent reviewer reports into a single
coherent final review with an overall recommendation.

The agent implements :class:`AgentInterface` directly (rather than
subclassing :class:`LangGraphAdapter`) because it needs two separate
graphs with different state schemas.
"""

from __future__ import annotations

import asyncio
import json
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
    ToolInterface,
)
from scriptum_ai.agents.meta_reviewer.prompts import (
    AGGREGATION_ANALYZE,
    AGGREGATION_REPORT,
    AGGREGATION_SYNTHESIZE,
    DESK_CHECK_FORMATTING,
    DESK_CHECK_SCOPE,
    META_REVIEWER_SYSTEM,
)
from scriptum_ai.agents.meta_reviewer.tools import create_meta_reviewer_tools
from scriptum_ai.backend.core.llm import LLMClient

# ---------------------------------------------------------------------------
# Graph state definitions
# ---------------------------------------------------------------------------


class DeskCheckState(TypedDict, total=False):
    """State flowing through the desk-check graph."""

    task: dict[str, Any]  # ReviewTask.to_dict()
    context: dict[str, Any]  # journal_name, domain, etc.
    journal_guidelines: dict[str, Any]  # researched guidelines
    scope_result: dict[str, Any]  # LLM scope-check output
    formatting_result: dict[str, Any]  # LLM formatting-check output
    progress_events: Annotated[list[dict[str, Any]], operator.add]


class AggregationState(TypedDict, total=False):
    """State flowing through the aggregation graph."""

    reviewer_results: list[dict[str, Any]]  # list of ReviewResult dicts
    review_criteria: dict[str, float]  # category -> weight
    context: dict[str, Any]
    analysis: dict[str, Any]  # consensus / conflicts
    synthesis: dict[str, Any]  # weighted scores, recommendation
    report: dict[str, Any]  # final report JSON
    progress_events: Annotated[list[dict[str, Any]], operator.add]


# ---------------------------------------------------------------------------
# Node-step constants (used for progress tracking)
# ---------------------------------------------------------------------------

STEP_RESEARCH_JOURNAL = "research_journal"
STEP_CHECK_SCOPE = "check_scope"
STEP_CHECK_FORMATTING = "check_formatting"

STEP_COLLECT_ANALYZE = "collect_and_analyze"
STEP_SYNTHESIZE = "synthesize_scores"
STEP_GENERATE_REPORT = "generate_report"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class MetaReviewerAgent(AgentInterface):
    """Meta Reviewer: desk check + review aggregation.

    Two separate LangGraph pipelines:

    * **Desk check** ``research_journal → check_scope → check_formatting → END``
    * **Aggregation** ``collect_and_analyze → synthesize_scores → generate_report → END``

    Usage::

        agent = MetaReviewerAgent(config)
        await agent.initialize()

        # Desk check
        agent.set_context({"journal_name": "Nature", ...})
        result = await agent.desk_check({"task": review_task.to_dict()})

        # Aggregation (after reviewers finish)
        result = await agent.aggregate({
            "reviewer_results": [r1, r2, r3],
            "review_criteria": {"novelty": 0.25, ...},
        })
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        self._config = config or AgentConfig(agent_type="meta_reviewer")
        self._llm: LLMClient | None = None
        self._tools: list[ToolInterface] = []
        self._desk_check_graph: Any = None
        self._aggregation_graph: Any = None
        self._status: AgentStatusEnum = AgentStatusEnum.IDLE
        self._context: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # AgentInterface — lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create LLM client, instantiate tools, compile both graphs."""
        try:
            self._status = AgentStatusEnum.INITIALIZING

            self._llm = LLMClient(
                provider=self._config.provider,
                model=self._config.model,
            )

            self._tools = create_meta_reviewer_tools(self._config.tools_enabled or None)

            self._desk_check_graph = self._build_desk_check_graph()
            self._aggregation_graph = self._build_aggregation_graph()

            self._status = AgentStatusEnum.IDLE
            logger.info("MetaReviewerAgent initialised")
        except Exception as exc:
            self._status = AgentStatusEnum.FAILED
            logger.error("MetaReviewerAgent initialisation failed: {}", exc)
            raise

    async def cleanup(self) -> None:
        """Release resources."""
        self._llm = None
        self._tools = []
        self._desk_check_graph = None
        self._aggregation_graph = None
        self._status = AgentStatusEnum.IDLE

    # ------------------------------------------------------------------
    # AgentInterface — execution (routes by mode)
    # ------------------------------------------------------------------

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Route to :meth:`desk_check` or :meth:`aggregate` based on ``mode``."""
        mode = input_data.get("mode", "desk_check")
        if mode == "desk_check":
            return await self.desk_check(input_data)
        if mode == "aggregate":
            return await self.aggregate(input_data)
        raise ValueError(f"Unknown MetaReviewerAgent mode: {mode!r}")

    async def stream(self, input_data: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        """Stream progress events from the selected graph."""
        mode = input_data.get("mode", "desk_check")
        graph = self._desk_check_graph if mode == "desk_check" else self._aggregation_graph
        if graph is None:
            raise RuntimeError("Agent not initialised — call initialize() first")

        state = self._prepare_state(input_data, mode)
        async for event in graph.astream(state):
            yield self._format_stream_event(event)
        self._status = AgentStatusEnum.COMPLETED

    # ------------------------------------------------------------------
    # Public mode-specific methods
    # ------------------------------------------------------------------

    async def desk_check(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run the desk-check pipeline.

        Returns:
            A ``DeskCheckResult``-compatible dict with keys ``passed``,
            ``scope_check``, ``formatting_check``, ``formatting_confidence``,
            ``issues``.
        """
        if self._desk_check_graph is None:
            raise RuntimeError("Agent not initialised — call initialize() first")

        state = self._prepare_state(input_data, "desk_check")
        try:
            final = await asyncio.wait_for(
                self._desk_check_graph.ainvoke(state),
                timeout=self._config.timeout,
            )
            self._status = AgentStatusEnum.COMPLETED
            return self._extract_desk_check_result(final)
        except TimeoutError:
            self._status = AgentStatusEnum.FAILED
            raise RuntimeError(f"Desk check timed out after {self._config.timeout}s") from None
        except Exception:
            self._status = AgentStatusEnum.FAILED
            raise

    async def aggregate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run the aggregation pipeline.

        Returns:
            A partial ``ReviewReport``-compatible dict (the orchestrator
            in Step 3.3 adds ``review_id``, ``individual_reviews``,
            ``desk_check``, and ``created_at``).
        """
        if self._aggregation_graph is None:
            raise RuntimeError("Agent not initialised — call initialize() first")

        state = self._prepare_state(input_data, "aggregate")
        try:
            final = await asyncio.wait_for(
                self._aggregation_graph.ainvoke(state),
                timeout=self._config.timeout,
            )
            self._status = AgentStatusEnum.COMPLETED
            return self._extract_aggregation_result(final)
        except TimeoutError:
            self._status = AgentStatusEnum.FAILED
            raise RuntimeError(f"Aggregation timed out after {self._config.timeout}s") from None
        except Exception:
            self._status = AgentStatusEnum.FAILED
            raise

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
    # Graph builders
    # ------------------------------------------------------------------

    def _build_desk_check_graph(self) -> Any:
        """Build: research_journal → check_scope → check_formatting → END."""
        graph = StateGraph(DeskCheckState)
        graph.add_node(STEP_RESEARCH_JOURNAL, self._research_journal_node)
        graph.add_node(STEP_CHECK_SCOPE, self._check_scope_node)
        graph.add_node(STEP_CHECK_FORMATTING, self._check_formatting_node)
        graph.set_entry_point(STEP_RESEARCH_JOURNAL)
        graph.add_edge(STEP_RESEARCH_JOURNAL, STEP_CHECK_SCOPE)
        graph.add_edge(STEP_CHECK_SCOPE, STEP_CHECK_FORMATTING)
        graph.add_edge(STEP_CHECK_FORMATTING, END)
        return graph.compile()

    def _build_aggregation_graph(self) -> Any:
        """Build: collect_and_analyze → synthesize_scores → generate_report → END."""
        graph = StateGraph(AggregationState)
        graph.add_node(STEP_COLLECT_ANALYZE, self._collect_and_analyze_node)
        graph.add_node(STEP_SYNTHESIZE, self._synthesize_scores_node)
        graph.add_node(STEP_GENERATE_REPORT, self._generate_report_node)
        graph.set_entry_point(STEP_COLLECT_ANALYZE)
        graph.add_edge(STEP_COLLECT_ANALYZE, STEP_SYNTHESIZE)
        graph.add_edge(STEP_SYNTHESIZE, STEP_GENERATE_REPORT)
        graph.add_edge(STEP_GENERATE_REPORT, END)
        return graph.compile()

    # ------------------------------------------------------------------
    # Desk-check nodes
    # ------------------------------------------------------------------

    async def _research_journal_node(self, state: DeskCheckState) -> dict[str, Any]:
        """Use RAG + Perplexity + Google to gather journal guidelines."""
        self._status = AgentStatusEnum.RESEARCHING
        journal_name = state.get("context", {}).get("journal_name", "")
        guidelines: dict[str, Any] = {}

        # 1. Query RAG for pre-loaded journal guidelines
        rag = self._get_tool("rag")
        if rag:
            try:
                rag_results = await rag.execute(
                    query=f"{journal_name} scope formatting review criteria",
                    collection="journal_guidelines",
                    k=3,
                )
                if rag_results:
                    guidelines["stored"] = rag_results
            except Exception as exc:
                logger.warning("RAG query failed: {}", exc)

        # 2. Search Perplexity for journal info
        perplexity = self._get_tool("perplexity")
        if perplexity:
            try:
                results = await perplexity.execute(
                    query=(
                        f"{journal_name} author guidelines scope formatting requirements submission"
                    ),
                )
                if results:
                    guidelines["perplexity"] = [
                        {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
                    ]
            except Exception as exc:
                logger.warning("Perplexity search failed: {}", exc)

        # 3. Search Google for official guidelines page
        google = self._get_tool("google_search")
        if google:
            try:
                results = await google.execute(
                    query=f"{journal_name} author guidelines submission requirements",
                )
                if results:
                    guidelines["google"] = [
                        {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
                    ]
            except Exception as exc:
                logger.warning("Google search failed: {}", exc)

        # 4. Store discovered guidelines in RAG for reviewer agents
        if rag and (guidelines.get("perplexity") or guidelines.get("google")):
            try:
                texts: list[str] = []
                for source in ("perplexity", "google"):
                    for item in guidelines.get(source, []):
                        snippet = item.get("snippet", "")
                        if snippet:
                            texts.append(f"[{journal_name}] {snippet}")
                if texts:
                    await rag.store(
                        texts,
                        collection="journal_guidelines",
                        metadatas=[
                            {"journal_name": journal_name, "source": "research"} for _ in texts
                        ],
                    )
            except Exception as exc:
                logger.warning("Failed to store research results in RAG: {}", exc)

        return {
            "journal_guidelines": guidelines,
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_RESEARCH_JOURNAL,
                    agent="meta_reviewer",
                    progress=0.33,
                    message="Journal research complete",
                ).to_dict()
            ],
        }

    async def _check_scope_node(self, state: DeskCheckState) -> dict[str, Any]:
        """LLM analyses paper scope vs journal scope (JSON output)."""
        self._status = AgentStatusEnum.ANALYZING
        task = state.get("task", {})
        paper = task.get("paper", {})
        guidelines = state.get("journal_guidelines", {})

        journal_scope = self._extract_journal_scope(guidelines, task)
        metadata = paper.get("metadata", {})

        prompt = DESK_CHECK_SCOPE.format(
            abstract=metadata.get("abstract", "No abstract available."),
            title=metadata.get("title", "Untitled"),
            journal_scope=journal_scope,
        )

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": META_REVIEWER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            scope_result = json.loads(response.text)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("Scope check LLM call failed: {}", exc)
            scope_result = {
                "in_scope": True,
                "reasoning": f"Scope check could not be completed: {exc}",
                "confidence": 0.0,
                "scope_match_areas": [],
                "scope_concerns": [],
            }

        return {
            "scope_result": scope_result,
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_CHECK_SCOPE,
                    agent="meta_reviewer",
                    progress=0.66,
                    message="Scope check complete",
                ).to_dict()
            ],
        }

    async def _check_formatting_node(self, state: DeskCheckState) -> dict[str, Any]:
        """LLM checks paper formatting vs journal rules (JSON output)."""
        self._status = AgentStatusEnum.EVALUATING
        task = state.get("task", {})
        paper = task.get("paper", {})
        guidelines = state.get("journal_guidelines", {})

        formatting_rules = self._extract_formatting_rules(guidelines, task)
        sections = [s.get("heading", "") for s in paper.get("sections", [])]
        page_count = paper.get("metadata", {}).get("page_count", 0)

        prompt = DESK_CHECK_FORMATTING.format(
            sections=json.dumps(sections),
            page_count=page_count,
            formatting_rules=json.dumps(formatting_rules, indent=2),
        )

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": META_REVIEWER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            formatting_result = json.loads(response.text)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("Formatting check LLM call failed: {}", exc)
            formatting_result = {
                "passes": True,
                "issues": [],
                "confidence": 0.0,
                "missing_sections": [],
            }

        return {
            "formatting_result": formatting_result,
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_CHECK_FORMATTING,
                    agent="meta_reviewer",
                    progress=1.0,
                    message="Formatting check complete",
                ).to_dict()
            ],
        }

    # ------------------------------------------------------------------
    # Aggregation nodes
    # ------------------------------------------------------------------

    async def _collect_and_analyze_node(self, state: AggregationState) -> dict[str, Any]:
        """Parse reviewer results, identify agreements and conflicts."""
        self._status = AgentStatusEnum.ANALYZING
        reviewer_results = state.get("reviewer_results", [])

        prompt = AGGREGATION_ANALYZE.format(
            n_reviewers=len(reviewer_results),
            reviewer_results=json.dumps(reviewer_results, indent=2),
        )

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": META_REVIEWER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            analysis = json.loads(response.text)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("Aggregation analysis failed: {}", exc)
            analysis = {"consensus": [], "conflicts": [], "unique_insights": []}

        return {
            "analysis": analysis,
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_COLLECT_ANALYZE,
                    agent="meta_reviewer",
                    progress=0.33,
                    message="Review analysis complete",
                ).to_dict()
            ],
        }

    async def _synthesize_scores_node(self, state: AggregationState) -> dict[str, Any]:
        """Compute weighted scores and resolve conflicts."""
        self._status = AgentStatusEnum.EVALUATING
        reviewer_results = state.get("reviewer_results", [])
        review_criteria = state.get("review_criteria", {})
        analysis = state.get("analysis", {})

        reviewer_scores = {
            r.get("reviewer_type", f"reviewer_{i}"): r.get("scores", {})
            for i, r in enumerate(reviewer_results)
        }

        prompt = AGGREGATION_SYNTHESIZE.format(
            reviewer_scores=json.dumps(reviewer_scores, indent=2),
            criteria_weights=json.dumps(review_criteria, indent=2),
            conflicts=json.dumps(analysis.get("conflicts", []), indent=2),
        )

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": META_REVIEWER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            synthesis = json.loads(response.text)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("Score synthesis failed: {}", exc)
            synthesis = {
                "weighted_scores": {},
                "overall_score": 0.0,
                "conflict_resolutions": [],
                "recommendation": "major_revision",
                "confidence": "low",
            }

        return {
            "synthesis": synthesis,
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_SYNTHESIZE,
                    agent="meta_reviewer",
                    progress=0.66,
                    message="Score synthesis complete",
                ).to_dict()
            ],
        }

    async def _generate_report_node(self, state: AggregationState) -> dict[str, Any]:
        """Generate the final aggregated review report."""
        self._status = AgentStatusEnum.GENERATING
        reviewer_results = state.get("reviewer_results", [])
        synthesis = state.get("synthesis", {})

        reviewer_feedback = {
            r.get("reviewer_type", f"reviewer_{i}"): r.get("feedback", {})
            for i, r in enumerate(reviewer_results)
        }

        prompt = AGGREGATION_REPORT.format(
            scores=json.dumps(synthesis.get("weighted_scores", {}), indent=2),
            conflict_resolutions=json.dumps(synthesis.get("conflict_resolutions", []), indent=2),
            reviewer_feedback=json.dumps(reviewer_feedback, indent=2),
        )

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": META_REVIEWER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            report = json.loads(response.text)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("Report generation failed: {}", exc)
            report = {
                "recommendation": synthesis.get("recommendation", "major_revision"),
                "confidence": synthesis.get("confidence", "low"),
                "key_strengths": [],
                "key_weaknesses": [],
                "detailed_feedback": {},
                "suggested_improvements": [],
                "executive_summary": "Report generation encountered an error.",
            }

        return {
            "report": report,
            "progress_events": [
                ProgressEvent(
                    event_type="step_complete",
                    step=STEP_GENERATE_REPORT,
                    agent="meta_reviewer",
                    progress=1.0,
                    message="Report generation complete",
                ).to_dict()
            ],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_tool(self, name: str) -> ToolInterface | None:
        """Look up a tool by name from the agent's tool set."""
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    def _prepare_state(self, input_data: dict[str, Any], mode: str) -> dict[str, Any]:
        """Build initial graph state from input and context."""
        if mode == "desk_check":
            return DeskCheckState(
                task=input_data.get("task", input_data),
                context=self._context,
                journal_guidelines={},
                scope_result={},
                formatting_result={},
                progress_events=[],
            )
        return AggregationState(
            reviewer_results=input_data.get("reviewer_results", []),
            review_criteria=input_data.get("review_criteria", {}),
            context=self._context,
            analysis={},
            synthesis={},
            report={},
            progress_events=[],
        )

    def _extract_desk_check_result(self, state: dict[str, Any]) -> dict[str, Any]:
        """Convert final desk-check state to ``DeskCheckResult``-compatible dict."""
        scope = state.get("scope_result", {})
        formatting = state.get("formatting_result", {})

        scope_passed = scope.get("in_scope", True)
        formatting_passed = formatting.get("passes", True)

        issues: list[str] = []
        if not scope_passed:
            issues.extend(scope.get("scope_concerns", []))
        for item in formatting.get("issues", []):
            if isinstance(item, dict) and item.get("status") not in ("pass",):
                detail = item.get("detail", "")
                if detail:
                    issues.append(detail)

        return {
            "passed": scope_passed and formatting_passed,
            "scope_check": scope,
            "formatting_check": formatting,
            "formatting_confidence": formatting.get("confidence", 0.5),
            "issues": issues,
        }

    def _extract_aggregation_result(self, state: dict[str, Any]) -> dict[str, Any]:
        """Convert final aggregation state to partial ``ReviewReport``-compatible dict."""
        report = state.get("report", {})
        synthesis = state.get("synthesis", {})

        # Build ReviewScore list from weighted scores
        weighted = synthesis.get("weighted_scores", {})
        scores = [
            {"category": cat, "score": score, "reviewer_scores": {}}
            for cat, score in weighted.items()
        ]

        return {
            "recommendation": report.get(
                "recommendation",
                synthesis.get("recommendation", "major_revision"),
            ),
            "confidence": report.get("confidence", "medium"),
            "key_strengths": report.get("key_strengths", []),
            "key_weaknesses": report.get("key_weaknesses", []),
            "scores": scores,
            "detailed_feedback": report.get("detailed_feedback", {}),
            "suggested_improvements": report.get("suggested_improvements", []),
            "executive_summary": report.get("executive_summary", ""),
        }

    def _extract_journal_scope(self, guidelines: dict[str, Any], task: dict[str, Any]) -> str:
        """Build a scope description from RAG results + task context."""
        parts: list[str] = []
        # From journal_config in the task
        jc = task.get("journal_config", {})
        if scope := jc.get("scope", ""):
            parts.append(scope)
        # From RAG stored guidelines
        for item in guidelines.get("stored", []):
            if isinstance(item, dict):
                if doc := item.get("document", ""):
                    parts.append(doc)
        # From perplexity results
        for item in guidelines.get("perplexity", []):
            if snippet := item.get("snippet", ""):
                parts.append(snippet)
        return "\n".join(parts) if parts else "No journal scope information available."

    def _extract_formatting_rules(
        self, guidelines: dict[str, Any], task: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract formatting rules from task config + research."""
        rules = task.get("journal_config", {}).get("formatting_rules", {})
        return rules if rules else {"note": "No specific formatting rules found"}

    def _format_stream_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Format a raw LangGraph stream event into a progress dict."""
        for node_name, update in event.items():
            progress_events = update.get("progress_events", [])
            if progress_events:
                return progress_events[-1]
            return ProgressEvent(
                event_type="progress",
                step=node_name,
                agent="meta_reviewer",
                message=f"Completed {node_name}",
            ).to_dict()
        return {}
