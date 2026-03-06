"""Reference resolver for structured bibliography extraction.

Two-phase enrichment of raw reference strings:

Phase A — LLM structuring
    Batch raw reference strings through an LLM with structured JSON output
    to populate ``Reference.title``, ``authors``, ``year``, ``venue``.

Phase B — API enrichment (optional)
    Query CrossRef to resolve DOIs for the structured references.
"""

from __future__ import annotations

import asyncio
import json

import httpx
from loguru import logger

from tools.document.models import Reference

# Maximum references to send in a single LLM batch (to stay within context limits)
_LLM_BATCH_SIZE = 15

# CrossRef polite-pool contact
_CROSSREF_BASE = "https://api.crossref.org"
_CROSSREF_MAILTO = "scriptum-ai@users.noreply.github.com"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def resolve_references(
    raw_refs: list[Reference],
    *,
    use_llm: bool = True,
    use_apis: bool = False,
) -> list[Reference]:
    """Enrich raw reference objects with structured metadata.

    Parameters
    ----------
    raw_refs:
        References with at minimum ``raw_text`` populated.
    use_llm:
        If ``True``, use LLM to parse raw text into structured fields.
    use_apis:
        If ``True``, query CrossRef to resolve DOIs.

    Returns
    -------
    list[Reference]
        The same references with structured fields populated
        and ``resolved=True`` for successfully enriched entries.
    """
    if not raw_refs:
        return raw_refs

    logger.info(
        "Resolving {} references (LLM={}, APIs={})",
        len(raw_refs),
        use_llm,
        use_apis,
    )

    refs = list(raw_refs)

    # Phase A: LLM structuring
    if use_llm:
        refs = await _llm_structure_references(refs)

    # Phase B: API enrichment (CrossRef DOI lookup)
    if use_apis:
        refs = await _api_enrich_references(refs)

    resolved_count = sum(1 for r in refs if r.resolved)
    logger.info("Reference resolution complete: {}/{} resolved", resolved_count, len(refs))

    return refs


# ---------------------------------------------------------------------------
# Phase A: LLM structuring
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """\
You are a bibliographic reference parser. Given a list of raw citation strings, \
extract structured metadata for each one. Return a JSON array where each element has:
- "title": the paper/book title (string)
- "authors": list of author names (list of strings)
- "year": publication year (string, e.g. "2023")
- "venue": journal name, conference name, or publisher (string)

If a field cannot be determined, use an empty string or empty list. \
Return ONLY the JSON array, no other text."""


async def _llm_structure_references(refs: list[Reference]) -> list[Reference]:
    """Use LLM to parse raw reference text into structured fields."""
    try:
        from backend.core.llm import LLMClient
    except Exception as exc:
        logger.warning("LLM not available for reference structuring: {}", exc)
        return refs

    # Split into batches
    batches: list[list[int]] = []
    for i in range(0, len(refs), _LLM_BATCH_SIZE):
        batches.append(list(range(i, min(i + _LLM_BATCH_SIZE, len(refs)))))

    client = LLMClient()

    for batch_indices in batches:
        batch_refs = [refs[i] for i in batch_indices]

        # Only process refs that have raw_text and aren't already resolved
        unresolved = [(idx, ref) for idx, ref in zip(batch_indices, batch_refs) if ref.raw_text and not ref.resolved]
        if not unresolved:
            continue

        # Build the user message with numbered references
        numbered = "\n".join(f"{i+1}. {ref.raw_text}" for i, (_, ref) in enumerate(unresolved))
        messages = [
            {"role": "system", "content": _LLM_SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse these {len(unresolved)} references:\n\n{numbered}"},
        ]

        try:
            response = await client.complete(messages, temperature=0.0, max_tokens=4096)
            parsed = json.loads(response.text)

            if not isinstance(parsed, list):
                logger.warning("LLM returned non-array for reference batch, skipping")
                continue

            # Map results back to the original references
            for (orig_idx, _), result in zip(unresolved, parsed):
                if not isinstance(result, dict):
                    continue
                ref = refs[orig_idx]
                ref.title = result.get("title", ref.title) or ref.title
                ref.authors = result.get("authors", ref.authors) or ref.authors
                ref.year = str(result.get("year", ref.year) or ref.year)
                ref.venue = result.get("venue", ref.venue) or ref.venue
                ref.resolved = True

        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON for reference batch, skipping")
        except Exception as exc:
            logger.warning("LLM reference structuring failed for batch: {}", exc)

    return refs


# ---------------------------------------------------------------------------
# Phase B: API enrichment (CrossRef DOI lookup)
# ---------------------------------------------------------------------------


async def _api_enrich_references(refs: list[Reference]) -> list[Reference]:
    """Query CrossRef to resolve DOIs for structured references."""
    # Only look up refs that have a title but no DOI yet
    candidates = [(i, ref) for i, ref in enumerate(refs) if ref.title and not ref.doi]
    if not candidates:
        return refs

    logger.debug("CrossRef DOI lookup for {} references", len(candidates))

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Process in small concurrent batches to respect rate limits
        sem = asyncio.Semaphore(3)

        async def _lookup(idx: int, ref: Reference) -> None:
            async with sem:
                await _crossref_lookup(client, ref)

        tasks = [_lookup(idx, ref) for idx, ref in candidates]
        await asyncio.gather(*tasks, return_exceptions=True)

    return refs


async def _crossref_lookup(client: httpx.AsyncClient, ref: Reference) -> None:
    """Look up a single reference on CrossRef by title."""
    query = ref.title
    if ref.authors:
        query = f"{ref.authors[0]} {ref.title}"

    try:
        resp = await client.get(
            f"{_CROSSREF_BASE}/works",
            params={
                "query": query,
                "rows": 1,
                "mailto": _CROSSREF_MAILTO,
            },
        )
        if resp.status_code != 200:
            return

        data = resp.json()
        items = data.get("message", {}).get("items", [])
        if not items:
            return

        best = items[0]

        # Only accept if the title is a reasonable match
        cr_title = " ".join(best.get("title", []))
        if not cr_title:
            return

        # Simple similarity check — first 40 chars lowered
        if ref.title[:40].lower() not in cr_title[:60].lower() and cr_title[:40].lower() not in ref.title[:60].lower():
            return

        # Extract DOI
        doi = best.get("DOI", "")
        if doi:
            ref.doi = doi

        # Fill in venue if missing
        if not ref.venue:
            ref.venue = " ".join(best.get("container-title", []))

        # Fill in year if missing
        if not ref.year:
            issued = best.get("issued", {}).get("date-parts", [[]])
            if issued and issued[0]:
                ref.year = str(issued[0][0])

        ref.resolved = True

    except Exception as exc:
        logger.debug("CrossRef lookup failed for '{}': {}", ref.title[:50], exc)
