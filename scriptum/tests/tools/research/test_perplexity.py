"""Tests for the Perplexity research tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tools.research.perplexity import PerplexityTool


@pytest.fixture
def tool(mock_settings: MagicMock):
    with patch("tools.research.perplexity.get_settings", return_value=mock_settings):
        return PerplexityTool()


@pytest.fixture
def tool_no_key(mock_settings_no_keys: MagicMock):
    with patch("tools.research.perplexity.get_settings", return_value=mock_settings_no_keys):
        return PerplexityTool()


class TestPerplexitySearch:
    @pytest.mark.asyncio
    async def test_search_with_search_results(
        self, tool: PerplexityTool, sample_perplexity_response: dict
    ) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_perplexity_response
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.perplexity.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("What are transformers in NLP?")

        assert len(results) >= 1
        assert results[0].title == "Attention Is All You Need"
        assert results[0].source == "perplexity"
        assert "arxiv.org" in results[0].url

    @pytest.mark.asyncio
    async def test_search_with_citations_only(self, tool: PerplexityTool) -> None:
        response_data = {
            "choices": [{"message": {"content": "Transformers are..."}, "finish_reason": "stop"}],
            "citations": [
                "https://arxiv.org/abs/1706.03762",
                "https://arxiv.org/abs/1810.04805",
            ],
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = response_data
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.perplexity.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("transformers")

        assert len(results) == 2
        assert results[0].url == "https://arxiv.org/abs/1706.03762"
        assert results[0].snippet  # First citation gets the answer snippet

    @pytest.mark.asyncio
    async def test_search_answer_only_fallback(self, tool: PerplexityTool) -> None:
        response_data = {
            "model": "sonar",
            "choices": [{"message": {"content": "A plain answer without citations"}}],
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = response_data
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.perplexity.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("simple question")

        assert len(results) == 1
        assert results[0].title == "Perplexity Answer"
        assert "plain answer" in results[0].snippet

    @pytest.mark.asyncio
    async def test_search_no_api_key(self, tool_no_key: PerplexityTool) -> None:
        results = await tool_no_key.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_query(self, tool: PerplexityTool) -> None:
        results = await tool.search("")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_exception(self, tool: PerplexityTool) -> None:
        with patch(
            "tools.research.perplexity.http_request_with_retry",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            results = await tool.search("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_max_results_limits_output(
        self, tool: PerplexityTool, sample_perplexity_response: dict
    ) -> None:
        # Add more search results to the response
        sample_perplexity_response["search_results"] = [
            {"title": f"Result {i}", "url": f"https://example.com/{i}", "snippet": f"snippet {i}"}
            for i in range(10)
        ]
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_perplexity_response
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.perplexity.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("test", max_results=3)

        assert len(results) == 3
