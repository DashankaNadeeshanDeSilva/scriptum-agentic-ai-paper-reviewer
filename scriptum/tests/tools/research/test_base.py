"""Tests for research tool base classes and shared utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from scriptum_ai.tools.research.base import (
    CitationGraph,
    Paper,
    SearchResult,
    http_request_with_retry,
)


class TestSearchResult:
    def test_defaults(self) -> None:
        r = SearchResult()
        assert r.title == ""
        assert r.source == ""
        assert r.metadata == {}

    def test_creation(self) -> None:
        r = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="A snippet",
            source="arxiv",
            metadata={"arxiv_id": "2301.12345"},
        )
        assert r.title == "Test"
        assert r.metadata["arxiv_id"] == "2301.12345"


class TestPaper:
    def test_defaults(self) -> None:
        p = Paper()
        assert p.title == ""
        assert p.authors == []
        assert p.year is None

    def test_creation(self) -> None:
        p = Paper(
            title="Attention Is All You Need",
            authors=["Vaswani et al."],
            year=2017,
            venue="NeurIPS",
            doi="10.5555/3295222.3295349",
            citation_count=50000,
            source="semantic_scholar",
        )
        assert p.year == 2017
        assert p.citation_count == 50000


class TestCitationGraph:
    def test_defaults(self) -> None:
        g = CitationGraph()
        assert g.paper_id == ""
        assert g.citations == []
        assert g.references == []


class TestHttpRequestWithRetry:
    @pytest.mark.asyncio
    async def test_successful_request(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(return_value=mock_resp)

        resp = await http_request_with_retry(client, "GET", "https://api.example.com/test")
        assert resp.status_code == 200
        client.request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_on_429(self) -> None:
        rate_limited = MagicMock(spec=httpx.Response)
        rate_limited.status_code = 429
        rate_limited.headers = {"Retry-After": "0.01"}

        success = MagicMock(spec=httpx.Response)
        success.status_code = 200
        success.raise_for_status = MagicMock()

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(side_effect=[rate_limited, success])

        resp = await http_request_with_retry(
            client,
            "GET",
            "https://api.example.com/test",
            max_retries=3,
            retry_base_delay=0.01,
        )
        assert resp.status_code == 200
        assert client.request.await_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_500(self) -> None:
        server_error = MagicMock(spec=httpx.Response)
        server_error.status_code = 500

        success = MagicMock(spec=httpx.Response)
        success.status_code = 200
        success.raise_for_status = MagicMock()

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(side_effect=[server_error, success])

        resp = await http_request_with_retry(
            client,
            "GET",
            "https://api.example.com/test",
            max_retries=3,
            retry_base_delay=0.01,
        )
        assert resp.status_code == 200
        assert client.request.await_count == 2

    @pytest.mark.asyncio
    async def test_raises_on_4xx(self) -> None:
        bad_request = MagicMock(spec=httpx.Response)
        bad_request.status_code = 400
        bad_request.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "400 Bad Request",
                request=MagicMock(),
                response=bad_request,
            )
        )

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(return_value=bad_request)

        with pytest.raises(httpx.HTTPStatusError):
            await http_request_with_retry(
                client,
                "GET",
                "https://api.example.com/test",
                max_retries=3,
                retry_base_delay=0.01,
            )
        # No retry on 4xx (except 429)
        assert client.request.await_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        success = MagicMock(spec=httpx.Response)
        success.status_code = 200
        success.raise_for_status = MagicMock()

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(side_effect=[httpx.TimeoutException("timeout"), success])

        resp = await http_request_with_retry(
            client,
            "GET",
            "https://api.example.com/test",
            max_retries=3,
            retry_base_delay=0.01,
        )
        assert resp.status_code == 200
        assert client.request.await_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(httpx.ConnectError):
            await http_request_with_retry(
                client,
                "GET",
                "https://api.example.com/test",
                max_retries=2,
                retry_base_delay=0.01,
            )
        assert client.request.await_count == 2
