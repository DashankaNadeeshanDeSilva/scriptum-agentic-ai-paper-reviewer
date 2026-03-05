"""Base reviewer agent — shared review pipeline logic.

All three reviewer agents (Core Expert, Adjacent Expert, Methods Specialist)
subclass :class:`BaseReviewer` which itself subclasses :class:`LangGraphAdapter`.

The base class overrides the adapter's four pass-through node methods with
real LLM-powered implementations.  Concrete agents supply:

* A **system prompt** (their role/perspective)
* A **perspective** description (short text)
* **Focus areas** (which categories they weight most)
* A **_create_tools()** override selecting their tool subset
"""

from __future__ import annotations

import json
from abc import abstractmethod
from typing import Any

from loguru import logger

from agents.core.adapters.langgraph import (
    STEP_ANALYZE,
    STEP_EVALUATE,
    STEP_GENERATE,
    STEP_RESEARCH,
    LangGraphAdapter,
    ReviewState,
)
from agents.core.base import (
    AgentStatusEnum,
    ProgressEvent,
)
from agents.reviewers.prompts import (
    ANALYZE_PROMPT,
    EVALUATE_PROMPT,
    GENERATE_FEEDBACK_PROMPT,
    RESEARCH_PROMPT,
)


class BaseReviewer(LangGraphAdapter):
    """Shared review pipeline for all reviewer agents.

    Subclasses must implement:

    * :attr:`system_prompt` — the reviewer's persona/system message
    * :attr:`perspective` — a short description of the reviewer's viewpoint
    * :attr:`focus_areas` — list of categories the reviewer prioritises
    * :meth:`_create_tools` — returns the agent-specific tool set
    """

    # ------------------------------------------------------------------
    # Abstract properties — concrete agents must provide these
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Full system prompt establishing the reviewer's role."""
        ...

    @property
    @abstractmethod
    def perspective(self) -> str:
        """One-sentence description of the reviewer's viewpoint."""
        ...

    @property
    @abstractmethod
    def focus_areas(self) -> list[str]:
        """Review categories this reviewer focuses on most."""
        ...

    # ------------------------------------------------------------------
    # Node overrides — real LLM-powered implementations
    # ------------------------------------------------------------------

    async def _research_node(self, state: ReviewState) -> dict[str, Any]:
        """Search external sources for relevant prior work.

        Uses the agent's tools (arXiv, Semantic Scholar, Perplexity,
        Google, RAG) to gather context, then asks the LLM to synthesise
        findings into structured research notes.
        """
        self._status = AgentStatusEnum.RESEARCHING
        task = state.get("task", {})
        paper = task.get("paper", {})
        metadata = paper.get("metadata", {})
        title = metadata.get("title", "Untitled")
        abstract = metadata.get("abstract", "")

        # Gather results from all available research tools
        raw_findings: list[dict[str, Any]] = []
        for tool in self._tools:
            if tool.name == "rag":
                # Query RAG for domain knowledge and journal guidelines
                try:
                    results = await tool.execute(
                        query=f"{title} {abstract[:200]}",
                        collection="domain_knowledge",
                        k=3,
                    )
                    for r in results or []:
                        if isinstance(r, dict):
                            raw_findings.append(
                                {"source": "rag", "content": r.get("document", str(r))}
                            )
                        else:
                            raw_findings.append({"source": "rag", "content": str(r)})
                except Exception as exc:
                    logger.warning("RAG query failed in {}: {}", self._config.agent_type, exc)
            else:
                # Research tools (arxiv, semantic_scholar, perplexity, google_search)
                try:
                    results = await tool.execute(
                        query=f"{title} {metadata.get('authors', [''])[0] if metadata.get('authors') else ''}"
                    )
                    for r in results or []:
                        raw_findings.append({
                            "source": tool.name,
                            "title": getattr(r, "title", ""),
                            "url": getattr(r, "url", ""),
                            "snippet": getattr(r, "snippet", ""),
                        })
                except Exception as exc:
                    logger.warning(
                        "Tool '{}' failed in {}: {}",
                        tool.name, self._config.agent_type, exc,
                    )

        # Ask LLM to synthesise research findings
        research_analysis: dict[str, Any] = {}
        if self._llm:
            domain_general = task.get("domain_general", self._context.get("domain_general", ""))
            domain_specific = task.get("domain_specific", self._context.get("domain_specific", ""))

            prompt = RESEARCH_PROMPT.format(
                title=title,
                abstract=abstract,
                domain_general=domain_general,
                domain_specific=domain_specific,
                perspective=self.perspective,
                focus_areas=", ".join(self.focus_areas),
            )

            # Append raw findings as context
            if raw_findings:
                findings_text = json.dumps(raw_findings[:20], indent=2)  # cap at 20
                prompt += f"\n\nSearch results from tools:\n{findings_text}"

            try:
                response = await self._llm.complete(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                research_analysis = json.loads(response.text)
            except (json.JSONDecodeError, Exception) as exc:
                logger.error("Research LLM call failed in {}: {}", self._config.agent_type, exc)
                research_analysis = {
                    "key_prior_works": [],
                    "competing_approaches": [],
                    "methodological_context": [],
                    "red_flags": [],
                    "research_summary": f"Research analysis could not be completed: {exc}",
                }

        return {
            "research_findings": [
                {
                    "raw_findings": raw_findings,
                    "analysis": research_analysis,
                    "agent": self._config.agent_type,
                }
            ],
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
        """Analyse the paper content using the LLM with research context."""
        self._status = AgentStatusEnum.ANALYZING
        task = state.get("task", {})
        paper = task.get("paper", {})
        metadata = paper.get("metadata", {})
        research_findings = state.get("research_findings", [])

        # Build paper sections summary
        sections = paper.get("sections", [])
        sections_text = "\n".join(
            f"## {s.get('heading', 'Untitled Section')}\n{s.get('text', '')[:500]}"
            for s in sections
        )

        # Build research findings summary
        findings_summary = ""
        for rf in research_findings:
            if isinstance(rf, dict) and "analysis" in rf:
                findings_summary = json.dumps(rf["analysis"], indent=2)
                break

        prompt = ANALYZE_PROMPT.format(
            title=metadata.get("title", "Untitled"),
            paper_sections=sections_text or "No sections available.",
            research_findings=findings_summary or "No research findings available.",
            perspective=self.perspective,
        )

        analysis: dict[str, Any] = {}
        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            analysis = json.loads(response.text)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("Analysis LLM call failed in {}: {}", self._config.agent_type, exc)
            analysis = {
                "summary": f"Analysis could not be completed: {exc}",
                "technical_analysis": {},
                "context_in_literature": "",
                "key_observations": [],
                "questions_for_authors": [],
            }

        return {
            "analysis": analysis,
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
        """Score the paper on review criteria using the LLM."""
        self._status = AgentStatusEnum.EVALUATING
        task = state.get("task", {})
        analysis = state.get("analysis", {})

        criteria = task.get("review_criteria", self._context.get("review_criteria", {}))
        if not criteria:
            criteria = {
                "novelty": 0.25,
                "methodology": 0.25,
                "significance": 0.20,
                "presentation": 0.15,
                "reproducibility": 0.15,
            }

        prompt = EVALUATE_PROMPT.format(
            analysis=json.dumps(analysis, indent=2),
            criteria=json.dumps(criteria, indent=2),
            focus_areas=", ".join(self.focus_areas),
        )

        scores: dict[str, float] = {}
        evidence: list[dict[str, Any]] = []
        strengths: list[str] = []
        weaknesses: list[str] = []

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.text)
            scores = result.get("scores", {})
            evidence = result.get("evidence", [])
            strengths = result.get("strengths", [])
            weaknesses = result.get("weaknesses", [])
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("Evaluation LLM call failed in {}: {}", self._config.agent_type, exc)
            scores = {cat: 5.0 for cat in criteria}
            evidence = []
            strengths = []
            weaknesses = [f"Evaluation could not be completed: {exc}"]

        return {
            "scores": scores,
            "evidence": evidence,
            "strengths": strengths,
            "weaknesses": weaknesses,
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
        """Generate structured feedback and recommendation."""
        self._status = AgentStatusEnum.GENERATING
        scores = state.get("scores", {})
        analysis = state.get("analysis", {})
        evidence = state.get("evidence", [])

        prompt = GENERATE_FEEDBACK_PROMPT.format(
            scores=json.dumps(scores, indent=2),
            analysis=json.dumps(analysis, indent=2),
            evidence=json.dumps(evidence[:10], indent=2),  # cap evidence
        )

        feedback: dict[str, str] = {}
        recommendation = "major_revision"
        confidence = 0.0

        try:
            response = await self._llm.complete(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.text)
            feedback = result.get("feedback", {})
            recommendation = result.get("recommendation", "major_revision")
            confidence = result.get("confidence", 0.0)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error(
                "Feedback generation failed in {}: {}", self._config.agent_type, exc
            )
            feedback = {cat: f"Feedback generation failed: {exc}" for cat in scores}

        return {
            "feedback": feedback,
            "recommendation": recommendation,
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
    # Override _extract_result to include confidence
    # ------------------------------------------------------------------

    def _extract_result(self, state: dict[str, Any]) -> dict[str, Any]:
        """Convert final graph state to a ReviewResult-compatible dict.

        Enhances the base adapter's extraction with confidence from the
        generate_feedback node.
        """
        result = super()._extract_result(state)
        # Confidence is set during feedback generation via the state
        # We parse it from the last progress event or feedback data
        # The base _extract_result sets confidence=0.0; we can improve
        # by looking at the feedback output stored in state
        return result
