"""Tests for shared prompt constants and their integration into agent prompts."""

from scriptum_ai.agents.shared_prompts import (
    DEBIASING_INSTRUCTIONS,
    EVIDENCE_REQUIREMENT,
    SCORING_RUBRIC,
)


class TestSharedPromptConstants:
    def test_scoring_rubric_has_full_scale(self):
        assert "0-1" in SCORING_RUBRIC
        assert "9" in SCORING_RUBRIC
        assert "10" in SCORING_RUBRIC
        assert "Calibration" in SCORING_RUBRIC

    def test_debiasing_instructions_covers_key_biases(self):
        assert "Prestige bias" in DEBIASING_INSTRUCTIONS
        assert "Methodology bias" in DEBIASING_INSTRUCTIONS
        assert "Confirmation bias" in DEBIASING_INSTRUCTIONS
        assert "Anchoring" in DEBIASING_INSTRUCTIONS

    def test_evidence_requirement_specifies_formats(self):
        assert "Section" in EVIDENCE_REQUIREMENT
        assert "arXiv" in EVIDENCE_REQUIREMENT
        assert "quotes" in EVIDENCE_REQUIREMENT.lower()


class TestReviewerPromptsIntegration:
    def test_reviewer_system_prompts_include_debiasing(self):
        from scriptum_ai.agents.reviewers.prompts import (
            ADJACENT_EXPERT_SYSTEM,
            CORE_EXPERT_SYSTEM,
            METHODS_SPECIALIST_SYSTEM,
        )

        for prompt in [CORE_EXPERT_SYSTEM, ADJACENT_EXPERT_SYSTEM, METHODS_SPECIALIST_SYSTEM]:
            assert "Prestige bias" in prompt
            assert "Evidence Requirement" in prompt

    def test_evaluate_prompt_includes_scoring_rubric(self):
        from scriptum_ai.agents.reviewers.prompts import EVALUATE_PROMPT

        assert "Calibration" in EVALUATE_PROMPT
        assert "0-1" in EVALUATE_PROMPT

    def test_meta_reviewer_includes_debiasing(self):
        from scriptum_ai.agents.meta_reviewer.prompts import META_REVIEWER_SYSTEM

        assert "Prestige bias" in META_REVIEWER_SYSTEM

    def test_aggregation_includes_scoring_and_anti_anchoring(self):
        from scriptum_ai.agents.meta_reviewer.prompts import AGGREGATION_SYNTHESIZE

        assert "Calibration" in AGGREGATION_SYNTHESIZE
        assert "Anti-anchoring" in AGGREGATION_SYNTHESIZE
