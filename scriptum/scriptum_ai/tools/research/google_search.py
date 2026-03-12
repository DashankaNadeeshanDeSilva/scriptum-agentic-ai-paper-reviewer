"""Google Custom Search API research tool (direct HTTP, not MCP).

Uses httpx to query the Google Custom Search JSON API for web search
results. Requires an API key and a Custom Search Engine ID (CX).
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from scriptum_ai.backend.core.config import get_settings
from scriptum_ai.tools.research.base import ResearchTool, SearchResult, http_request_with_retry

_BASE_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchTool(ResearchTool):
    """Web search via Google Custom Search API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key: str = settings.mcp.google_search.api_key
        self._cx: str = settings.mcp.google_search.cx

    @property
    def name(self) -> str:
        return "google_search"

    @property
    def description(self) -> str:
        return "Web search via Google Custom Search API"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Search the web using Google Custom Search.

        ``GET /customsearch/v1?key={key}&cx={cx}&q={query}&num={num}``

        Args:
            query: Search query string.
            max_results: Number of results (1–10 per Google API limit).

        Returns:
            List of :class:`SearchResult` objects.
        """
        if not self._api_key or not self._cx:
            logger.warning("Google Search API key or CX not configured, skipping search")
            return []

        if not query.strip():
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await http_request_with_retry(
                    client,
                    "GET",
                    _BASE_URL,
                    params={
                        "key": self._api_key,
                        "cx": self._cx,
                        "q": query,
                        "num": min(max_results, 10),
                    },
                )
                data = resp.json()
                return [
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="google",
                        metadata={
                            "display_link": item.get("displayLink", ""),
                            "formatted_url": item.get("formattedUrl", ""),
                        },
                    )
                    for item in data.get("items", [])
                ]

        except Exception as exc:
            logger.error("Google Search failed: {}", exc)
            return []
