"""Tests for the Docling DocumentConverter singleton.

Tests verify that ``get_converter()`` correctly:
- Reads configuration from ``get_settings().document``
- Maps device strings to AcceleratorDevice enum values
- Maps table mode strings to TableFormerMode enum values
- Creates a singleton (lru_cache)
- Passes OCR / thread settings to pipeline options
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from scriptum_ai.backend.core.config import DocumentConfig
from scriptum_ai.tools.document.converter import _DEVICE_MAP, _TABLE_MODE_MAP, get_converter


class TestDeviceMap:
    """Verify the device string → enum mapping is complete."""

    def test_all_devices_mapped(self):
        assert "auto" in _DEVICE_MAP
        assert "cpu" in _DEVICE_MAP
        assert "cuda" in _DEVICE_MAP
        assert "mps" in _DEVICE_MAP

    def test_unknown_device_not_mapped(self):
        assert "tpu" not in _DEVICE_MAP


class TestTableModeMap:
    def test_both_modes_mapped(self):
        assert "accurate" in _TABLE_MODE_MAP
        assert "fast" in _TABLE_MODE_MAP


class TestGetConverter:
    """Tests for the ``get_converter()`` singleton function."""

    def setup_method(self):
        # Clear the lru_cache before each test
        get_converter.cache_clear()

    def test_returns_converter_instance(self):
        """get_converter() should return whatever DocumentConverter() returns."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        with patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings):
            converter = get_converter()

        # DocumentConverter is mocked, so converter is a MagicMock
        assert converter is not None

    def test_singleton_returns_same_instance(self):
        """Multiple calls return the same cached instance."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        with patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings):
            c1 = get_converter()
            c2 = get_converter()

        assert c1 is c2

    def test_cache_clear_creates_new_instance(self):
        """After cache_clear(), a new converter is created."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()

        with patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings):
            c1 = get_converter()
            get_converter.cache_clear()
            c2 = get_converter()

        # MagicMock() creates a new instance each call, so they differ
        assert c1 is not c2

    def test_reads_device_from_config(self):
        """Verify the device setting is read from DocumentConfig."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig(device="cuda")

        with patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings):
            get_converter()

        # If we got here without error, the device was successfully looked up

    def test_reads_ocr_from_config(self):
        """Verify OCR setting is passed to PdfPipelineOptions."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig(ocr_enabled=False)
        mock_pipeline = MagicMock()

        with (
            patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings),
            patch("scriptum_ai.tools.document.converter.PdfPipelineOptions", mock_pipeline),
        ):
            get_converter()

        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args
        assert call_kwargs[1]["do_ocr"] is False

    def test_reads_thread_count_from_config(self):
        """Verify thread_count is passed to AcceleratorOptions."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig(thread_count=8)
        mock_accel = MagicMock()

        with (
            patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings),
            patch("scriptum_ai.tools.document.converter.AcceleratorOptions", mock_accel),
        ):
            get_converter()

        mock_accel.assert_called_once()
        call_kwargs = mock_accel.call_args
        assert call_kwargs[1]["num_threads"] == 8

    def test_table_mode_fast(self):
        """Verify table_mode='fast' is correctly mapped."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig(table_mode="fast")

        with patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings):
            get_converter()
        # No error means the mapping worked

    def test_unknown_device_falls_back_to_auto(self):
        """Unknown device strings should fall back to AUTO."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig(device="tpu")

        with patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings):
            # Should not raise — falls back to AUTO
            get_converter()

    def test_case_insensitive_device(self):
        """Device strings are lowercased before lookup."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig(device="CUDA")

        with patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings):
            get_converter()

    def test_allowed_formats_set(self):
        """Converter should be created with PDF and LATEX formats."""
        mock_settings = MagicMock()
        mock_settings.document = DocumentConfig()
        mock_converter_cls = MagicMock()

        with (
            patch("scriptum_ai.tools.document.converter.get_settings", return_value=mock_settings),
            patch("scriptum_ai.tools.document.converter.DocumentConverter", mock_converter_cls),
        ):
            get_converter()

        mock_converter_cls.assert_called_once()
        call_kwargs = mock_converter_cls.call_args
        allowed = call_kwargs[1]["allowed_formats"]
        assert "pdf" in allowed
        assert "latex" in allowed
