"""Shared fixtures for document processing tests.

The fake Docling types and sys.modules patching live in ``mock_docling.py``
(a regular module) to avoid pytest's special conftest loading mechanism,
which creates duplicate class objects and breaks isinstance checks.
"""

from __future__ import annotations

from typing import Any

import pytest

# This import triggers sys.modules patching — must happen before any
# tools.document.* imports so the fake types are in place.
from tests.tools.document.mock_docling import (  # noqa: F401 — side-effect import
    FakeDoclingDocument,
    FakeFormulaItem,
    FakePageItem,
    FakePictureItem,
    FakeProvenanceItem,
    FakeRefItem,
    FakeSectionHeaderItem,
    FakeTableItem,
    FakeTextItem,
    FakeTitleItem,
)


@pytest.fixture
def mock_docling_document() -> FakeDoclingDocument:
    """A realistic mock DoclingDocument simulating an academic paper.

    Structure:
      - Title: "Deep Learning for Climate Prediction"
      - Abstract section with text
      - Introduction section with two paragraphs
      - Methods section (level 1) with a sub-section (level 2)
      - Results section with a table and a figure
      - Conclusion section
      - An equation in the Methods section
      - References section with 3 entries
    """
    prov_p0 = [FakeProvenanceItem(page_no=0)]
    prov_p1 = [FakeProvenanceItem(page_no=1)]
    prov_p2 = [FakeProvenanceItem(page_no=2)]
    prov_p3 = [FakeProvenanceItem(page_no=3)]
    prov_p4 = [FakeProvenanceItem(page_no=4)]

    # Caption items for cross-referencing
    table_caption = FakeTextItem("Table 1: Model performance comparison", prov=prov_p2)
    figure_caption = FakeTextItem("Figure 1: Architecture overview", prov=prov_p3)

    ref_map = {
        "#/texts/table_cap": table_caption,
        "#/texts/fig_cap": figure_caption,
    }

    items: list[tuple[Any, int]] = [
        (FakeTitleItem("Deep Learning for Climate Prediction", prov=prov_p0), 0),
        (FakeSectionHeaderItem("Abstract", level=1, prov=prov_p0), 0),
        (
            FakeTextItem(
                "We present a novel approach to climate prediction using deep learning.",
                prov=prov_p0,
            ),
            1,
        ),
        (FakeSectionHeaderItem("Introduction", level=1, prov=prov_p0), 0),
        (FakeTextItem("Climate change is one of the most pressing challenges.", prov=prov_p0), 1),
        (
            FakeTextItem("Recent advances in deep learning offer new possibilities.", prov=prov_p1),
            1,
        ),
        (FakeSectionHeaderItem("Methods", level=1, prov=prov_p1), 0),
        (FakeTextItem("We use a transformer-based architecture.", prov=prov_p1), 1),
        (FakeFormulaItem("L = \\sum_{i=1}^{N} (y_i - \\hat{y}_i)^2", prov=prov_p1), 1),
        (FakeSectionHeaderItem("Data Preprocessing", level=2, prov=prov_p2), 1),
        (FakeTextItem("Data was sourced from ERA5 reanalysis.", prov=prov_p2), 2),
        (FakeSectionHeaderItem("Results", level=1, prov=prov_p2), 0),
        (FakeTextItem("Our model outperforms baselines on all metrics.", prov=prov_p2), 1),
        (
            FakeTableItem(
                captions=[FakeRefItem(ref="#/texts/table_cap")],
                data="raw table data",
                prov=prov_p2,
                df_data={"Model": ["Ours", "Baseline"], "RMSE": [0.12, 0.45]},
            ),
            1,
        ),
        (FakePictureItem(captions=[FakeRefItem(ref="#/texts/fig_cap")], prov=prov_p3), 1),
        (FakeSectionHeaderItem("Conclusion", level=1, prov=prov_p3), 0),
        (FakeTextItem("We demonstrated the effectiveness of our approach.", prov=prov_p3), 1),
        (FakeSectionHeaderItem("References", level=1, prov=prov_p4), 0),
        (
            FakeTextItem(
                "Smith, J. et al. (2023). Deep learning for weather. Nature, 601.", prov=prov_p4
            ),
            1,
        ),
        (
            FakeTextItem(
                "Chen, W. & Li, H. (2022). Transformer models in climate science. ICML.",
                prov=prov_p4,
            ),
            1,
        ),
        (
            FakeTextItem(
                "Brown, A. (2024). Foundation models for Earth systems. arXiv:2401.12345.",
                prov=prov_p4,
            ),
            1,
        ),
    ]

    return FakeDoclingDocument(
        items=items,
        pages={
            0: FakePageItem(0),
            1: FakePageItem(1),
            2: FakePageItem(2),
            3: FakePageItem(3),
            4: FakePageItem(4),
        },
        markdown="# Deep Learning for Climate Prediction\n\n## Abstract\n\nWe present...",
        ref_map=ref_map,
    )


@pytest.fixture
def empty_docling_document() -> FakeDoclingDocument:
    """A DoclingDocument with no items (empty/corrupt file)."""
    return FakeDoclingDocument(items=[], pages={}, markdown="")
