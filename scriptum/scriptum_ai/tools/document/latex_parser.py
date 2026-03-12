"""LaTeX parsing via Docling for SCRIPTUM.

Docling handles LaTeX natively through the same ``convert()`` API used
for PDFs. The ``_docling_to_parsed()`` mapping function from
``pdf_parser`` is reused since Docling produces an identical
``DoclingDocument`` regardless of input format.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from loguru import logger

from scriptum_ai.tools.document.converter import get_converter
from scriptum_ai.tools.document.models import ParsedDocument
from scriptum_ai.tools.document.pdf_parser import _docling_to_parsed


async def parse_latex(file_path: str | Path) -> ParsedDocument:
    """Parse a LaTeX file and return a normalised ``ParsedDocument``.

    CPU-bound Docling work runs in a thread so the event loop stays free.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"LaTeX file not found: {file_path}")

    logger.info("Parsing LaTeX: {}", file_path.name)
    start = time.perf_counter()

    docling_doc = await asyncio.to_thread(_convert_latex, file_path)

    elapsed = time.perf_counter() - start
    parsed = _docling_to_parsed(docling_doc, source_format="latex", parse_time=elapsed)

    logger.info(
        "LaTeX parsed | {} sections | {} tables | {} refs | {:.1f}s",
        len(parsed.sections),
        len(parsed.tables),
        len(parsed.references),
        elapsed,
    )
    return parsed


def _convert_latex(path: Path):
    """Run the Docling converter synchronously on a LaTeX file."""
    result = get_converter().convert(str(path))
    return result.document
