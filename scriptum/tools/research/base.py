"""Base classes and shared data models for research tools.

All SCRIPTUM research tools inherit from :class:`ResearchTool`, which
extends :class:`ToolInterface` with a typed ``search()`` method.
"""

from __future__ import annotations

import asyncio
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

from agents.core.base import ToolInterface


# ---------------------------------------------------------------------------
# Data models (plain dataclasses — ephemeral internal objects)
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single search result from any research tool."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""  # "arxiv" | "semantic_scholar" | "perplexity" | "google" | "crossref"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Paper:
    """A paper found via research tools."""

    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    year: int | None = None
    venue: str = ""
    doi: str = ""
    arxiv_id: str = ""
    url: str = ""
    citation_count: int | None = None
    source: str = ""


@dataclass
class CitationGraph:
    """Citation relationships for a paper."""

    paper_id: str = ""
    citations: list[Paper] = field(default_factory=list)  # papers that cite this one
    references: list[Paper] = field(default_factory=list)  # papers this one cites


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class ResearchTool(ToolInterface):
    """Abstract base for research tools.

    Extends :class:`ToolInterface` with a typed ``search()`` method.
    Concrete tools must implement ``search()``, ``name``, and ``description``.
    The ``execute()`` method delegates to ``search()`` so agents can call
    tools uniformly via the ``ToolInterface`` contract.
    """

    @abstractmethod
    async def search(self, query: str, **kwargs: Any) -> list[SearchResult]:
        """Search for relevant papers or information."""
        ...

    async def execute(self, **kwargs: Any) -> Any:
        """ToolInterface.execute() — delegates to search()."""
        query = kwargs.pop("query", "")
        return await self.search(query, **kwargs)


# ---------------------------------------------------------------------------
# Shared HTTP helper with retry for rate limits
# ---------------------------------------------------------------------------


async def http_request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    retry_base_delay: float = 1.0,
    **kwargs: Any,
) -> httpx.Response:
    """Execute an HTTP request with retry on 429 and 5xx errors.

    Args:
        client: An httpx.AsyncClient instance.
        method: HTTP method (``"GET"`` or ``"POST"``).
        url: Request URL.
        max_retries: Number of retry attempts.
        retry_base_delay: Base delay in seconds for exponential backoff.
        **kwargs: Passed through to ``client.request()``.

    Returns:
        The successful ``httpx.Response``.

    Raises:
        httpx.HTTPStatusError: After exhausting retries on 4xx/5xx.
        httpx.TimeoutException: On timeout.
        httpx.ConnectError: On connection failure.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = await client.request(method, url, **kwargs)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", "0")) or retry_base_delay * (2**attempt)
                logger.warning(
                    "Rate limited (429) on {} {}, retry in {:.1f}s (attempt {}/{})",
                    method, url, retry_after, attempt + 1, max_retries,
                )
                await asyncio.sleep(retry_after)
                continue

            if resp.status_code >= 500 and attempt < max_retries - 1:
                delay = retry_base_delay * (2**attempt)
                logger.warning(
                    "Server error ({}) on {} {}, retry in {:.1f}s",
                    resp.status_code, method, url, delay,
                )
                await asyncio.sleep(delay)
                continue

            resp.raise_for_status()
            return resp

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                delay = retry_base_delay * (2**attempt)
                logger.warning(
                    "{} on {} {}, retry in {:.1f}s",
                    type(exc).__name__, method, url, delay,
                )
                await asyncio.sleep(delay)
            else:
                raise

    # Should not normally reach here, but handle edge case
    if last_exc:
        raise last_exc
    raise httpx.HTTPStatusError(
        "Max retries exceeded", request=httpx.Request(method, url), response=resp  # type: ignore[possibly-undefined]
    )
