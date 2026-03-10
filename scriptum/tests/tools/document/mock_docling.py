"""Mock Docling types for unit testing.

This module provides fake Docling type classes and patches ``sys.modules``
so that ``isinstance()`` checks in the production code work correctly.

IMPORTANT: This is a regular module (not conftest.py) to avoid pytest's
special conftest loading mechanism, which would create duplicate class
objects and break isinstance checks.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

# =========================================================================
# Fake Docling type classes (for isinstance checks)
# =========================================================================


@dataclass
class FakeProvenanceItem:
    """Mimics ``docling_core.types.doc.ProvenanceItem``."""

    page_no: int = 0


@dataclass
class FakeRefItem:
    """Mimics ``docling_core.types.doc.RefItem``."""

    ref: str = ""


class FakeNodeItem:
    """Base for all document items."""

    def __init__(
        self,
        *,
        label: str = "paragraph",
        prov: list[FakeProvenanceItem] | None = None,
        children: list[FakeRefItem] | None = None,
    ):
        self.label = label
        self.prov = prov or []
        self.children = children or []


class FakeTextItem(FakeNodeItem):
    """Mimics ``docling_core.types.doc.TextItem``."""

    def __init__(
        self,
        text: str = "",
        *,
        label: str = "paragraph",
        prov: list[FakeProvenanceItem] | None = None,
    ):
        super().__init__(label=label, prov=prov)
        self.text = text
        self.orig = text


class FakeSectionHeaderItem(FakeTextItem):
    """Mimics ``docling_core.types.doc.SectionHeaderItem``."""

    def __init__(
        self,
        text: str = "",
        *,
        level: int = 1,
        prov: list[FakeProvenanceItem] | None = None,
    ):
        super().__init__(text=text, label="section_header", prov=prov)
        self.level = level


class FakeTitleItem(FakeTextItem):
    """Mimics ``docling_core.types.doc.TitleItem``."""

    def __init__(
        self,
        text: str = "",
        *,
        prov: list[FakeProvenanceItem] | None = None,
    ):
        super().__init__(text=text, label="title", prov=prov)


class FakeTableItem(FakeNodeItem):
    """Mimics ``docling_core.types.doc.TableItem``."""

    def __init__(
        self,
        *,
        captions: list[FakeRefItem] | None = None,
        data: Any = None,
        prov: list[FakeProvenanceItem] | None = None,
        df_data: dict[str, list] | None = None,
    ):
        super().__init__(label="table", prov=prov)
        self.captions = captions or []
        self.data = data
        self.references: list[FakeRefItem] = []
        self._df_data = df_data

    def export_to_dataframe(self, doc: Any = None) -> Any:
        """Return a pandas DataFrame with to_markdown()."""
        import pandas as pd

        if self._df_data:
            return pd.DataFrame(self._df_data)
        raise ValueError("No dataframe data")


class FakePictureItem(FakeNodeItem):
    """Mimics ``docling_core.types.doc.PictureItem``."""

    def __init__(
        self,
        *,
        captions: list[FakeRefItem] | None = None,
        prov: list[FakeProvenanceItem] | None = None,
    ):
        super().__init__(label="picture", prov=prov)
        self.captions = captions or []
        self.image = None
        self.annotations: list = []


class FakeFormulaItem(FakeNodeItem):
    """Mimics ``docling_core.types.doc.FormulaItem``."""

    def __init__(
        self,
        formula: str = "",
        *,
        prov: list[FakeProvenanceItem] | None = None,
    ):
        super().__init__(label="formula", prov=prov)
        self.formula = formula


@dataclass
class FakePageItem:
    """Mimics a page entry in DoclingDocument.pages."""

    page_no: int = 0
    size: dict[str, float] = field(default_factory=lambda: {"width": 612, "height": 792})


class FakeDoclingDocument:
    """Mimics ``docling_core.types.doc.DoclingDocument``.

    Constructed from a list of items that ``iterate_items()`` yields.
    """

    def __init__(
        self,
        *,
        items: list[tuple[Any, int]] | None = None,
        pages: dict[int, Any] | None = None,
        markdown: str = "",
        ref_map: dict[str, Any] | None = None,
    ):
        self._items = items or []
        self.pages = pages or {}
        self._markdown = markdown
        self._ref_map = ref_map or {}
        self.texts: list = []
        self.tables: list = []
        self.pictures: list = []
        self.formulas: list = []

    def iterate_items(self, **kwargs: Any):
        """Yield (item, depth) tuples."""
        yield from self._items

    def export_to_markdown(self, **kwargs: Any) -> str:
        return self._markdown

    def get_ref_item(self, ref: Any) -> Any:
        """Resolve a RefItem to the actual item."""
        key = ref.ref if hasattr(ref, "ref") else str(ref)
        return self._ref_map.get(key, MagicMock(text=""))


# =========================================================================
# Patch sys.modules with fake docling packages
# =========================================================================


def _create_mock_docling_modules() -> dict[str, ModuleType]:
    """Build the full mock module tree for docling and docling_core."""
    modules: dict[str, ModuleType] = {}

    def _mod(name: str) -> ModuleType:
        m = ModuleType(name)
        modules[name] = m
        return m

    # --- docling_core ---
    docling_core = _mod("docling_core")
    docling_core_types = _mod("docling_core.types")
    docling_core_types_doc = _mod("docling_core.types.doc")

    docling_core_types_doc.DoclingDocument = FakeDoclingDocument  # type: ignore[attr-defined]
    docling_core_types_doc.TextItem = FakeTextItem  # type: ignore[attr-defined]
    docling_core_types_doc.SectionHeaderItem = FakeSectionHeaderItem  # type: ignore[attr-defined]
    docling_core_types_doc.TableItem = FakeTableItem  # type: ignore[attr-defined]
    docling_core_types_doc.PictureItem = FakePictureItem  # type: ignore[attr-defined]
    docling_core_types_doc.TitleItem = FakeTitleItem  # type: ignore[attr-defined]
    docling_core_types_doc.FormulaItem = FakeFormulaItem  # type: ignore[attr-defined]
    docling_core_types_doc.NodeItem = FakeNodeItem  # type: ignore[attr-defined]
    docling_core_types_doc.RefItem = FakeRefItem  # type: ignore[attr-defined]
    docling_core_types_doc.ProvenanceItem = FakeProvenanceItem  # type: ignore[attr-defined]

    docling_core.types = docling_core_types  # type: ignore[attr-defined]
    docling_core_types.doc = docling_core_types_doc  # type: ignore[attr-defined]

    # --- docling ---
    docling = _mod("docling")
    datamodel = _mod("docling.datamodel")
    base_models = _mod("docling.datamodel.base_models")
    pipeline_options = _mod("docling.datamodel.pipeline_options")
    accelerator_options = _mod("docling.datamodel.accelerator_options")

    class InputFormat:
        PDF = "pdf"
        LATEX = "latex"
        DOCX = "docx"
        HTML = "html"
        IMAGE = "image"

    base_models.InputFormat = InputFormat  # type: ignore[attr-defined]
    base_models.DocumentStream = MagicMock  # type: ignore[attr-defined]

    class TableFormerMode:
        FAST = "fast"
        ACCURATE = "accurate"

    pipeline_options.PdfPipelineOptions = MagicMock  # type: ignore[attr-defined]
    pipeline_options.TableFormerMode = TableFormerMode  # type: ignore[attr-defined]
    pipeline_options.TableStructureOptions = MagicMock  # type: ignore[attr-defined]
    pipeline_options.EasyOcrOptions = MagicMock  # type: ignore[attr-defined]

    class AcceleratorDevice:
        AUTO = "auto"
        CPU = "cpu"
        CUDA = "cuda"
        MPS = "mps"

    accelerator_options.AcceleratorDevice = AcceleratorDevice  # type: ignore[attr-defined]
    accelerator_options.AcceleratorOptions = MagicMock  # type: ignore[attr-defined]

    doc_converter = _mod("docling.document_converter")
    doc_converter.DocumentConverter = MagicMock  # type: ignore[attr-defined]
    doc_converter.PdfFormatOption = MagicMock  # type: ignore[attr-defined]

    docling.datamodel = datamodel  # type: ignore[attr-defined]
    datamodel.base_models = base_models  # type: ignore[attr-defined]
    datamodel.pipeline_options = pipeline_options  # type: ignore[attr-defined]
    datamodel.accelerator_options = accelerator_options  # type: ignore[attr-defined]
    docling.document_converter = doc_converter  # type: ignore[attr-defined]

    return modules


# Install mocks into sys.modules on first import
_mock_modules = _create_mock_docling_modules()
sys.modules.update(_mock_modules)
