"""Tests for the arXiv research tool."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from tools.research.arxiv import ArxivTool


def _make_arxiv_result(
    title: str = "Test Paper",
    summary: str = "A test abstract",
    entry_id: str = "http://arxiv.org/abs/2301.12345v1",
    pdf_url: str = "http://arxiv.org/pdf/2301.12345v1",
    categories: list[str] | None = None,
    primary_category: str = "cs.AI",
):
    """Create a mock arxiv.Result object."""
    result = MagicMock()
    result.title = title
    result.summary = summary
    result.entry_id = entry_id
    result.pdf_url = pdf_url
    result.categories = categories or ["cs.AI", "cs.CL"]
    result.primary_category = primary_category
    result.published = datetime(2023, 1, 15, tzinfo=UTC)
    result.updated = datetime(2023, 2, 1, tzinfo=UTC)
    result.authors = [MagicMock(name="Alice Smith"), MagicMock(name="Bob Jones")]
    # MagicMock.name is special — override it properly
    result.authors[0].name = "Alice Smith"
    result.authors[1].name = "Bob Jones"
    return result


class TestArxivToolSearch:
    @pytest.mark.asyncio
    @patch("tools.research.arxiv.arxiv")
    async def test_search_returns_results(self, mock_arxiv_mod: MagicMock) -> None:
        mock_client = MagicMock()
        mock_arxiv_mod.Client.return_value = mock_client
        mock_arxiv_mod.Search.return_value = MagicMock()
        mock_arxiv_mod.SortCriterion.Relevance = "relevance"
        mock_client.results.return_value = [
            _make_arxiv_result("Paper A"),
            _make_arxiv_result("Paper B", entry_id="http://arxiv.org/abs/2302.99999v1"),
        ]

        tool = ArxivTool()
        results = await tool.search("transformers")

        assert len(results) == 2
        assert results[0].title == "Paper A"
        assert results[0].source == "arxiv"
        assert results[0].metadata["arxiv_id"] == "2301.12345v1"
        assert "Alice Smith" in results[0].metadata["authors"]

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(self) -> None:
        tool = ArxivTool()
        results = await tool.search("")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_whitespace_query_returns_empty(self) -> None:
        tool = ArxivTool()
        results = await tool.search("   ")
        assert results == []

    @pytest.mark.asyncio
    @patch("tools.research.arxiv.arxiv")
    async def test_search_caps_max_results(self, mock_arxiv_mod: MagicMock) -> None:
        mock_client = MagicMock()
        mock_arxiv_mod.Client.return_value = mock_client
        mock_arxiv_mod.Search.return_value = MagicMock()
        mock_arxiv_mod.SortCriterion.Relevance = "relevance"
        mock_client.results.return_value = []

        tool = ArxivTool()
        await tool.search("test", max_results=200)

        # Verify Search was called with capped max_results
        call_kwargs = mock_arxiv_mod.Search.call_args
        assert call_kwargs.kwargs.get("max_results", call_kwargs[1].get("max_results")) <= 100

    @pytest.mark.asyncio
    @patch("tools.research.arxiv.arxiv")
    async def test_search_handles_exception(self, mock_arxiv_mod: MagicMock) -> None:
        mock_arxiv_mod.Client.side_effect = Exception("Network error")

        tool = ArxivTool()
        results = await tool.search("test")
        assert results == []

    @pytest.mark.asyncio
    @patch("tools.research.arxiv.arxiv")
    async def test_search_sort_by_submitted(self, mock_arxiv_mod: MagicMock) -> None:
        mock_client = MagicMock()
        mock_arxiv_mod.Client.return_value = mock_client
        mock_arxiv_mod.Search.return_value = MagicMock()
        mock_arxiv_mod.SortCriterion.SubmittedDate = "submitted"
        mock_client.results.return_value = []

        tool = ArxivTool()
        await tool.search("test", sort_by="submitted")

        call_kwargs = mock_arxiv_mod.Search.call_args
        assert call_kwargs.kwargs.get("sort_by", call_kwargs[1].get("sort_by")) == "submitted"


class TestArxivToolGetPaper:
    @pytest.mark.asyncio
    @patch("tools.research.arxiv.arxiv")
    async def test_get_paper_found(self, mock_arxiv_mod: MagicMock) -> None:
        mock_client = MagicMock()
        mock_arxiv_mod.Client.return_value = mock_client
        mock_arxiv_mod.Search.return_value = MagicMock()
        mock_client.results.return_value = [_make_arxiv_result()]

        tool = ArxivTool()
        paper = await tool.get_paper("2301.12345")

        assert paper is not None
        assert paper.title == "Test Paper"
        assert paper.venue == "arXiv"
        assert paper.year == 2023
        assert paper.source == "arxiv"

    @pytest.mark.asyncio
    @patch("tools.research.arxiv.arxiv")
    async def test_get_paper_not_found(self, mock_arxiv_mod: MagicMock) -> None:
        mock_client = MagicMock()
        mock_arxiv_mod.Client.return_value = mock_client
        mock_arxiv_mod.Search.return_value = MagicMock()
        mock_client.results.return_value = []

        tool = ArxivTool()
        paper = await tool.get_paper("9999.99999")
        assert paper is None

    @pytest.mark.asyncio
    @patch("tools.research.arxiv.arxiv")
    async def test_get_paper_handles_exception(self, mock_arxiv_mod: MagicMock) -> None:
        mock_arxiv_mod.Client.side_effect = Exception("API error")

        tool = ArxivTool()
        paper = await tool.get_paper("2301.12345")
        assert paper is None
