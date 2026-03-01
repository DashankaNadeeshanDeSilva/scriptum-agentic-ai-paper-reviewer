"""Reference resolver for structured bibliography extraction.

**Current status: STUB** — returns references unchanged.

Full implementation in Phase 3 when LiteLLM integration is ready:

Phase A — LLM structuring
    Batch raw reference strings through an LLM with structured output
    to populate ``Reference.title``, ``authors``, ``year``, ``venue``.

Phase B — API enrichment
    Query Semantic Scholar / CrossRef to resolve DOIs and arXiv IDs,
    filling ``Reference.doi`` and ``Reference.arxiv_id``.
"""

from __future__ import annotations

from loguru import logger

from tools.document.models import Reference


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
        If ``True``, use LLM to structure raw text into fields.
    use_apis:
        If ``True``, query external APIs (Semantic Scholar, CrossRef)
        to resolve DOIs and enrich metadata.

    Returns
    -------
    list[Reference]
        The same references, potentially with structured fields populated
        and ``resolved=True``.

    Notes
    -----
    This is currently a no-op stub. The interface exists so the document
    service can call it without code changes when Phase 3 fills in the
    implementation.
    """
    if not raw_refs:
        return raw_refs

    logger.debug(
        "Reference resolver stub called with {} refs (LLM={}, APIs={})",
        len(raw_refs),
        use_llm,
        use_apis,
    )

    # Phase 3 TODO: Implement LLM-based structuring and API enrichment
    return raw_refs
