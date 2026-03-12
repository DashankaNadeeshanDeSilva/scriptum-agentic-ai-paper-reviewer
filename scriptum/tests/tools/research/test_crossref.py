"""Tests for the CrossRef research tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from scriptum_ai.tools.research.crossref import CrossRefTool


class TestCrossRefSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, sample_crossref_search_response: dict) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_crossref_search_response
        mock_resp.raise_for_status = MagicMock()

        tool = CrossRefTool()
        with patch(
            "scriptum_ai.tools.research.crossref.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("deep learning genomics")

        assert len(results) == 1
        assert results[0].title == "Deep learning for genomics"
        assert results[0].source == "crossref"
        assert results[0].metadata["doi"] == "10.1038/nature12373"
        assert results[0].metadata["year"] == 2013
        assert "John Smith" in results[0].metadata["authors"]
        assert results[0].metadata["container_title"] == "Nature"

    @pytest.mark.asyncio
    async def test_search_empty_query(self) -> None:
        tool = CrossRefTool()
        results = await tool.search("")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_handles_exception(self) -> None:
        tool = CrossRefTool()
        with patch(
            "scriptum_ai.tools.research.crossref.http_request_with_retry",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Network error"),
        ):
            results = await tool.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_response(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok", "message": {"items": []}}
        mock_resp.raise_for_status = MagicMock()

        tool = CrossRefTool()
        with patch(
            "scriptum_ai.tools.research.crossref.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            results = await tool.search("nonexistent paper")
        assert results == []


class TestCrossRefVerifyDoi:
    @pytest.mark.asyncio
    async def test_verify_doi_found(self, sample_crossref_work_response: dict) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_crossref_work_response
        mock_resp.raise_for_status = MagicMock()

        tool = CrossRefTool()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            paper = await tool.verify_doi("10.1038/nature12373")

        assert paper is not None
        assert paper.title == "Deep learning for genomics"
        assert paper.doi == "10.1038/nature12373"
        assert paper.year == 2013
        assert paper.venue == "Nature"
        assert "John Smith" in paper.authors
        assert paper.source == "crossref"

    @pytest.mark.asyncio
    async def test_verify_doi_not_found(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 404

        tool = CrossRefTool()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            paper = await tool.verify_doi("10.9999/nonexistent")
        assert paper is None

    @pytest.mark.asyncio
    async def test_verify_doi_empty_input(self) -> None:
        tool = CrossRefTool()
        paper = await tool.verify_doi("")
        assert paper is None

    @pytest.mark.asyncio
    async def test_verify_doi_handles_exception(self) -> None:
        tool = CrossRefTool()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_cls.return_value = mock_client

            paper = await tool.verify_doi("10.1038/nature12373")
        assert paper is None


class TestCrossRefSearchByTitle:
    @pytest.mark.asyncio
    async def test_search_by_title_found(
        self,
        sample_crossref_search_response: dict,
        sample_crossref_work_response: dict,
    ) -> None:
        search_resp = MagicMock(spec=httpx.Response)
        search_resp.status_code = 200
        search_resp.json.return_value = sample_crossref_search_response
        search_resp.raise_for_status = MagicMock()

        doi_resp = MagicMock(spec=httpx.Response)
        doi_resp.status_code = 200
        doi_resp.json.return_value = sample_crossref_work_response
        doi_resp.raise_for_status = MagicMock()

        tool = CrossRefTool()

        with patch(
            "scriptum_ai.tools.research.crossref.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=search_resp,
        ):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client.get = AsyncMock(return_value=doi_resp)
                mock_client_cls.return_value = mock_client

                paper = await tool.search_by_title("Deep learning for genomics")

        assert paper is not None
        assert paper.title == "Deep learning for genomics"

    @pytest.mark.asyncio
    async def test_search_by_title_no_results(self) -> None:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok", "message": {"items": []}}
        mock_resp.raise_for_status = MagicMock()

        tool = CrossRefTool()
        with patch(
            "scriptum_ai.tools.research.crossref.http_request_with_retry",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            paper = await tool.search_by_title("Nonexistent Paper Title")
        assert paper is None


class TestCrossRefToolInterface:
    def test_name(self) -> None:
        tool = CrossRefTool()
        assert tool.name == "crossref"

    def test_description(self) -> None:
        tool = CrossRefTool()
        assert "CrossRef" in tool.description
