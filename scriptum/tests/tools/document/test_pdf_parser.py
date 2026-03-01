"""Tests for PDF parsing via Docling.

The primary focus is testing ``_docling_to_parsed()``, which maps a
DoclingDocument to SCRIPTUM's ParsedDocument. This function contains
the core extraction logic shared by both PDF and LaTeX parsers.

The ``parse_pdf()`` async entry point is tested for file validation
and delegation to the converter.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.tools.document.mock_docling import (
    FakeDoclingDocument,
    FakeFormulaItem,
    FakePictureItem,
    FakeProvenanceItem,
    FakeSectionHeaderItem,
    FakeTableItem,
    FakeTextItem,
    FakeTitleItem,
)
from tools.document.models import ParsedDocument
from tools.document.pdf_parser import _docling_to_parsed, _flush_section, parse_pdf

# =========================================================================
# _docling_to_parsed() — core mapping logic
# =========================================================================


class TestDoclingToParsed:
    """Tests for the DoclingDocument → ParsedDocument mapping."""

    def test_full_paper_extraction(self, mock_docling_document):
        """Test with a realistic academic paper mock."""
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=2.5)

        assert isinstance(parsed, ParsedDocument)
        assert parsed.metadata.source_format == "pdf"
        assert parsed.metadata.parse_time_seconds == 2.5

    def test_title_extraction(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        assert parsed.metadata.title == "Deep Learning for Climate Prediction"

    def test_abstract_extraction(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        assert "novel approach to climate prediction" in parsed.metadata.abstract

    def test_section_extraction(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        headings = [s.heading for s in parsed.sections]

        assert "Abstract" in headings
        assert "Introduction" in headings
        assert "Methods" in headings
        assert "Data Preprocessing" in headings
        assert "Results" in headings
        assert "Conclusion" in headings

    def test_section_levels(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        level_map = {s.heading: s.level for s in parsed.sections}

        assert level_map["Introduction"] == 1
        assert level_map["Methods"] == 1
        assert level_map["Data Preprocessing"] == 2

    def test_section_text_content(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        intro = next(s for s in parsed.sections if s.heading == "Introduction")
        assert "pressing challenges" in intro.text
        assert "deep learning offer" in intro.text

    def test_introduction_has_two_paragraphs(self, mock_docling_document):
        """Paragraphs within a section are joined with double newlines."""
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        intro = next(s for s in parsed.sections if s.heading == "Introduction")
        assert "\n\n" in intro.text

    def test_table_extraction(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        assert len(parsed.tables) == 1
        table = parsed.tables[0]
        assert "Model performance comparison" in table.caption
        assert table.page == 2

    def test_table_has_content(self, mock_docling_document):
        """Table should have non-empty markdown (from DataFrame or fallback)."""
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        table = parsed.tables[0]
        assert len(table.markdown) > 0

    def test_figure_extraction(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        assert len(parsed.figures) == 1
        fig = parsed.figures[0]
        assert "Architecture overview" in fig.caption
        assert fig.page == 3

    def test_equation_extraction(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        assert len(parsed.equations) == 1
        eq = parsed.equations[0]
        assert "\\sum" in eq.latex
        assert eq.page == 1

    def test_equation_context(self, mock_docling_document):
        """Equation context should contain nearby paragraph text."""
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        eq = parsed.equations[0]
        assert "transformer" in eq.context

    def test_reference_extraction(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        assert len(parsed.references) == 3
        raw_texts = [r.raw_text for r in parsed.references]
        assert any("Smith" in t for t in raw_texts)
        assert any("Chen" in t for t in raw_texts)
        assert any("Brown" in t for t in raw_texts)

    def test_references_are_unresolved(self, mock_docling_document):
        """All references should start as unresolved."""
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        for ref in parsed.references:
            assert ref.resolved is False

    def test_references_not_in_sections(self, mock_docling_document):
        """Text in the References section should NOT appear in regular sections."""
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        # References heading creates a section but with no text
        ref_section = next((s for s in parsed.sections if s.heading == "References"), None)
        if ref_section:
            assert ref_section.text == ""

    def test_page_count(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        assert parsed.metadata.page_count == 5

    def test_full_text_markdown(self, mock_docling_document):
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        assert "Deep Learning for Climate Prediction" in parsed.full_text_markdown

    def test_page_span(self, mock_docling_document):
        """Sections should track which pages they span."""
        parsed = _docling_to_parsed(mock_docling_document, source_format="pdf", parse_time=0.1)
        intro = next(s for s in parsed.sections if s.heading == "Introduction")
        assert intro.page_span is not None
        assert intro.page_span[0] == 0  # starts on page 0
        assert intro.page_span[1] == 1  # second paragraph on page 1

    def test_source_format_passed_through(self):
        """source_format parameter is set in metadata."""
        doc = FakeDoclingDocument(items=[], pages={}, markdown="")
        parsed = _docling_to_parsed(doc, source_format="latex", parse_time=0.0)
        assert parsed.metadata.source_format == "latex"

    def test_parse_time_rounded(self):
        doc = FakeDoclingDocument(items=[], pages={}, markdown="")
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=1.23456789)
        assert parsed.metadata.parse_time_seconds == 1.235


class TestDoclingToParsedEdgeCases:
    """Edge cases for the mapping function."""

    def test_empty_document(self, empty_docling_document):
        parsed = _docling_to_parsed(empty_docling_document, source_format="pdf", parse_time=0.0)
        assert parsed.metadata.title == ""
        assert parsed.metadata.abstract == ""
        assert parsed.sections == []
        assert parsed.tables == []
        assert parsed.figures == []
        assert parsed.equations == []
        assert parsed.references == []
        assert parsed.metadata.page_count == 0

    def test_title_only_document(self):
        """Document with only a title and nothing else."""
        doc = FakeDoclingDocument(
            items=[(FakeTitleItem("Just a Title"), 0)],
            pages={0: MagicMock()},
            markdown="# Just a Title",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert parsed.metadata.title == "Just a Title"
        assert parsed.sections == []

    def test_only_first_title_captured(self):
        """If multiple title items exist, only the first is used."""
        doc = FakeDoclingDocument(
            items=[
                (FakeTitleItem("First Title"), 0),
                (FakeTitleItem("Second Title"), 0),
            ],
            pages={},
            markdown="",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert parsed.metadata.title == "First Title"

    def test_bibliography_heading_detected(self):
        """'Bibliography' heading should also trigger reference collection."""
        doc = FakeDoclingDocument(
            items=[
                (FakeSectionHeaderItem("Bibliography", level=1), 0),
                (FakeTextItem("Jones 2021. A study."), 1),
            ],
            pages={},
            markdown="",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert len(parsed.references) == 1
        assert "Jones 2021" in parsed.references[0].raw_text

    def test_works_cited_heading_detected(self):
        doc = FakeDoclingDocument(
            items=[
                (FakeSectionHeaderItem("Works Cited", level=1), 0),
                (FakeTextItem("Doe 2022. Some work."), 1),
            ],
            pages={},
            markdown="",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert len(parsed.references) == 1

    def test_table_without_caption(self):
        """Tables with no captions should still be extracted."""
        doc = FakeDoclingDocument(
            items=[
                (
                    FakeTableItem(
                        captions=[],
                        data="some data",
                        prov=[FakeProvenanceItem(page_no=1)],
                    ),
                    0,
                ),
            ],
            pages={},
            markdown="",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert len(parsed.tables) == 1
        assert parsed.tables[0].caption == ""

    def test_table_dataframe_export_fallback(self):
        """If export_to_dataframe fails, raw data string is used."""

        class FailingTableItem(FakeTableItem):
            def export_to_dataframe(self, doc=None):
                raise RuntimeError("No pandas")

        doc = FakeDoclingDocument(
            items=[
                (FailingTableItem(data="fallback data", prov=[FakeProvenanceItem(1)]), 0),
            ],
            pages={},
            markdown="",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert parsed.tables[0].markdown == "fallback data"

    def test_figure_without_caption(self):
        doc = FakeDoclingDocument(
            items=[(FakePictureItem(captions=[], prov=[FakeProvenanceItem(2)]), 0)],
            pages={},
            markdown="",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert len(parsed.figures) == 1
        assert parsed.figures[0].caption == ""
        assert parsed.figures[0].page == 2

    def test_equation_without_preceding_text(self):
        """Equation with no preceding paragraphs should have empty context."""
        doc = FakeDoclingDocument(
            items=[
                (FakeSectionHeaderItem("Math", level=1), 0),
                (FakeFormulaItem("x^2", prov=[FakeProvenanceItem(0)]), 1),
            ],
            pages={},
            markdown="",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert len(parsed.equations) == 1
        assert parsed.equations[0].context == ""

    def test_empty_text_items_skipped(self):
        """TextItems with whitespace-only text are ignored."""
        doc = FakeDoclingDocument(
            items=[
                (FakeSectionHeaderItem("Section", level=1), 0),
                (FakeTextItem(""), 1),
                (FakeTextItem("   "), 1),
                (FakeTextItem("Real text"), 1),
            ],
            pages={},
            markdown="",
        )
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        section = parsed.sections[0]
        assert section.text == "Real text"

    def test_no_pages_gives_zero_count(self):
        doc = FakeDoclingDocument(items=[], pages=None, markdown="")
        # pages=None; len(None) would fail, so code checks `if doc.pages`
        parsed = _docling_to_parsed(doc, source_format="pdf", parse_time=0.0)
        assert parsed.metadata.page_count == 0


# =========================================================================
# _flush_section() helper
# =========================================================================


class TestFlushSection:
    def test_appends_section_with_heading_and_text(self):
        sections = []
        _flush_section(sections, "Intro", 1, ["Para 1", "Para 2"], 0, 1)
        assert len(sections) == 1
        assert sections[0].heading == "Intro"
        assert sections[0].text == "Para 1\n\nPara 2"
        assert sections[0].page_span == (0, 1)

    def test_skips_empty_section(self):
        sections = []
        _flush_section(sections, "", 1, [], None, None)
        assert sections == []

    def test_heading_only_section(self):
        """A section with a heading but no paragraphs is still recorded."""
        sections = []
        _flush_section(sections, "Empty Section", 1, [], 3, 3)
        assert len(sections) == 1
        assert sections[0].text == ""

    def test_no_page_span_when_pages_missing(self):
        sections = []
        _flush_section(sections, "S", 1, ["text"], None, None)
        assert sections[0].page_span is None


# =========================================================================
# parse_pdf() async entry point
# =========================================================================


class TestParsePdf:
    @pytest.mark.asyncio
    async def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            await parse_pdf(tmp_path / "nonexistent.pdf")

    @pytest.mark.asyncio
    async def test_calls_converter_and_returns_parsed_doc(self, tmp_path):
        """parse_pdf delegates to _convert_document and _docling_to_parsed."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        mock_doc = FakeDoclingDocument(
            items=[(FakeTitleItem("Test"), 0)],
            pages={0: MagicMock()},
            markdown="# Test",
        )

        with patch("tools.document.pdf_parser._convert_document", return_value=mock_doc):
            result = await parse_pdf(pdf_file)

        assert isinstance(result, ParsedDocument)
        assert result.metadata.title == "Test"
        assert result.metadata.source_format == "pdf"

    @pytest.mark.asyncio
    async def test_parse_time_recorded(self, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        mock_doc = FakeDoclingDocument(items=[], pages={}, markdown="")

        with patch("tools.document.pdf_parser._convert_document", return_value=mock_doc):
            result = await parse_pdf(pdf_file)

        assert result.metadata.parse_time_seconds >= 0
