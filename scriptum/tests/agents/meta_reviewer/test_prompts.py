"""Tests for Meta Reviewer prompt constants."""

from __future__ import annotations

from agents.meta_reviewer.prompts import (
    AGGREGATION_ANALYZE,
    AGGREGATION_REPORT,
    AGGREGATION_SYNTHESIZE,
    DESK_CHECK_FORMATTING,
    DESK_CHECK_RESEARCH,
    DESK_CHECK_SCOPE,
    META_REVIEWER_SYSTEM,
)


class TestPromptConstants:
    def test_all_prompts_are_nonempty_strings(self) -> None:
        prompts = [
            META_REVIEWER_SYSTEM,
            DESK_CHECK_RESEARCH,
            DESK_CHECK_SCOPE,
            DESK_CHECK_FORMATTING,
            AGGREGATION_ANALYZE,
            AGGREGATION_SYNTHESIZE,
            AGGREGATION_REPORT,
        ]
        for prompt in prompts:
            assert isinstance(prompt, str)
            assert len(prompt.strip()) > 50

    def test_system_prompt_establishes_role(self) -> None:
        assert "Meta Reviewer" in META_REVIEWER_SYSTEM
        assert "evidence" in META_REVIEWER_SYSTEM.lower()
        assert "transparent" in META_REVIEWER_SYSTEM.lower()

    def test_json_prompts_mention_json_format(self) -> None:
        json_prompts = [
            DESK_CHECK_SCOPE,
            DESK_CHECK_FORMATTING,
            AGGREGATION_ANALYZE,
            AGGREGATION_SYNTHESIZE,
            AGGREGATION_REPORT,
        ]
        for prompt in json_prompts:
            assert "JSON" in prompt or "json" in prompt or "{" in prompt

    def test_desk_check_scope_has_placeholders(self) -> None:
        assert "{abstract}" in DESK_CHECK_SCOPE
        assert "{title}" in DESK_CHECK_SCOPE
        assert "{journal_scope}" in DESK_CHECK_SCOPE

    def test_desk_check_formatting_has_placeholders(self) -> None:
        assert "{sections}" in DESK_CHECK_FORMATTING
        assert "{page_count}" in DESK_CHECK_FORMATTING
        assert "{formatting_rules}" in DESK_CHECK_FORMATTING

    def test_aggregation_prompts_have_placeholders(self) -> None:
        assert "{n_reviewers}" in AGGREGATION_ANALYZE
        assert "{reviewer_results}" in AGGREGATION_ANALYZE
        assert "{reviewer_scores}" in AGGREGATION_SYNTHESIZE
        assert "{criteria_weights}" in AGGREGATION_SYNTHESIZE
        assert "{scores}" in AGGREGATION_REPORT
        assert "{reviewer_feedback}" in AGGREGATION_REPORT

    def test_desk_check_research_has_placeholders(self) -> None:
        assert "{journal_name}" in DESK_CHECK_RESEARCH
        assert "{domain_general}" in DESK_CHECK_RESEARCH
