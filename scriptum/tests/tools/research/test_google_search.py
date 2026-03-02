"""Tests for the Google Custom Search research tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tools.research.google_search import GoogleSearchTool


@pytest.fixture
def tool(mock_settings: MagicMock):
    with patch("tools.research.google_search.get_settings", return_value=mock_settings):
        return GoogleSearchTool()


@pytest.fixture
def tool_no_key(mock_settings_no_keys: MagicMock):
    with patch("tools.research.google_search.get_settings", return_value=mock_settings_no_keys):
        return GoogleSearchTool()


class TestGoogleSearchSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(
        self, tool: GoogleSearchTool, sample_google_search_response: dict
    ) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_google_search_response
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.google_search.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("attention is all you need")

        assert len(results) == 2
        assert results[0].title == "Attention Is All You Need - arXiv"
        assert results[0].source == "google"
        assert "arxiv.org" in results[0].url
        assert results[0].metadata["display_link"] == "arxiv.org"

    @pytest.mark.asyncio
    async def test_search_no_api_key(self, tool_no_key: GoogleSearchTool) -> None:
        results = await tool_no_key.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_query(self, tool: GoogleSearchTool) -> None:
        results = await tool.search("")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_items(self, tool: GoogleSearchTool) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": []}
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.google_search.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("obscure query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_exception(self, tool: GoogleSearchTool) -> None:
        with patch(
            "tools.research.google_search.http_request_with_retry",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("Request timed out"),
        ):
            results = await tool.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_caps_at_10(self, tool: GoogleSearchTool) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": []}
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "tools.research.google_search.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ) as mock_req:
            await tool.search("test", max_results=50)

        # Verify num param is capped at 10
        call_kwargs = mock_req.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params["num"] == 10
