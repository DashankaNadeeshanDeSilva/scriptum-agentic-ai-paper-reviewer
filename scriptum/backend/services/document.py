"""Document processing service for SCRIPTUM.

This service is the single entry point for all document processing in the
backend. It validates inputs, routes to the correct parser (PDF or LaTeX),
optionally resolves references, and returns a normalised ``ParsedDocument``.

Called by the review orchestrator (Phase 3) and the file upload API.
"""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger

from backend.core.config import get_settings
from tools.document.latex_parser import parse_latex
from tools.document.models import ParsedDocument
from tools.document.pdf_parser import parse_pdf
from tools.document.reference_resolver import resolve_references

# Supported file types mapped to their parser
_SUPPORTED_TYPES: dict[str, str] = {
    "pdf": "pdf",
    "tex": "latex",
    "latex": "latex",
}


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""


async def process_document(
    file_path: str | Path,
    *,
    file_type: str | None = None,
    resolve_refs: bool = False,
) -> ParsedDocument:
    """Parse a document and return a normalised ``ParsedDocument``.

    Parameters
    ----------
    file_path:
        Path to the PDF or LaTeX file on disk.
    file_type:
        Explicit file type (``"pdf"``, ``"tex"``, ``"latex"``). If ``None``,
        inferred from the file extension.
    resolve_refs:
        If ``True``, run the reference resolver after parsing to enrich
        bibliography entries. Currently a no-op stub (Phase 3).

    Returns
    -------
    ParsedDocument
        Normalised document with extracted sections, tables, figures,
        equations, and references.

    Raises
    ------
    FileNotFoundError
        If ``file_path`` does not exist.
    DocumentProcessingError
        If the file type is unsupported or the file exceeds the size limit.
    """
    path = Path(file_path)

    # ------------------------------------------------------------------
    # 1. Validate file exists
    # ------------------------------------------------------------------
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    # ------------------------------------------------------------------
    # 2. Resolve file type
    # ------------------------------------------------------------------
    if file_type is None:
        ext = path.suffix.lstrip(".").lower()
        file_type = ext

    normalised_type = _SUPPORTED_TYPES.get(file_type.lower())
    if normalised_type is None:
        supported = ", ".join(sorted(_SUPPORTED_TYPES.keys()))
        raise DocumentProcessingError(
            f"Unsupported file type: '{file_type}'. Supported: {supported}"
        )

    # ------------------------------------------------------------------
    # 3. Validate file size
    # ------------------------------------------------------------------
    settings = get_settings()
    max_bytes = settings.document.max_file_size_mb * 1024 * 1024
    file_size = os.path.getsize(path)
    if file_size > max_bytes:
        size_mb = file_size / (1024 * 1024)
        raise DocumentProcessingError(
            f"File too large: {size_mb:.1f} MB (limit: {settings.document.max_file_size_mb} MB)"
        )

    # ------------------------------------------------------------------
    # 4. Parse document
    # ------------------------------------------------------------------
    logger.info("Processing document: {} (type={})", path.name, normalised_type)

    if normalised_type == "pdf":
        parsed = await parse_pdf(path)
    else:
        parsed = await parse_latex(path)

    # ------------------------------------------------------------------
    # 5. Optionally resolve references
    # ------------------------------------------------------------------
    if resolve_refs and parsed.references:
        logger.info("Resolving {} references", len(parsed.references))
        parsed.references = await resolve_references(parsed.references)

    logger.info(
        "Document processed: {} | title='{}' | {} sections | {} tables | "
        "{} figures | {} equations | {} refs | {:.1f}s",
        path.name,
        parsed.metadata.title[:60] or "(untitled)",
        len(parsed.sections),
        len(parsed.tables),
        len(parsed.figures),
        len(parsed.equations),
        len(parsed.references),
        parsed.metadata.parse_time_seconds,
    )

    return parsed
