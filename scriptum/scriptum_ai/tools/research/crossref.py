"""CrossRef API research tool for DOI verification and metadata lookup.

Uses httpx to query the CrossRef REST API. No authentication required;
uses the "polite pool" (mailto parameter) for better rate limits.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from scriptum_ai.tools.research.base import (
    Paper,
    ResearchTool,
    SearchResult,
    http_request_with_retry,
)

_BASE_URL = "https://api.crossref.org"
_MAILTO = "scriptum-ai@users.noreply.github.com"


class CrossRefTool(ResearchTool):
    """Verify DOIs and search for paper metadata via CrossRef."""

    @property
    def name(self) -> str:
        return "crossref"

    @property
    def description(self) -> str:
        return "Verify DOIs and look up paper metadata via CrossRef"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Search CrossRef by title or query string.

        ``GET /works?query={query}&rows={rows}&mailto={mailto}``

        Args:
            query: Search query (title, author, keywords).
            max_results: Maximum number of results (default 5).

        Returns:
            List of :class:`SearchResult` objects.
        """
        if not query.strip():
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await http_request_with_retry(
                    client,
                    "GET",
                    f"{_BASE_URL}/works",
                    params={
                        "query": query,
                        "rows": min(max_results, 50),
                        "mailto": _MAILTO,
                    },
                )
                data = resp.json()
                items = data.get("message", {}).get("items", [])
                return [self._item_to_result(item) for item in items]

        except Exception as exc:
            logger.error("CrossRef search failed: {}", exc)
            return []

    async def verify_doi(self, doi: str) -> Paper | None:
        """Verify a DOI exists and return its metadata.

        ``GET /works/{doi}``

        Args:
            doi: A DOI string (e.g. ``"10.1038/nature12373"``).

        Returns:
            A :class:`Paper` object if found, ``None`` otherwise.
        """
        if not doi.strip():
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{_BASE_URL}/works/{doi}",
                    params={"mailto": _MAILTO},
                )
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                item = resp.json().get("message", {})
                return self._item_to_paper(item)

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("CrossRef verify_doi({}) failed: {}", doi, exc)
            return None
        except Exception as exc:
            logger.error("CrossRef verify_doi({}) failed: {}", doi, exc)
            return None

    async def search_by_title(self, title: str) -> Paper | None:
        """Find the best match for an exact title.

        Searches CrossRef and verifies the top result's DOI.

        Args:
            title: The paper title to look up.

        Returns:
            A :class:`Paper` if a match is found, ``None`` otherwise.
        """
        results = await self.search(title, max_results=1)
        if not results:
            return None

        doi = results[0].metadata.get("doi", "")
        if doi:
            return await self.verify_doi(doi)
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _item_to_result(item: dict[str, Any]) -> SearchResult:
        """Convert a CrossRef work item to a SearchResult."""
        titles = item.get("title", [])
        title = titles[0] if titles else ""

        authors = item.get("author", [])
        author_names = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors]

        year = None
        issued = item.get("issued", {})
        date_parts = issued.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

        return SearchResult(
            title=title,
            url=item.get("URL", ""),
            snippet=(item.get("abstract", "") or "")[:500],
            source="crossref",
            metadata={
                "doi": item.get("DOI", ""),
                "authors": author_names,
                "year": year,
                "type": item.get("type", ""),
                "publisher": item.get("publisher", ""),
                "citation_count": item.get("is-referenced-by-count"),
                "container_title": (item.get("container-title") or [""])[0],
            },
        )

    @staticmethod
    def _item_to_paper(item: dict[str, Any]) -> Paper:
        """Convert a CrossRef work item to a Paper."""
        titles = item.get("title", [])
        title = titles[0] if titles else ""

        authors = item.get("author", [])
        author_names = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors]

        year = None
        issued = item.get("issued", {})
        date_parts = issued.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

        venue = (item.get("container-title") or [""])[0]

        return Paper(
            title=title,
            authors=author_names,
            abstract=(item.get("abstract", "") or "")[:1000],
            year=year,
            venue=venue,
            doi=item.get("DOI", ""),
            url=item.get("URL", ""),
            citation_count=item.get("is-referenced-by-count"),
            source="crossref",
        )
