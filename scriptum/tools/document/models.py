"""Data models for SCRIPTUM document processing pipeline.

These are plain dataclasses (not Pydantic) because they are ephemeral
internal transfer objects that flow through agents — they never cross
an API boundary or get persisted to the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentMetadata:
    """Top-level metadata extracted from a parsed document."""

    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    page_count: int = 0
    source_format: str = ""  # "pdf" | "latex"
    parse_time_seconds: float = 0.0


@dataclass
class Section:
    """A logical section of the document."""

    heading: str = ""
    level: int = 1  # 1 = top-level, 2 = sub-section, etc.
    text: str = ""
    page_span: tuple[int, int] | None = None  # (start_page, end_page), 0-indexed


@dataclass
class Table:
    """A table extracted from the document."""

    caption: str = ""
    markdown: str = ""  # Markdown representation of the table
    page: int | None = None


@dataclass
class Figure:
    """A figure/image reference extracted from the document."""

    caption: str = ""
    page: int | None = None


@dataclass
class Equation:
    """A mathematical equation extracted from the document."""

    latex: str = ""
    context: str = ""  # Surrounding text for context
    page: int | None = None


@dataclass
class Reference:
    """A bibliographic reference extracted from the document."""

    raw_text: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    doi: str = ""
    arxiv_id: str = ""
    resolved: bool = False  # True once enriched via LLM/API (Phase 3)


@dataclass
class ParsedDocument:
    """Normalized output from Docling, consumed by SCRIPTUM agents.

    This is the single transfer object that flows from document parsing
    through the review pipeline. All parser implementations (PDF, LaTeX)
    produce this same structure.
    """

    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    sections: list[Section] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    figures: list[Figure] = field(default_factory=list)
    equations: list[Equation] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    full_text_markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary (JSON-compatible)."""
        return {
            "metadata": {
                "title": self.metadata.title,
                "authors": self.metadata.authors,
                "abstract": self.metadata.abstract,
                "keywords": self.metadata.keywords,
                "page_count": self.metadata.page_count,
                "source_format": self.metadata.source_format,
                "parse_time_seconds": self.metadata.parse_time_seconds,
            },
            "sections": [
                {
                    "heading": s.heading,
                    "level": s.level,
                    "text": s.text,
                    "page_span": list(s.page_span) if s.page_span else None,
                }
                for s in self.sections
            ],
            "tables": [
                {"caption": t.caption, "markdown": t.markdown, "page": t.page} for t in self.tables
            ],
            "figures": [{"caption": f.caption, "page": f.page} for f in self.figures],
            "equations": [
                {"latex": e.latex, "context": e.context, "page": e.page} for e in self.equations
            ],
            "references": [
                {
                    "raw_text": r.raw_text,
                    "title": r.title,
                    "authors": r.authors,
                    "year": r.year,
                    "venue": r.venue,
                    "doi": r.doi,
                    "arxiv_id": r.arxiv_id,
                    "resolved": r.resolved,
                }
                for r in self.references
            ],
            "full_text_markdown": self.full_text_markdown,
        }
