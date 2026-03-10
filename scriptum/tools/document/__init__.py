"""SCRIPTUM document processing tools.

Public API:
    - Data models: ParsedDocument, Section, Table, Figure, Equation, Reference, DocumentMetadata
    - Parsers: parse_pdf, parse_latex
    - Reference resolution: resolve_references
"""

from tools.document.models import (
    DocumentMetadata,
    Equation,
    Figure,
    ParsedDocument,
    Reference,
    Section,
    Table,
)

# Parser imports are deferred because they pull in docling, which may
# not be installed in lightweight/test environments.
try:
    from tools.document.latex_parser import parse_latex
    from tools.document.pdf_parser import parse_pdf
    from tools.document.reference_resolver import resolve_references
except ImportError:
    parse_latex = None  # type: ignore[assignment,misc]
    parse_pdf = None  # type: ignore[assignment,misc]
    resolve_references = None  # type: ignore[assignment,misc]

__all__ = [
    "DocumentMetadata",
    "Equation",
    "Figure",
    "ParsedDocument",
    "Reference",
    "Section",
    "Table",
    "parse_pdf",
    "parse_latex",
    "resolve_references",
]
