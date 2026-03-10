"""Tests for the Semantic Scholar research tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tools.research.semantic_scholar import SemanticScholarTool


@pytest.fixture
def tool(mock_settings: MagicMock):
    """Create a SemanticScholarTool with mocked settings."""
    with patch("tools.research.semantic_scholar.get_settings", return_value=mock_settings):
        return SemanticScholarTool()


class TestSemanticScholarSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(
        self, tool: SemanticScholarTool, sample_s2_search_response: dict
    ) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_s2_search_response
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.semantic_scholar.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("transformers")

        assert len(results) == 2
        assert results[0].title == "Attention Is All You Need"
        assert results[0].source == "semantic_scholar"
        assert results[0].metadata["paper_id"] == "abc123"
        assert results[0].metadata["doi"] == "10.5555/3295222.3295349"
        assert "Ashish Vaswani" in results[0].metadata["authors"]

    @pytest.mark.asyncio
    async def test_search_empty_query(self, tool: SemanticScholarTool) -> None:
        results = await tool.search("")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_exception(self, tool: SemanticScholarTool) -> None:
        with patch(
            "tools.research.semantic_scholar.http_request_with_retry",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection failed"),
        ):
            results = await tool.search("test query")
        assert results == []


class TestSemanticScholarGetPaper:
    @pytest.mark.asyncio
    async def test_get_paper_found(self, tool: SemanticScholarTool) -> None:
        paper_data = {
            "paperId": "abc123",
            "title": "Test Paper",
            "abstract": "Abstract text",
            "year": 2023,
            "venue": "NeurIPS",
            "citationCount": 100,
            "url": "https://semanticscholar.org/paper/abc123",
            "authors": [{"name": "Author A"}],
            "externalIds": {"DOI": "10.1234/test", "ArXiv": "2301.00001"},
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = paper_data
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.semantic_scholar.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            paper = await tool.get_paper("abc123")

        assert paper is not None
        assert paper.title == "Test Paper"
        assert paper.doi == "10.1234/test"
        assert paper.arxiv_id == "2301.00001"

    @pytest.mark.asyncio
    async def test_get_paper_not_found(self, tool: SemanticScholarTool) -> None:
        with patch(
            "tools.research.semantic_scholar.http_request_with_retry",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError(
                "404",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            ),
        ):
            paper = await tool.get_paper("nonexistent")
        assert paper is None


class TestSemanticScholarCitations:
    @pytest.mark.asyncio
    async def test_get_citations(
        self, tool: SemanticScholarTool, sample_s2_citations_response: dict
    ) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_s2_citations_response
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.semantic_scholar.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            graph = await tool.get_citations("abc123")

        assert graph.paper_id == "abc123"
        assert len(graph.citations) == 1
        assert graph.citations[0].title == "GPT-2"

    @pytest.mark.asyncio
    async def test_get_references(self, tool: SemanticScholarTool) -> None:
        ref_response = {
            "data": [
                {
                    "citedPaper": {
                        "paperId": "ref1",
                        "title": "Seq2Seq",
                        "year": 2014,
                        "venue": "NeurIPS",
                        "citationCount": 20000,
                        "url": "",
                        "authors": [{"name": "Ilya Sutskever"}],
                        "externalIds": {},
                    }
                }
            ]
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = ref_response
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.semantic_scholar.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            graph = await tool.get_references("abc123")

        assert len(graph.references) == 1
        assert graph.references[0].title == "Seq2Seq"

    @pytest.mark.asyncio
    async def test_get_citations_handles_error(self, tool: SemanticScholarTool) -> None:
        with patch(
            "tools.research.semantic_scholar.http_request_with_retry",
            new_callable=AsyncMock,
            side_effect=Exception("Server error"),
        ):
            graph = await tool.get_citations("abc123")
        assert graph.paper_id == "abc123"
        assert graph.citations == []


class TestSemanticScholarClose:
    @pytest.mark.asyncio
    async def test_close_client(self, tool: SemanticScholarTool) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.is_closed = False
        tool._client = mock_client
        await tool.close()
        mock_client.aclose.assert_awaited_once()
        assert tool._client is None
