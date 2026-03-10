"""Tests for LaTeX parsing via Docling.

The LaTeX parser reuses ``_docling_to_parsed()`` from pdf_parser, so
the mapping logic is thoroughly tested in ``test_pdf_parser.py``. These
tests focus on LaTeX-specific behaviour:

- File validation (FileNotFoundError)
- source_format is set to "latex"
- Delegation to the converter
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.tools.document.mock_docling import (
    FakeDoclingDocument,
    FakeSectionHeaderItem,
    FakeTextItem,
    FakeTitleItem,
)
from tools.document.latex_parser import parse_latex
from tools.document.models import ParsedDocument


class TestParseLatex:
    @pytest.mark.asyncio
    async def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="LaTeX file not found"):
            await parse_latex(tmp_path / "nonexistent.tex")

    @pytest.mark.asyncio
    async def test_returns_parsed_document(self, tmp_path):
        tex_file = tmp_path / "paper.tex"
        tex_file.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")

        mock_doc = FakeDoclingDocument(
            items=[
                (FakeTitleItem("LaTeX Paper"), 0),
                (FakeSectionHeaderItem("Introduction", level=1), 0),
                (FakeTextItem("This is written in LaTeX."), 1),
            ],
            pages={0: MagicMock()},
            markdown="# LaTeX Paper\n\n## Introduction\n\nThis is written in LaTeX.",
        )

        with patch("tools.document.latex_parser._convert_latex", return_value=mock_doc):
            result = await parse_latex(tex_file)

        assert isinstance(result, ParsedDocument)
        assert result.metadata.title == "LaTeX Paper"
        assert len(result.sections) >= 1

    @pytest.mark.asyncio
    async def test_source_format_is_latex(self, tmp_path):
        """LaTeX parser must set source_format='latex' in metadata."""
        tex_file = tmp_path / "paper.tex"
        tex_file.write_text(r"\documentclass{article}")

        mock_doc = FakeDoclingDocument(items=[], pages={}, markdown="")

        with patch("tools.document.latex_parser._convert_latex", return_value=mock_doc):
            result = await parse_latex(tex_file)

        assert result.metadata.source_format == "latex"

    @pytest.mark.asyncio
    async def test_parse_time_recorded(self, tmp_path):
        tex_file = tmp_path / "paper.tex"
        tex_file.write_text(r"\documentclass{article}")

        mock_doc = FakeDoclingDocument(items=[], pages={}, markdown="")

        with patch("tools.document.latex_parser._convert_latex", return_value=mock_doc):
            result = await parse_latex(tex_file)

        assert result.metadata.parse_time_seconds >= 0

    @pytest.mark.asyncio
    async def test_accepts_path_as_string(self, tmp_path):
        """parse_latex should accept both str and Path."""
        tex_file = tmp_path / "paper.tex"
        tex_file.write_text(r"\documentclass{article}")

        mock_doc = FakeDoclingDocument(items=[], pages={}, markdown="")

        with patch("tools.document.latex_parser._convert_latex", return_value=mock_doc):
            result = await parse_latex(str(tex_file))

        assert isinstance(result, ParsedDocument)
