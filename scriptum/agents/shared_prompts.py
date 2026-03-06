"""Shared prompt constants used across all SCRIPTUM reviewer and meta-reviewer agents.

These constants are appended to individual agent prompts to ensure consistent
scoring, evidence requirements, and bias mitigation across all reviewers.
"""

SCORING_RUBRIC = """\
## Scoring Rubric (0-10 Scale)

Apply this rubric consistently to every category you score:

- **0-1 (Fundamentally flawed)**: Critical errors that invalidate the work. \
Fabricated data, plagiarism, or completely unsound methodology.
- **2-3 (Major deficiencies)**: Serious issues that cannot be addressed by revision \
alone. Incorrect theoretical foundations, flawed experimental design, or misleading claims.
- **4-5 (Below acceptance threshold)**: Significant weaknesses that require major revision. \
Missing comparisons, incomplete analysis, or unsupported conclusions, but the core idea \
has potential.
- **6 (Borderline)**: Meets minimum standards but has notable gaps. Adequate methodology \
with some missing details. Results are valid but incremental.
- **7 (Good, solid contribution)**: Clear contribution to the field. Sound methodology, \
well-supported conclusions, and adequate presentation. Suitable for a respectable venue.
- **8 (Strong contribution)**: Above-average work. Novel insights, rigorous methodology, \
and clear presentation. Would strengthen any top venue.
- **9 (Excellent)**: Outstanding work that significantly advances the field. Innovative \
approach, comprehensive evaluation, and exceptional clarity.
- **10 (Exceptional, among the best)**: Landmark contribution. Reserve this for truly \
groundbreaking work that will reshape thinking in the field.

**Calibration guidance**: A score of 7 should represent a solid contribution suitable \
for a top venue. Most competent papers should score in the 5-7 range. Scores of 9-10 \
should be genuinely rare.
"""

DEBIASING_INSTRUCTIONS = """\
## Bias Mitigation

You MUST actively guard against these cognitive biases:

- **Prestige bias**: Do NOT favour or penalise work based on author reputation, \
institution, or venue history. Evaluate the work on its own merits.
- **Methodology bias**: Do NOT downgrade unfamiliar or unconventional approaches \
simply because they differ from your preferred methodology. If the approach is \
sound and well-justified, evaluate it fairly.
- **Position bias**: Do NOT let the order in which you encounter claims or \
sections influence your overall assessment. Give equal attention to all parts.
- **Confirmation bias**: Actively seek evidence that contradicts your initial \
impression. If your first reaction is positive, look harder for weaknesses; \
if negative, look harder for strengths.
- **Anchoring**: Do NOT anchor your scores to any initial impression or single \
metric. Evaluate each category independently before forming an overall view.

When uncertain, note your uncertainty explicitly rather than defaulting to a \
lower score. Distinguish clearly between "this is wrong" and "this is different \
from how I would do it."
"""

EVIDENCE_REQUIREMENT = """\
## Evidence Requirement

Every evaluative claim you make MUST cite specific evidence:

- **Paper references**: Cite by section (e.g., "Section 3.2", "Table 2", "Equation 5")
- **External sources**: Cite by identifier (e.g., "arXiv:2301.12345", "Semantic Scholar")
- **Direct quotes**: Include brief quotes from the paper when assessing specific claims

Claims without supporting evidence will be discarded during aggregation. \
Vague statements like "the methodology is weak" are insufficient — you must \
explain *why* and point to *where* in the paper the issue occurs.
"""
