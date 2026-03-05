"""arXiv API research tool.

Uses the ``arxiv`` Python package to search the arXiv preprint repository.
The library is synchronous, so searches are wrapped in
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

import arxiv
from loguru import logger

from tools.research.base import Paper, ResearchTool, SearchResult


class ArxivTool(ResearchTool):
    """Search arXiv for academic papers."""

    @property
    def name(self) -> str:
        return "arxiv"

    @property
    def description(self) -> str:
        return "Search the arXiv preprint repository for academic papers"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        sort_by: str = "relevance",
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Search arXiv by query string.

        Args:
            query: Search query (supports arXiv search syntax).
            max_results: Maximum number of results (default 10, max 100).
            sort_by: Sort order — ``"relevance"`` or ``"submitted"``.

        Returns:
            List of :class:`SearchResult` objects.
        """
        if not query.strip():
            return []

        max_results = min(max_results, 100)
        try:
            return await asyncio.to_thread(
                self._sync_search, query, max_results, sort_by
            )
        except Exception as exc:
            logger.error("arXiv search failed: {}", exc)
            return []

    def _sync_search(
        self, query: str, max_results: int, sort_by: str
    ) -> list[SearchResult]:
        """Synchronous search using the arxiv package."""
        sort_criterion = (
            arxiv.SortCriterion.SubmittedDate
            if sort_by == "submitted"
            else arxiv.SortCriterion.Relevance
        )
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_criterion,
        )

        results: list[SearchResult] = []
        for paper in client.results(search):
            arxiv_id = paper.entry_id.split("/abs/")[-1] if "/abs/" in paper.entry_id else paper.entry_id.split("/")[-1]
            results.append(
                SearchResult(
                    title=paper.title,
                    url=paper.entry_id,
                    snippet=paper.summary[:500] if paper.summary else "",
                    source="arxiv",
                    metadata={
                        "arxiv_id": arxiv_id,
                        "authors": [a.name for a in paper.authors],
                        "published": paper.published.isoformat() if paper.published else "",
                        "updated": paper.updated.isoformat() if paper.updated else "",
                        "pdf_url": paper.pdf_url or "",
                        "categories": list(paper.categories) if paper.categories else [],
                        "primary_category": paper.primary_category or "",
                    },
                )
            )
        return results

    async def get_paper(self, arxiv_id: str) -> Paper | None:
        """Fetch a specific paper by its arXiv ID.

        Args:
            arxiv_id: arXiv identifier (e.g. ``"2301.12345"``).

        Returns:
            A :class:`Paper` object, or ``None`` if not found.
        """
        try:
            return await asyncio.to_thread(self._sync_get_paper, arxiv_id)
        except Exception as exc:
            logger.error("arXiv get_paper({}) failed: {}", arxiv_id, exc)
            return None

    def _sync_get_paper(self, arxiv_id: str) -> Paper | None:
        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(client.results(search))
        if not results:
            return None

        p = results[0]
        return Paper(
            title=p.title,
            authors=[a.name for a in p.authors],
            abstract=p.summary or "",
            year=p.published.year if p.published else None,
            venue="arXiv",
            arxiv_id=arxiv_id,
            url=p.entry_id,
            source="arxiv",
        )
