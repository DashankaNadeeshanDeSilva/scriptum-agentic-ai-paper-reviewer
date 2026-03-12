"""Tests for document processing data models.

These tests verify the ParsedDocument dataclass and its serialization.
No Docling mocking needed — models.py has no Docling imports.
"""

from scriptum_ai.tools.document.models import (
    DocumentMetadata,
    Equation,
    Figure,
    ParsedDocument,
    Reference,
    Section,
    Table,
)


class TestDocumentMetadata:
    """Tests for the DocumentMetadata dataclass."""

    def test_defaults(self):
        meta = DocumentMetadata()
        assert meta.title == ""
        assert meta.authors == []
        assert meta.abstract == ""
        assert meta.keywords == []
        assert meta.page_count == 0
        assert meta.source_format == ""
        assert meta.parse_time_seconds == 0.0

    def test_custom_values(self):
        meta = DocumentMetadata(
            title="My Paper",
            authors=["Alice", "Bob"],
            abstract="This is the abstract.",
            keywords=["ml", "ai"],
            page_count=12,
            source_format="pdf",
            parse_time_seconds=3.456,
        )
        assert meta.title == "My Paper"
        assert meta.authors == ["Alice", "Bob"]
        assert meta.page_count == 12

    def test_authors_list_independence(self):
        """Each instance gets its own mutable list."""
        m1 = DocumentMetadata()
        m2 = DocumentMetadata()
        m1.authors.append("Alice")
        assert m2.authors == []


class TestSection:
    def test_defaults(self):
        s = Section()
        assert s.heading == ""
        assert s.level == 1
        assert s.text == ""
        assert s.page_span is None

    def test_with_page_span(self):
        s = Section(heading="Methods", level=2, text="Content", page_span=(1, 3))
        assert s.page_span == (1, 3)


class TestTable:
    def test_defaults(self):
        t = Table()
        assert t.caption == ""
        assert t.markdown == ""
        assert t.page is None

    def test_with_values(self):
        t = Table(caption="Table 1", markdown="| a | b |\n|---|---|\n| 1 | 2 |", page=5)
        assert t.caption == "Table 1"
        assert "| a | b |" in t.markdown
        assert t.page == 5


class TestReference:
    def test_defaults(self):
        r = Reference()
        assert r.raw_text == ""
        assert r.resolved is False
        assert r.authors == []

    def test_unresolved(self):
        r = Reference(raw_text="Smith 2020. Some paper.")
        assert r.resolved is False
        assert r.title == ""

    def test_resolved(self):
        r = Reference(
            raw_text="Smith 2020. Some paper.",
            title="Some paper",
            authors=["Smith, J."],
            year="2020",
            doi="10.1234/test",
            resolved=True,
        )
        assert r.resolved is True
        assert r.doi == "10.1234/test"

    def test_authors_list_independence(self):
        r1 = Reference()
        r2 = Reference()
        r1.authors.append("Smith")
        assert r2.authors == []


class TestParsedDocument:
    """Tests for ParsedDocument, focusing on to_dict() serialization."""

    def test_empty_document_defaults(self):
        doc = ParsedDocument()
        assert doc.metadata.title == ""
        assert doc.sections == []
        assert doc.tables == []
        assert doc.figures == []
        assert doc.equations == []
        assert doc.references == []
        assert doc.full_text_markdown == ""

    def test_to_dict_empty(self):
        doc = ParsedDocument()
        d = doc.to_dict()
        assert d["metadata"]["title"] == ""
        assert d["sections"] == []
        assert d["tables"] == []
        assert d["figures"] == []
        assert d["equations"] == []
        assert d["references"] == []
        assert d["full_text_markdown"] == ""

    def test_to_dict_complete(self):
        doc = ParsedDocument(
            metadata=DocumentMetadata(
                title="Test Paper",
                authors=["Alice"],
                abstract="Abstract text",
                page_count=5,
                source_format="pdf",
                parse_time_seconds=2.5,
            ),
            sections=[
                Section(heading="Intro", level=1, text="Hello", page_span=(0, 1)),
                Section(heading="Methods", level=2, text="World"),
            ],
            tables=[Table(caption="T1", markdown="| a |", page=2)],
            figures=[Figure(caption="F1", page=3)],
            equations=[Equation(latex="E=mc^2", context="energy eq", page=4)],
            references=[
                Reference(raw_text="Smith 2020", title="Paper", resolved=True),
            ],
            full_text_markdown="# Test\n\nHello World",
        )
        d = doc.to_dict()

        # Metadata
        assert d["metadata"]["title"] == "Test Paper"
        assert d["metadata"]["authors"] == ["Alice"]
        assert d["metadata"]["page_count"] == 5
        assert d["metadata"]["source_format"] == "pdf"
        assert d["metadata"]["parse_time_seconds"] == 2.5

        # Sections
        assert len(d["sections"]) == 2
        assert d["sections"][0]["heading"] == "Intro"
        assert d["sections"][0]["page_span"] == [0, 1]  # tuple → list
        assert d["sections"][1]["page_span"] is None  # no span

        # Tables
        assert len(d["tables"]) == 1
        assert d["tables"][0]["caption"] == "T1"

        # Figures
        assert len(d["figures"]) == 1
        assert d["figures"][0]["page"] == 3

        # Equations
        assert len(d["equations"]) == 1
        assert d["equations"][0]["latex"] == "E=mc^2"
        assert d["equations"][0]["context"] == "energy eq"

        # References
        assert len(d["references"]) == 1
        assert d["references"][0]["resolved"] is True

        # Markdown
        assert "Hello World" in d["full_text_markdown"]

    def test_to_dict_page_span_conversion(self):
        """page_span tuple is converted to a list for JSON serialization."""
        doc = ParsedDocument(sections=[Section(heading="S", page_span=(2, 5))])
        d = doc.to_dict()
        span = d["sections"][0]["page_span"]
        assert isinstance(span, list)
        assert span == [2, 5]

    def test_to_dict_is_json_serializable(self):
        """Verify the dict contains only JSON-serializable types."""
        import json

        doc = ParsedDocument(
            metadata=DocumentMetadata(title="T", authors=["A"], page_count=1),
            sections=[Section(heading="S", page_span=(0, 0))],
            references=[Reference(raw_text="R", authors=["B"])],
        )
        # This will raise if not serializable
        serialized = json.dumps(doc.to_dict())
        assert '"title": "T"' in serialized

    def test_collections_are_independent(self):
        """Each ParsedDocument gets its own mutable lists."""
        d1 = ParsedDocument()
        d2 = ParsedDocument()
        d1.sections.append(Section(heading="Added"))
        assert d2.sections == []
