"""Docling DocumentConverter singleton for SCRIPTUM.

Mirrors the ``get_settings()`` caching pattern: a single converter
instance is created on first use and reused for all subsequent calls.

Call ``get_converter.cache_clear()`` if you need to reinitialize
(e.g. after a config change in tests).
"""

from __future__ import annotations

from functools import lru_cache

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from loguru import logger

from scriptum_ai.backend.core.config import get_settings

_DEVICE_MAP: dict[str, AcceleratorDevice] = {
    "auto": AcceleratorDevice.AUTO,
    "cpu": AcceleratorDevice.CPU,
    "cuda": AcceleratorDevice.CUDA,
    "mps": AcceleratorDevice.MPS,
}

_TABLE_MODE_MAP: dict[str, TableFormerMode] = {
    "accurate": TableFormerMode.ACCURATE,
    "fast": TableFormerMode.FAST,
}


@lru_cache(maxsize=1)
def get_converter() -> DocumentConverter:
    """Return a cached Docling ``DocumentConverter`` configured from app settings."""

    doc_cfg = get_settings().document

    device = _DEVICE_MAP.get(doc_cfg.device.lower(), AcceleratorDevice.AUTO)
    table_mode = _TABLE_MODE_MAP.get(doc_cfg.table_mode.lower(), TableFormerMode.ACCURATE)

    pipeline_options = PdfPipelineOptions(
        do_ocr=doc_cfg.ocr_enabled,
        do_table_structure=True,
        do_formula_enrichment=True,
    )
    pipeline_options.table_structure_options.mode = table_mode
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=doc_cfg.thread_count,
        device=device,
    )

    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.LATEX],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        },
    )

    logger.info(
        "Docling converter initialized | device={} | ocr={} | table_mode={} | threads={}",
        doc_cfg.device,
        doc_cfg.ocr_enabled,
        doc_cfg.table_mode,
        doc_cfg.thread_count,
    )

    return converter
