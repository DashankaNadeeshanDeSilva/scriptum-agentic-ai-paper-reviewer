"""Shared fixtures for Meta Reviewer agent tests."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.core.base import AgentConfig


@dataclass
class MockSearchResult:
    """Mimics tools.research.base.SearchResult for tool mock returns."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@pytest.fixture
def meta_config() -> AgentConfig:
    """AgentConfig for meta reviewer."""
    return AgentConfig(
        agent_type="meta_reviewer",
        provider="openai",
        model="gpt-4",
        timeout=60,
    )


@pytest.fixture
def mock_llm_response():
    """Factory for creating mock LLM responses with configurable JSON text."""

    def _make(text: str):
        resp = MagicMock()
        resp.text = text
        resp.model = "gpt-4"
        resp.provider = "openai"
        resp.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        resp.latency_ms = 500.0
        resp.cost_usd = 0.01
        return resp

    return _make


@pytest.fixture
def mock_rag_tool():
    """Mock RAGTool."""
    tool = AsyncMock()
    tool.name = "rag"
    tool.description = "RAG tool"
    tool.execute = AsyncMock(return_value=[])
    tool.store = AsyncMock()
    tool.query = AsyncMock(return_value=[])
    return tool


@pytest.fixture
def mock_perplexity_tool():
    """Mock PerplexityTool returning SearchResult-like objects."""
    tool = AsyncMock()
    tool.name = "perplexity"
    tool.description = "Perplexity"
    tool.execute = AsyncMock(
        return_value=[
            MockSearchResult(
                title="Nature Author Guidelines",
                url="https://nature.com/guidelines",
                snippet="Nature publishes outstanding research across all fields of science.",
                source="perplexity",
            )
        ]
    )
    return tool


@pytest.fixture
def mock_google_tool():
    """Mock GoogleSearchTool returning SearchResult-like objects."""
    tool = AsyncMock()
    tool.name = "google_search"
    tool.description = "Google Search"
    tool.execute = AsyncMock(
        return_value=[
            MockSearchResult(
                title="Nature Submission Guide",
                url="https://nature.com/submission",
                snippet="Page limit: 8 pages. Double-blind review.",
                source="google",
            )
        ]
    )
    return tool


@pytest.fixture
def sample_paper_dict() -> dict:
    """A realistic ParsedDocument.to_dict() for testing."""
    return {
        "metadata": {
            "title": "Attention Is All You Need",
            "abstract": (
                "We propose a new simple network architecture, the Transformer, "
                "based solely on attention mechanisms, dispensing with recurrence "
                "and convolutions entirely."
            ),
            "authors": ["Ashish Vaswani", "Noam Shazeer"],
            "page_count": 11,
        },
        "sections": [
            {"heading": "Abstract", "text": "..."},
            {"heading": "Introduction", "text": "..."},
            {"heading": "Related Work", "text": "..."},
            {"heading": "Model Architecture", "text": "..."},
            {"heading": "Experiments", "text": "..."},
            {"heading": "Results", "text": "..."},
            {"heading": "Conclusion", "text": "..."},
        ],
        "tables": [],
        "figures": [],
        "equations": [],
        "references": [],
    }


@pytest.fixture
def sample_journal_config() -> dict:
    """Journal config matching a Nature-like journal."""
    return {
        "name": "Nature",
        "scope": (
            "Publishes outstanding research across all fields of science and technology."
        ),
        "formatting_rules": {
            "page_limit": 8,
            "citation_style": "Nature",
            "double_blind": False,
            "abstract_word_limit": 150,
            "required_sections": [
                "Abstract",
                "Introduction",
                "Results",
                "Discussion",
                "Methods",
            ],
        },
    }


@pytest.fixture
def sample_reviewer_results() -> list[dict]:
    """Three ReviewResult.to_dict() dicts with varying scores."""
    return [
        {
            "reviewer_type": "core_expert",
            "scores": {
                "novelty": 8.0,
                "methodology": 7.5,
                "significance": 8.0,
                "presentation": 7.0,
                "reproducibility": 6.5,
            },
            "feedback": {
                "novelty": "The Transformer architecture is highly novel.",
                "methodology": "Sound experimental design with proper baselines.",
                "significance": "Likely to have major impact on NLP.",
                "presentation": "Well-written but dense in places.",
                "reproducibility": "Hyperparameters given but code not released.",
            },
            "evidence": [
                {"claim": "Novel attention mechanism", "source": "paper:section:3", "quote": "...", "relevance": 0.9}
            ],
            "recommendation": "accept",
            "confidence": 0.85,
            "strengths": ["Highly original architecture", "Strong empirical results"],
            "weaknesses": ["Could improve code release"],
        },
        {
            "reviewer_type": "adjacent_expert",
            "scores": {
                "novelty": 7.5,
                "methodology": 6.0,
                "significance": 9.0,
                "presentation": 8.0,
                "reproducibility": 5.0,
            },
            "feedback": {
                "novelty": "Novel approach from a cross-domain perspective.",
                "methodology": "Some concerns about scalability claims.",
                "significance": "Extremely impactful for broad ML community.",
                "presentation": "Accessible to non-NLP researchers.",
                "reproducibility": "Lack of code is concerning.",
            },
            "evidence": [],
            "recommendation": "minor_revision",
            "confidence": 0.7,
            "strengths": ["Broad impact", "Clear writing"],
            "weaknesses": ["Reproducibility concerns", "Scalability analysis needed"],
        },
        {
            "reviewer_type": "methods_specialist",
            "scores": {
                "novelty": 7.0,
                "methodology": 8.5,
                "significance": 7.5,
                "presentation": 7.0,
                "reproducibility": 7.0,
            },
            "feedback": {
                "novelty": "Attention-only approach is a significant departure.",
                "methodology": "Rigorous ablation studies and baselines.",
                "significance": "Solid contribution to sequence modeling.",
                "presentation": "Notation could be improved.",
                "reproducibility": "Sufficient detail for reproduction.",
            },
            "evidence": [],
            "recommendation": "accept",
            "confidence": 0.8,
            "strengths": ["Thorough ablations", "Strong baselines"],
            "weaknesses": ["Notation inconsistencies"],
        },
    ]


@pytest.fixture
def sample_review_criteria() -> dict:
    """Review criteria weights (sum to 1.0)."""
    return {
        "novelty": 0.25,
        "methodology": 0.25,
        "significance": 0.20,
        "presentation": 0.15,
        "reproducibility": 0.15,
    }
