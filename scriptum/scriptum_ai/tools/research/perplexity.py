"""Perplexity API research tool (direct HTTP, not MCP).

Uses httpx to query the Perplexity chat completions API for
AI-powered academic search with inline citations.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from scriptum_ai.backend.core.config import get_settings
from scriptum_ai.tools.research.base import ResearchTool, SearchResult, http_request_with_retry

_BASE_URL = "https://api.perplexity.ai"


class PerplexityTool(ResearchTool):
    """AI-powered academic search with citations via Perplexity."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key: str = settings.mcp.perplexity.api_key

    @property
    def name(self) -> str:
        return "perplexity"

    @property
    def description(self) -> str:
        return "AI-powered academic search with citations via Perplexity"

    async def search(
        self,
        query: str,
        *,
        focus: str = "academic",
        model: str = "sonar",
        max_results: int = 5,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Send an academic query to Perplexity and extract citations.

        ``POST /chat/completions`` with the ``sonar`` model. The response
        includes ``citations`` (URLs) and ``search_results`` (title+snippet).

        Args:
            query: The search query, phrased as a question for best results.
            focus: Search focus hint included in the system prompt.
            model: Perplexity model name (``"sonar"`` or ``"sonar-pro"``).
            max_results: Not directly supported by API; limits returned results.

        Returns:
            List of :class:`SearchResult` objects from citations.
        """
        if not self._api_key:
            logger.warning("Perplexity API key not configured, skipping search")
            return []

        if not query.strip():
            return []

        system_msg = (
            f"You are an {focus} research assistant. Provide factual answers "
            "with specific citations to academic papers and sources."
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await http_request_with_retry(
                    client,
                    "POST",
                    f"{_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": query},
                        ],
                    },
                )
                data = resp.json()
                return self._parse_response(data, max_results)

        except Exception as exc:
            logger.error("Perplexity search failed: {}", exc)
            return []

    def _parse_response(self, data: dict[str, Any], max_results: int) -> list[SearchResult]:
        """Extract SearchResults from the Perplexity API response.

        The response may contain:
        - ``citations``: list of URLs cited in the answer
        - ``search_results``: list of {title, url, snippet} objects
        - ``choices[0].message.content``: the answer text
        """
        results: list[SearchResult] = []

        answer = ""
        choices = data.get("choices", [])
        if choices:
            answer = choices[0].get("message", {}).get("content", "")

        # Prefer structured search_results if available
        search_results = data.get("search_results", [])
        if search_results:
            for sr in search_results[:max_results]:
                results.append(
                    SearchResult(
                        title=sr.get("title", ""),
                        url=sr.get("url", ""),
                        snippet=sr.get("snippet", ""),
                        source="perplexity",
                        metadata={"date": sr.get("date", "")},
                    )
                )
            return results

        # Fall back to citations list (URLs only)
        citations = data.get("citations", [])
        if citations:
            for i, url in enumerate(citations[:max_results]):
                results.append(
                    SearchResult(
                        title=f"Citation {i + 1}",
                        url=url if isinstance(url, str) else "",
                        snippet=answer[:200] if i == 0 else "",
                        source="perplexity",
                    )
                )
            return results

        # No structured results — return the answer as a single result
        if answer:
            results.append(
                SearchResult(
                    title="Perplexity Answer",
                    url="",
                    snippet=answer[:500],
                    source="perplexity",
                    metadata={"model": data.get("model", "")},
                )
            )

        return results
