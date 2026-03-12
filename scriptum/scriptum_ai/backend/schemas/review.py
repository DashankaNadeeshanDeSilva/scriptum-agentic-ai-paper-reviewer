"""Pydantic v2 schemas for the SCRIPTUM Review API.

These schemas define the request/response contracts for all review-related
endpoints. They are intentionally separate from SQLAlchemy models to allow
independent evolution of the API surface and database layer.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class StartReviewRequest(BaseModel):
    """Request body for starting a new review."""

    file_ids: list[UUID] = Field(
        ..., min_length=1, description="IDs of uploaded files (at least one PDF)"
    )
    journal_name: str = Field(..., min_length=1, max_length=255)
    domain_general: str = Field(..., min_length=1, max_length=100)
    domain_specific: str = Field(..., min_length=1, max_length=100)
    llm_provider: str | None = Field(default=None, description="Override default LLM provider")
    llm_model: str | None = Field(default=None, description="Override default LLM model")


class FeedbackRequest(BaseModel):
    """Request body for submitting user feedback on a review."""

    rating: int = Field(..., ge=1, le=5, description="Overall satisfaction (1-5)")
    category_ratings: dict[str, int] | None = Field(
        default=None, description="Per-category ratings (e.g. {'novelty': 4, 'methodology': 5})"
    )
    comments: str | None = Field(default=None, max_length=5000)


# ---------------------------------------------------------------------------
# Agent & Progress Schemas
# ---------------------------------------------------------------------------


class AgentStatus(BaseModel):
    """Status of an individual reviewer agent."""

    name: str
    status: str = Field(description="idle | working | completed | failed")
    progress_percent: float = Field(ge=0.0, le=100.0)
    current_task: str | None = None


class ReviewStatusResponse(BaseModel):
    """Current status and progress of a review."""

    review_id: UUID
    status: str = Field(
        description="pending | processing | desk_check | reviewing | aggregating | completed | failed | cancelled"
    )
    current_step: str
    progress_percent: float = Field(ge=0.0, le=100.0)
    agent_statuses: dict[str, AgentStatus] = Field(default_factory=dict)
    estimated_time_remaining: int | None = Field(default=None, description="Seconds remaining")


# ---------------------------------------------------------------------------
# Desk Check Schemas
# ---------------------------------------------------------------------------


class DeskCheckResult(BaseModel):
    """Result of the Meta Reviewer's initial desk check."""

    passed: bool
    scope_check: dict = Field(default_factory=dict)
    formatting_check: dict = Field(default_factory=dict)
    formatting_confidence: float = Field(
        ge=0.0, le=1.0, description="0-1, higher with LaTeX source"
    )
    issues: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Review Report Schemas
# ---------------------------------------------------------------------------


class ReviewScore(BaseModel):
    """Aggregated and per-reviewer score for a single category."""

    category: str
    score: float = Field(ge=0.0, le=10.0)
    reviewer_scores: dict[str, float] = Field(
        default_factory=dict, description="Mapping of reviewer_type -> score"
    )


class ReviewerReport(BaseModel):
    """Full report from a single reviewer agent."""

    reviewer_type: str = Field(description="core_expert | adjacent_expert | methods_specialist")
    scores: dict[str, float] = Field(default_factory=dict)
    feedback: dict[str, str] = Field(default_factory=dict, description="Per-category feedback text")
    evidence: list[dict] = Field(default_factory=list, description="Citations and evidence items")
    recommendation: str = Field(description="accept | minor_revision | major_revision | reject")
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    """The complete aggregated review report delivered to the user."""

    review_id: UUID
    recommendation: str = Field(description="accept | minor_revision | major_revision | reject")
    confidence: str = Field(description="high | medium | low")
    key_strengths: list[str] = Field(default_factory=list)
    key_weaknesses: list[str] = Field(default_factory=list)
    scores: list[ReviewScore] = Field(default_factory=list)
    detailed_feedback: dict[str, str] = Field(
        default_factory=dict, description="Per-category detailed feedback"
    )
    suggested_improvements: list[str] = Field(default_factory=list)
    individual_reviews: list[ReviewerReport] = Field(default_factory=list)
    desk_check: DeskCheckResult | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# File Schemas
# ---------------------------------------------------------------------------


class FileUploadResponse(BaseModel):
    """Response after uploading files."""

    file_id: UUID
    filename: str
    file_type: str
    size_bytes: int
    status: str = "accepted"


class FileInfo(BaseModel):
    """Metadata for a previously uploaded file."""

    file_id: UUID
    review_id: UUID | None = None
    filename: str
    file_type: str
    size_bytes: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Review List / Summary Schemas
# ---------------------------------------------------------------------------


class ReviewSummary(BaseModel):
    """Lightweight review info for list views and dashboard cards."""

    review_id: UUID
    status: str
    paper_title: str | None = None
    journal_name: str | None = None
    domain_general: str | None = None
    domain_specific: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    recommendation: str | None = Field(default=None, description="Set once review completes")
    created_at: datetime
    completed_at: datetime | None = None


class ReviewListResponse(BaseModel):
    """Paginated list of reviews."""

    reviews: list[ReviewSummary] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# WebSocket Event Schemas
# ---------------------------------------------------------------------------


class ReviewEvent(BaseModel):
    """Event streamed over WebSocket during a review."""

    type: str = Field(description="progress | step_complete | complete | error | info")
    step: str | None = None
    agent: str | None = None
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
    message: str | None = None
    result: dict | None = None
    report_id: UUID | None = None


# ---------------------------------------------------------------------------
# Settings Schemas (for API contract)
# ---------------------------------------------------------------------------


class LLMProviderSettings(BaseModel):
    """Settings for a single LLM provider."""

    enabled: bool = False
    model: str | None = None
    has_key: bool = False
    base_url: str | None = None


class SettingsResponse(BaseModel):
    """Full application settings (API keys masked)."""

    llm: dict = Field(default_factory=dict)
    mcp: dict = Field(default_factory=dict)
    apis: dict = Field(default_factory=dict)
    agents: dict = Field(default_factory=dict)


class SettingsUpdateRequest(BaseModel):
    """Partial settings update. All fields are optional; only provided fields are merged."""

    llm: dict | None = Field(default=None, description="Partial LLM config update")
    mcp: dict | None = Field(default=None, description="Partial MCP config update")
    apis: dict | None = Field(default=None, description="Partial APIs config update")
    agents: dict | None = Field(default=None, description="Partial agents config update")


class TestConnectionRequest(BaseModel):
    """Request to test an LLM provider connection."""

    provider: str = Field(..., description="anthropic | openai | ollama")
    model: str
    api_key: str | None = Field(default=None, description="API key (not needed for Ollama)")


class TestConnectionResponse(BaseModel):
    """Result of a connection test."""

    success: bool
    latency_ms: float | None = None
    model_info: str | None = None
    error: str | None = None
