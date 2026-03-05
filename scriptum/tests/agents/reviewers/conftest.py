"""Shared fixtures for reviewer agent tests."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.core.base import AgentConfig


@dataclass
class MockSearchResult:
    """Mimics tools.research.base.SearchResult."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""


@pytest.fixture
def core_expert_config() -> AgentConfig:
    return AgentConfig(
        agent_type="core_expert",
        provider="openai",
        model="gpt-4",
        timeout=60,
    )


@pytest.fixture
def adjacent_expert_config() -> AgentConfig:
    return AgentConfig(
        agent_type="adjacent_expert",
        provider="openai",
        model="gpt-4",
        timeout=60,
    )


@pytest.fixture
def methods_specialist_config() -> AgentConfig:
    return AgentConfig(
        agent_type="methods_specialist",
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
    tool = AsyncMock()
    tool.name = "rag"
    tool.description = "RAG tool"
    tool.execute = AsyncMock(return_value=[])
    tool.store = AsyncMock()
    tool.query = AsyncMock(return_value=[])
    return tool


@pytest.fixture
def mock_perplexity_tool():
    tool = AsyncMock()
    tool.name = "perplexity"
    tool.description = "Perplexity"
    tool.execute = AsyncMock(
        return_value=[
            MockSearchResult(
                title="Attention Is All You Need",
                url="https://arxiv.org/abs/1706.03762",
                snippet="The Transformer architecture uses self-attention mechanisms.",
                source="perplexity",
            )
        ]
    )
    return tool


@pytest.fixture
def mock_arxiv_tool():
    tool = AsyncMock()
    tool.name = "arxiv"
    tool.description = "arXiv"
    tool.execute = AsyncMock(
        return_value=[
            MockSearchResult(
                title="BERT: Pre-training of Deep Bidirectional Transformers",
                url="https://arxiv.org/abs/1810.04805",
                snippet="We introduce BERT, a new language representation model.",
                source="arxiv",
            )
        ]
    )
    return tool


@pytest.fixture
def mock_semantic_scholar_tool():
    tool = AsyncMock()
    tool.name = "semantic_scholar"
    tool.description = "Semantic Scholar"
    tool.execute = AsyncMock(
        return_value=[
            MockSearchResult(
                title="Deep Residual Learning",
                url="https://semantic-scholar.org/paper/123",
                snippet="Residual connections enable training of very deep networks.",
                source="semantic_scholar",
            )
        ]
    )
    return tool


@pytest.fixture
def mock_google_tool():
    tool = AsyncMock()
    tool.name = "google_search"
    tool.description = "Google Search"
    tool.execute = AsyncMock(
        return_value=[
            MockSearchResult(
                title="Transformer Survey",
                url="https://example.com/survey",
                snippet="A comprehensive survey of transformer architectures.",
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
            {"heading": "Abstract", "text": "We propose a new architecture..."},
            {"heading": "Introduction", "text": "Recurrent neural networks..."},
            {"heading": "Model Architecture", "text": "The Transformer follows an encoder-decoder..."},
            {"heading": "Experiments", "text": "We trained on WMT 2014..."},
            {"heading": "Results", "text": "Our model achieves 28.4 BLEU..."},
            {"heading": "Conclusion", "text": "We presented the Transformer..."},
        ],
        "tables": [],
        "figures": [],
        "equations": [],
        "references": [],
    }


@pytest.fixture
def sample_task_input(sample_paper_dict) -> dict:
    """Input data for execute() matching ReviewTask.to_dict() shape."""
    return {
        "paper": sample_paper_dict,
        "journal_config": {"name": "Nature", "scope": "All fields of science"},
        "domain_general": "Computer Science",
        "domain_specific": "Natural Language Processing",
        "review_criteria": {
            "novelty": 0.25,
            "methodology": 0.25,
            "significance": 0.20,
            "presentation": 0.15,
            "reproducibility": 0.15,
        },
    }
