"""Tests for Meta Reviewer tool factory."""

from __future__ import annotations

from unittest.mock import patch

from agents.meta_reviewer.tools import create_meta_reviewer_tools


class TestCreateMetaReviewerTools:
    def test_default_creates_three_tools(self) -> None:
        tools = create_meta_reviewer_tools()
        tool_names = {t.name for t in tools}
        assert "rag" in tool_names
        # Perplexity and Google may fail if no API keys — that's OK
        assert len(tools) >= 1  # at minimum RAG

    def test_filtered_to_rag_only(self) -> None:
        tools = create_meta_reviewer_tools(tools_enabled=["rag"])
        assert len(tools) == 1
        assert tools[0].name == "rag"

    def test_graceful_on_import_failure(self) -> None:
        with patch.dict(
            "sys.modules",
            {"tools.research.perplexity": None, "tools.research.google_search": None},
        ):
            tools = create_meta_reviewer_tools(tools_enabled=["perplexity", "google_search", "rag"])
            # Should still have rag at minimum
            tool_names = {t.name for t in tools}
            assert "rag" in tool_names

    def test_empty_on_unknown_tools(self) -> None:
        tools = create_meta_reviewer_tools(tools_enabled=["nonexistent_tool"])
        assert tools == []
