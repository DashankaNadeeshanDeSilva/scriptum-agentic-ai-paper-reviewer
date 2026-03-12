"""Semantic Scholar Graph API research tool.

Uses httpx to query the Semantic Scholar Academic Graph API v1 for
paper search, citation retrieval, and reference lookup.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from scriptum_ai.backend.core.config import get_settings
from scriptum_ai.tools.research.base import (
    CitationGraph,
    Paper,
    ResearchTool,
    SearchResult,
    http_request_with_retry,
)

_BASE_URL = "https://api.semanticscholar.org/graph/v1"
_SEARCH_FIELDS = "title,authors,abstract,year,venue,externalIds,citationCount,url"
_PAPER_FIELDS = "title,authors,abstract,year,venue,externalIds,citationCount,url,publicationDate"
_CITATION_FIELDS = "title,authors,year,venue,externalIds,citationCount,url"


class SemanticScholarTool(ResearchTool):
    """Search Semantic Scholar for papers, citations, and references."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key: str = settings.apis.semantic_scholar.api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init httpx client with optional API key header."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {}
            if self._api_key:
                headers["x-api-key"] = self._api_key
            self._client = httpx.AsyncClient(
                base_url=_BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    @property
    def name(self) -> str:
        return "semantic_scholar"

    @property
    def description(self) -> str:
        return "Search Semantic Scholar for papers and citation data"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Search papers by query string.

        ``GET /paper/search?query={query}&limit={limit}&fields={fields}``
        """
        if not query.strip():
            return []

        try:
            client = await self._get_client()
            resp = await http_request_with_retry(
                client,
                "GET",
                "/paper/search",
                params={
                    "query": query,
                    "limit": min(max_results, 100),
                    "fields": _SEARCH_FIELDS,
                },
            )
            data = resp.json()
            papers = data.get("data", [])
            return [self._to_search_result(p) for p in papers]

        except Exception as exc:
            logger.error("Semantic Scholar search failed: {}", exc)
            return []

    async def get_paper(self, paper_id: str) -> Paper | None:
        """Get paper by Semantic Scholar ID, DOI, or arXiv ID.

        ``GET /paper/{paper_id}?fields={fields}``

        Use prefixes for non-S2 IDs: ``DOI:10.xxx``, ``ARXIV:2301.xxx``.
        """
        try:
            client = await self._get_client()
            resp = await http_request_with_retry(
                client,
                "GET",
                f"/paper/{paper_id}",
                params={"fields": _PAPER_FIELDS},
            )
            if resp.status_code == 404:
                return None
            return self._to_paper(resp.json())

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("Semantic Scholar get_paper({}) failed: {}", paper_id, exc)
            return None
        except Exception as exc:
            logger.error("Semantic Scholar get_paper({}) failed: {}", paper_id, exc)
            return None

    async def get_citations(self, paper_id: str, *, limit: int = 50) -> CitationGraph:
        """Get papers that cite this paper.

        ``GET /paper/{paper_id}/citations?fields={fields}&limit={limit}``
        """
        graph = CitationGraph(paper_id=paper_id)
        try:
            client = await self._get_client()
            resp = await http_request_with_retry(
                client,
                "GET",
                f"/paper/{paper_id}/citations",
                params={"fields": _CITATION_FIELDS, "limit": min(limit, 1000)},
            )
            data = resp.json()
            for item in data.get("data", []):
                citing = item.get("citingPaper", {})
                if citing:
                    graph.citations.append(self._to_paper(citing))

        except Exception as exc:
            logger.error("Semantic Scholar get_citations({}) failed: {}", paper_id, exc)
        return graph

    async def get_references(self, paper_id: str, *, limit: int = 50) -> CitationGraph:
        """Get papers that this paper references.

        ``GET /paper/{paper_id}/references?fields={fields}&limit={limit}``
        """
        graph = CitationGraph(paper_id=paper_id)
        try:
            client = await self._get_client()
            resp = await http_request_with_retry(
                client,
                "GET",
                f"/paper/{paper_id}/references",
                params={"fields": _CITATION_FIELDS, "limit": min(limit, 1000)},
            )
            data = resp.json()
            for item in data.get("data", []):
                cited = item.get("citedPaper", {})
                if cited:
                    graph.references.append(self._to_paper(cited))

        except Exception as exc:
            logger.error("Semantic Scholar get_references({}) failed: {}", paper_id, exc)
        return graph

    async def close(self) -> None:
        """Close the underlying httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_search_result(data: dict[str, Any]) -> SearchResult:
        ext_ids = data.get("externalIds") or {}
        authors = data.get("authors") or []
        return SearchResult(
            title=data.get("title", ""),
            url=data.get("url", ""),
            snippet=(data.get("abstract") or "")[:500],
            source="semantic_scholar",
            metadata={
                "paper_id": data.get("paperId", ""),
                "authors": [a.get("name", "") for a in authors],
                "year": data.get("year"),
                "venue": data.get("venue", ""),
                "citation_count": data.get("citationCount"),
                "doi": ext_ids.get("DOI", ""),
                "arxiv_id": ext_ids.get("ArXiv", ""),
            },
        )

    @staticmethod
    def _to_paper(data: dict[str, Any]) -> Paper:
        ext_ids = data.get("externalIds") or {}
        authors = data.get("authors") or []
        return Paper(
            title=data.get("title", ""),
            authors=[a.get("name", "") for a in authors],
            abstract=(data.get("abstract") or "")[:1000],
            year=data.get("year"),
            venue=data.get("venue", ""),
            doi=ext_ids.get("DOI", ""),
            arxiv_id=ext_ids.get("ArXiv", ""),
            url=data.get("url", ""),
            citation_count=data.get("citationCount"),
            source="semantic_scholar",
        )
