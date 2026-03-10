"""Shared fixtures for research tool tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_settings():
    """Return a mock AppSettings with test API keys."""
    settings = MagicMock()

    # Semantic Scholar
    settings.apis.semantic_scholar.api_key = "test-s2-key"
    settings.apis.arxiv.enabled = True
    settings.apis.crossref.enabled = True

    # MCP (Perplexity + Google Search — config section kept for compatibility)
    settings.mcp.perplexity.api_key = "test-pplx-key"
    settings.mcp.perplexity.enabled = True
    settings.mcp.google_search.api_key = "test-google-key"
    settings.mcp.google_search.cx = "test-cx-id"
    settings.mcp.google_search.enabled = True

    return settings


@pytest.fixture
def mock_settings_no_keys():
    """Return a mock AppSettings with no API keys configured."""
    settings = MagicMock()

    settings.apis.semantic_scholar.api_key = ""
    settings.mcp.perplexity.api_key = ""
    settings.mcp.google_search.api_key = ""
    settings.mcp.google_search.cx = ""

    return settings


# ---------------------------------------------------------------------------
# Sample API responses
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_s2_search_response():
    """Sample Semantic Scholar paper search response."""
    return {
        "total": 2,
        "data": [
            {
                "paperId": "abc123",
                "title": "Attention Is All You Need",
                "abstract": "The dominant sequence transduction models...",
                "year": 2017,
                "venue": "NeurIPS",
                "citationCount": 50000,
                "url": "https://www.semanticscholar.org/paper/abc123",
                "authors": [
                    {"authorId": "1", "name": "Ashish Vaswani"},
                    {"authorId": "2", "name": "Noam Shazeer"},
                ],
                "externalIds": {
                    "DOI": "10.5555/3295222.3295349",
                    "ArXiv": "1706.03762",
                },
            },
            {
                "paperId": "def456",
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "abstract": "We introduce a new language representation model...",
                "year": 2019,
                "venue": "NAACL",
                "citationCount": 40000,
                "url": "https://www.semanticscholar.org/paper/def456",
                "authors": [{"authorId": "3", "name": "Jacob Devlin"}],
                "externalIds": {"DOI": "10.18653/v1/N19-1423", "ArXiv": "1810.04805"},
            },
        ],
    }


@pytest.fixture
def sample_s2_citations_response():
    """Sample Semantic Scholar citations response."""
    return {
        "data": [
            {
                "citingPaper": {
                    "paperId": "cite1",
                    "title": "GPT-2",
                    "year": 2019,
                    "venue": "",
                    "citationCount": 5000,
                    "url": "https://www.semanticscholar.org/paper/cite1",
                    "authors": [{"name": "Alec Radford"}],
                    "externalIds": {},
                }
            }
        ]
    }


@pytest.fixture
def sample_perplexity_response():
    """Sample Perplexity chat completions response."""
    return {
        "id": "pplx-123",
        "model": "sonar",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Transformers have revolutionised NLP...",
                },
                "finish_reason": "stop",
            }
        ],
        "citations": [
            "https://arxiv.org/abs/1706.03762",
            "https://arxiv.org/abs/1810.04805",
        ],
        "search_results": [
            {
                "title": "Attention Is All You Need",
                "url": "https://arxiv.org/abs/1706.03762",
                "snippet": "We propose a new architecture...",
                "date": "2017-06-12",
            }
        ],
    }


@pytest.fixture
def sample_google_search_response():
    """Sample Google Custom Search response."""
    return {
        "items": [
            {
                "title": "Attention Is All You Need - arXiv",
                "link": "https://arxiv.org/abs/1706.03762",
                "snippet": "We propose a new simple network architecture...",
                "displayLink": "arxiv.org",
                "formattedUrl": "https://arxiv.org/abs/1706.03762",
            },
            {
                "title": "BERT - Google AI",
                "link": "https://ai.google/research/pubs/pub46201",
                "snippet": "Pre-training of Deep Bidirectional Transformers...",
                "displayLink": "ai.google",
                "formattedUrl": "https://ai.google/research/pubs/pub46201",
            },
        ]
    }


@pytest.fixture
def sample_crossref_search_response():
    """Sample CrossRef /works search response."""
    return {
        "status": "ok",
        "message": {
            "total-results": 1,
            "items": [
                {
                    "DOI": "10.1038/nature12373",
                    "title": ["Deep learning for genomics"],
                    "author": [
                        {"given": "John", "family": "Smith"},
                        {"given": "Jane", "family": "Doe"},
                    ],
                    "issued": {"date-parts": [[2013]]},
                    "URL": "https://doi.org/10.1038/nature12373",
                    "type": "journal-article",
                    "publisher": "Nature Publishing Group",
                    "container-title": ["Nature"],
                    "is-referenced-by-count": 150,
                    "abstract": "A comprehensive review of deep learning...",
                }
            ],
        },
    }


@pytest.fixture
def sample_crossref_work_response():
    """Sample CrossRef /works/{doi} response."""
    return {
        "status": "ok",
        "message": {
            "DOI": "10.1038/nature12373",
            "title": ["Deep learning for genomics"],
            "author": [
                {"given": "John", "family": "Smith"},
                {"given": "Jane", "family": "Doe"},
            ],
            "issued": {"date-parts": [[2013]]},
            "URL": "https://doi.org/10.1038/nature12373",
            "type": "journal-article",
            "publisher": "Nature Publishing Group",
            "container-title": ["Nature"],
            "is-referenced-by-count": 150,
            "abstract": "A comprehensive review of deep learning...",
        },
    }
