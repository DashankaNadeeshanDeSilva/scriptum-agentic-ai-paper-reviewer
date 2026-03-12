"""Tests for reviewer prompt constants."""

from __future__ import annotations

from scriptum_ai.agents.reviewers.prompts import (
    ADJACENT_EXPERT_SYSTEM,
    ANALYZE_PROMPT,
    CORE_EXPERT_SYSTEM,
    EVALUATE_PROMPT,
    GENERATE_FEEDBACK_PROMPT,
    METHODS_SPECIALIST_SYSTEM,
    RESEARCH_PROMPT,
)


class TestSystemPrompts:
    def test_all_system_prompts_are_nonempty(self) -> None:
        for prompt in [CORE_EXPERT_SYSTEM, ADJACENT_EXPERT_SYSTEM, METHODS_SPECIALIST_SYSTEM]:
            assert isinstance(prompt, str)
            assert len(prompt.strip()) > 100

    def test_core_expert_focuses_on_novelty(self) -> None:
        assert "Novelty" in CORE_EXPERT_SYSTEM
        assert "domain specialist" in CORE_EXPERT_SYSTEM.lower()

    def test_adjacent_expert_focuses_on_impact(self) -> None:
        assert "Significance" in ADJACENT_EXPERT_SYSTEM
        assert "cross-disciplinary" in ADJACENT_EXPERT_SYSTEM.lower()

    def test_methods_specialist_focuses_on_methodology(self) -> None:
        assert "Methodology" in METHODS_SPECIALIST_SYSTEM
        assert "reproducibility" in METHODS_SPECIALIST_SYSTEM.lower()

    def test_all_system_prompts_enforce_independence(self) -> None:
        for prompt in [CORE_EXPERT_SYSTEM, ADJACENT_EXPERT_SYSTEM, METHODS_SPECIALIST_SYSTEM]:
            assert "INDEPENDENT" in prompt

    def test_all_system_prompts_require_evidence(self) -> None:
        for prompt in [CORE_EXPERT_SYSTEM, ADJACENT_EXPERT_SYSTEM, METHODS_SPECIALIST_SYSTEM]:
            assert "evidence" in prompt.lower()


class TestTaskPrompts:
    def test_all_task_prompts_are_nonempty(self) -> None:
        for prompt in [RESEARCH_PROMPT, ANALYZE_PROMPT, EVALUATE_PROMPT, GENERATE_FEEDBACK_PROMPT]:
            assert isinstance(prompt, str)
            assert len(prompt.strip()) > 100

    def test_research_prompt_has_placeholders(self) -> None:
        assert "{title}" in RESEARCH_PROMPT
        assert "{abstract}" in RESEARCH_PROMPT
        assert "{perspective}" in RESEARCH_PROMPT
        assert "{focus_areas}" in RESEARCH_PROMPT

    def test_analyze_prompt_has_placeholders(self) -> None:
        assert "{title}" in ANALYZE_PROMPT
        assert "{paper_sections}" in ANALYZE_PROMPT
        assert "{research_findings}" in ANALYZE_PROMPT
        assert "{perspective}" in ANALYZE_PROMPT

    def test_evaluate_prompt_has_placeholders(self) -> None:
        assert "{analysis}" in EVALUATE_PROMPT
        assert "{criteria}" in EVALUATE_PROMPT
        assert "{focus_areas}" in EVALUATE_PROMPT

    def test_generate_feedback_prompt_has_placeholders(self) -> None:
        assert "{scores}" in GENERATE_FEEDBACK_PROMPT
        assert "{analysis}" in GENERATE_FEEDBACK_PROMPT
        assert "{evidence}" in GENERATE_FEEDBACK_PROMPT

    def test_json_prompts_mention_json_format(self) -> None:
        for prompt in [RESEARCH_PROMPT, ANALYZE_PROMPT, EVALUATE_PROMPT, GENERATE_FEEDBACK_PROMPT]:
            assert "JSON" in prompt or "json" in prompt or "{" in prompt
