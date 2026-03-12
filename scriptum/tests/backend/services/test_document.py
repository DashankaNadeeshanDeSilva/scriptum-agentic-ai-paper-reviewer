"""Tests for the document processing service layer.

Tests verify routing, validation, and error handling. Parsers are mocked
since their logic is tested separately in ``tests/tools/document/``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scriptum_ai.backend.core.config import DocumentConfig
from scriptum_ai.backend.services.document import DocumentProcessingError, process_document
from scriptum_ai.tools.document.models import DocumentMetadata, ParsedDocument, Reference


def _make_parsed(source_format: str = "pdf") -> ParsedDocument:
    """Helper to create a minimal ParsedDocument for mocking."""
    return ParsedDocument(
        metadata=DocumentMetadata(
            title="Test Paper",
            source_format=source_format,
            parse_time_seconds=1.0,
        ),
        references=[Reference(raw_text="Smith 2020")],
    )


# =========================================================================
# File validation
# =========================================================================


class TestFileValidation:
    @pytest.mark.asyncio
    async def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Document not found"):
            await process_document(tmp_path / "nonexistent.pdf")

    @pytest.mark.asyncio
    async def test_unsupported_file_type_from_extension(self, tmp_path):
        docx = tmp_path / "paper.docx"
        docx.write_bytes(b"fake")

        with pytest.raises(DocumentProcessingError, match="Unsupported file type"):
            await process_document(docx)

    @pytest.mark.asyncio
    async def test_unsupported_explicit_file_type(self, tmp_path):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"fake")

        with pytest.raises(DocumentProcessingError, match="Unsupported file type"):
            await process_document(pdf, file_type="docx")

    @pytest.mark.asyncio
    async def test_file_too_large(self, tmp_path):
        pdf = tmp_path / "big.pdf"
        # Create a file larger than 1 MB (our mock limit)
        pdf.write_bytes(b"x" * (2 * 1024 * 1024))

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig(max_file_size_mb=1)

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            pytest.raises(DocumentProcessingError, match="File too large"),
        ):
            await process_document(pdf)

    @pytest.mark.asyncio
    async def test_file_within_size_limit(self, tmp_path):
        pdf = tmp_path / "small.pdf"
        pdf.write_bytes(b"x" * 100)

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig(max_file_size_mb=1)

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch(
                "scriptum_ai.backend.services.document.parse_pdf",
                new_callable=AsyncMock,
                return_value=_make_parsed(),
            ),
        ):
            result = await process_document(pdf)
            assert result.metadata.title == "Test Paper"


# =========================================================================
# File type routing
# =========================================================================


class TestFileTypeRouting:
    @pytest.mark.asyncio
    async def test_pdf_routes_to_parse_pdf(self, tmp_path):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"fake")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        mock_parse_pdf = AsyncMock(return_value=_make_parsed("pdf"))

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch("scriptum_ai.backend.services.document.parse_pdf", mock_parse_pdf),
        ):
            result = await process_document(pdf)

        mock_parse_pdf.assert_awaited_once()
        assert result.metadata.source_format == "pdf"

    @pytest.mark.asyncio
    async def test_tex_routes_to_parse_latex(self, tmp_path):
        tex = tmp_path / "paper.tex"
        tex.write_text(r"\documentclass{article}")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        mock_parse_latex = AsyncMock(return_value=_make_parsed("latex"))

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch("scriptum_ai.backend.services.document.parse_latex", mock_parse_latex),
        ):
            result = await process_document(tex)

        mock_parse_latex.assert_awaited_once()
        assert result.metadata.source_format == "latex"

    @pytest.mark.asyncio
    async def test_explicit_type_overrides_extension(self, tmp_path):
        """A .pdf file with file_type='tex' routes to LaTeX parser."""
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"fake")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        mock_parse_latex = AsyncMock(return_value=_make_parsed("latex"))

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch("scriptum_ai.backend.services.document.parse_latex", mock_parse_latex),
        ):
            await process_document(pdf, file_type="tex")

        mock_parse_latex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_latex_type_string(self, tmp_path):
        """'latex' as file_type should also route to LaTeX parser."""
        tex = tmp_path / "paper.tex"
        tex.write_text("content")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        mock_parse_latex = AsyncMock(return_value=_make_parsed("latex"))

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch("scriptum_ai.backend.services.document.parse_latex", mock_parse_latex),
        ):
            await process_document(tex, file_type="latex")

        mock_parse_latex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_case_insensitive_file_type(self, tmp_path):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"fake")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        mock_parse_pdf = AsyncMock(return_value=_make_parsed())

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch("scriptum_ai.backend.services.document.parse_pdf", mock_parse_pdf),
        ):
            await process_document(pdf, file_type="PDF")

        mock_parse_pdf.assert_awaited_once()


# =========================================================================
# Reference resolution
# =========================================================================


class TestReferenceResolution:
    @pytest.mark.asyncio
    async def test_resolve_refs_false_skips_resolver(self, tmp_path):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"fake")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        mock_resolve = AsyncMock(return_value=[])

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch(
                "scriptum_ai.backend.services.document.parse_pdf",
                new_callable=AsyncMock,
                return_value=_make_parsed(),
            ),
            patch("scriptum_ai.backend.services.document.resolve_references", mock_resolve),
        ):
            await process_document(pdf, resolve_refs=False)

        mock_resolve.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_resolve_refs_true_calls_resolver(self, tmp_path):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"fake")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        parsed = _make_parsed()
        resolved_refs = [Reference(raw_text="Smith 2020", resolved=True)]
        mock_resolve = AsyncMock(return_value=resolved_refs)

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch(
                "scriptum_ai.backend.services.document.parse_pdf",
                new_callable=AsyncMock,
                return_value=parsed,
            ),
            patch("scriptum_ai.backend.services.document.resolve_references", mock_resolve),
        ):
            result = await process_document(pdf, resolve_refs=True)

        mock_resolve.assert_awaited_once()
        assert result.references == resolved_refs

    @pytest.mark.asyncio
    async def test_resolve_refs_skipped_when_no_references(self, tmp_path):
        """Even with resolve_refs=True, skip if document has no references."""
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"fake")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        parsed = ParsedDocument(metadata=DocumentMetadata(title="No Refs"))
        mock_resolve = AsyncMock()

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch(
                "scriptum_ai.backend.services.document.parse_pdf",
                new_callable=AsyncMock,
                return_value=parsed,
            ),
            patch("scriptum_ai.backend.services.document.resolve_references", mock_resolve),
        ):
            await process_document(pdf, resolve_refs=True)

        mock_resolve.assert_not_awaited()


# =========================================================================
# Auto file type detection
# =========================================================================


class TestAutoFileTypeDetection:
    @pytest.mark.asyncio
    async def test_detects_pdf_from_extension(self, tmp_path):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"fake")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        mock_parse_pdf = AsyncMock(return_value=_make_parsed())

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch("scriptum_ai.backend.services.document.parse_pdf", mock_parse_pdf),
        ):
            await process_document(pdf)  # No file_type arg

        mock_parse_pdf.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_detects_tex_from_extension(self, tmp_path):
        tex = tmp_path / "paper.tex"
        tex.write_text("content")

        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        mock_parse_latex = AsyncMock(return_value=_make_parsed("latex"))

        with (
            patch("scriptum_ai.backend.services.document.get_settings", return_value=mock_settings),
            patch("scriptum_ai.backend.services.document.parse_latex", mock_parse_latex),
        ):
            await process_document(tex)

        mock_parse_latex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_extension_raises(self, tmp_path):
        doc = tmp_path / "paper.odt"
        doc.write_bytes(b"fake")

        with pytest.raises(DocumentProcessingError, match="Unsupported"):
            await process_document(doc)
