"""PDF parsing via Docling for SCRIPTUM.

Public API
----------
- ``parse_pdf(file_path)`` — async entry point returning a ``ParsedDocument``.

The internal ``_docling_to_parsed()`` helper is also used by the LaTeX
parser since Docling produces the same ``DoclingDocument`` regardless of
input format.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from docling_core.types.doc import (
    DoclingDocument,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
)
from loguru import logger

from scriptum_ai.tools.document.converter import get_converter
from scriptum_ai.tools.document.models import (
    DocumentMetadata,
    Equation,
    Figure,
    ParsedDocument,
    Reference,
    Section,
    Table,
)

# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


async def parse_pdf(file_path: str | Path) -> ParsedDocument:
    """Parse a PDF file and return a normalised ``ParsedDocument``.

    CPU-bound Docling work runs in a thread so the event loop stays free.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    logger.info("Parsing PDF: {}", file_path.name)
    start = time.perf_counter()

    docling_doc = await asyncio.to_thread(_convert_document, file_path)

    elapsed = time.perf_counter() - start
    parsed = _docling_to_parsed(docling_doc, source_format="pdf", parse_time=elapsed)

    logger.info(
        "PDF parsed | {} sections | {} tables | {} refs | {:.1f}s",
        len(parsed.sections),
        len(parsed.tables),
        len(parsed.references),
        elapsed,
    )
    return parsed


# ---------------------------------------------------------------------------
# Sync conversion (runs inside asyncio.to_thread)
# ---------------------------------------------------------------------------


def _convert_document(path: Path) -> DoclingDocument:
    """Run the Docling converter synchronously and return the document."""
    result = get_converter().convert(str(path))
    return result.document


# ---------------------------------------------------------------------------
# DoclingDocument → ParsedDocument mapping (shared with latex_parser)
# ---------------------------------------------------------------------------


def _docling_to_parsed(
    doc: DoclingDocument,
    *,
    source_format: str,
    parse_time: float,
) -> ParsedDocument:
    """Map a Docling ``DoclingDocument`` to SCRIPTUM's ``ParsedDocument``."""

    sections: list[Section] = []
    tables: list[Table] = []
    figures: list[Figure] = []
    equations: list[Equation] = []
    references: list[Reference] = []

    title = ""
    abstract = ""
    page_count = len(doc.pages) if doc.pages else 0

    # ------------------------------------------------------------------
    # Walk the structured body tree to extract sections, equations, etc.
    # ------------------------------------------------------------------
    current_heading = ""
    current_level = 1
    current_paragraphs: list[str] = []
    current_page_start: int | None = None
    current_page_end: int | None = None

    # Track whether we're inside a "references" section
    in_references_section = False

    for item, _depth in doc.iterate_items():
        # Page provenance
        item_page: int | None = None
        if hasattr(item, "prov") and item.prov:
            item_page = item.prov[0].page_no

        # --- Title ---
        if hasattr(item, "label") and str(item.label).lower() == "title":
            if isinstance(item, TextItem) and not title:
                title = item.text.strip()
            continue

        # --- Section headers ---
        if isinstance(item, SectionHeaderItem):
            # Flush previous section
            _flush_section(
                sections,
                current_heading,
                current_level,
                current_paragraphs,
                current_page_start,
                current_page_end,
            )
            current_heading = item.text.strip()
            current_level = item.level
            current_paragraphs = []
            current_page_start = item_page
            current_page_end = item_page

            # Detect references section
            heading_lower = current_heading.lower()
            in_references_section = heading_lower in (
                "references",
                "bibliography",
                "works cited",
                "literature",
            )
            continue

        # --- Text items (paragraphs) ---
        if isinstance(item, TextItem):
            text = item.text.strip()
            if not text:
                continue

            # Capture abstract
            if not abstract and current_heading.lower() == "abstract":
                abstract = text

            # Collect references from the references section
            if in_references_section:
                references.append(Reference(raw_text=text))
                continue

            current_paragraphs.append(text)
            if item_page is not None:
                current_page_end = item_page
            continue

        # --- Tables ---
        if isinstance(item, TableItem):
            caption = ""
            if item.captions:
                caption_parts = []
                for cap_ref in item.captions:
                    cap_item = doc.get_ref_item(cap_ref)
                    if hasattr(cap_item, "text"):
                        caption_parts.append(cap_item.text.strip())
                caption = " ".join(caption_parts)

            md = ""
            try:
                df = item.export_to_dataframe(doc=doc)
                md = df.to_markdown(index=False)
            except Exception:
                # Fallback: use raw table data if dataframe export fails
                if item.data:
                    md = str(item.data)

            tables.append(Table(caption=caption, markdown=md, page=item_page))
            continue

        # --- Figures / pictures ---
        if isinstance(item, PictureItem):
            caption = ""
            if hasattr(item, "captions") and item.captions:
                caption_parts = []
                for cap_ref in item.captions:
                    cap_item = doc.get_ref_item(cap_ref)
                    if hasattr(cap_item, "text"):
                        caption_parts.append(cap_item.text.strip())
                caption = " ".join(caption_parts)
            figures.append(Figure(caption=caption, page=item_page))
            continue

        # --- Formulas / equations ---
        if hasattr(item, "formula"):
            context = ""
            if current_paragraphs:
                context = current_paragraphs[-1][:200]
            equations.append(Equation(latex=item.formula, context=context, page=item_page))
            continue

    # Flush the last section
    _flush_section(
        sections,
        current_heading,
        current_level,
        current_paragraphs,
        current_page_start,
        current_page_end,
    )

    # ------------------------------------------------------------------
    # Full markdown export
    # ------------------------------------------------------------------
    full_text_markdown = doc.export_to_markdown()

    # ------------------------------------------------------------------
    # Assemble ParsedDocument
    # ------------------------------------------------------------------
    metadata = DocumentMetadata(
        title=title,
        authors=[],  # Docling doesn't reliably extract author lists
        abstract=abstract,
        keywords=[],
        page_count=page_count,
        source_format=source_format,
        parse_time_seconds=round(parse_time, 3),
    )

    return ParsedDocument(
        metadata=metadata,
        sections=sections,
        tables=tables,
        figures=figures,
        equations=equations,
        references=references,
        full_text_markdown=full_text_markdown,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flush_section(
    sections: list[Section],
    heading: str,
    level: int,
    paragraphs: list[str],
    page_start: int | None,
    page_end: int | None,
) -> None:
    """Append the accumulated section to the list (if non-empty)."""
    text = "\n\n".join(paragraphs)
    if heading or text:
        page_span = None
        if page_start is not None and page_end is not None:
            page_span = (page_start, page_end)
        sections.append(Section(heading=heading, level=level, text=text, page_span=page_span))
