"""SCRIPTUM document processing tools.

Public API:
    - Data models: ParsedDocument, Section, Table, Figure, Equation, Reference, DocumentMetadata
    - Parsers: parse_pdf, parse_latex
    - Reference resolution: resolve_references
"""

from tools.document.latex_parser import parse_latex
from tools.document.models import (
    DocumentMetadata,
    Equation,
    Figure,
    ParsedDocument,
    Reference,
    Section,
    Table,
)
from tools.document.pdf_parser import parse_pdf
from tools.document.reference_resolver import resolve_references

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
