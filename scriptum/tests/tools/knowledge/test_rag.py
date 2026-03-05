"""Tests for the RAG tool and journal guideline loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import chromadb
import pytest

from tools.knowledge.journal_loader import _yaml_to_text, load_journal_guidelines
from tools.knowledge.rag import (
    DOMAIN_KNOWLEDGE,
    JOURNAL_GUIDELINES,
    RAGTool,
    get_chroma_client,
)


@pytest.fixture
def ephemeral_client():
    """Create an ephemeral (in-memory) ChromaDB client for testing."""
    return chromadb.EphemeralClient()


@pytest.fixture
def rag(ephemeral_client):
    """Create a RAGTool backed by an ephemeral client."""
    return RAGTool(client=ephemeral_client)


# ---------------------------------------------------------------------------
# RAGTool core operations
# ---------------------------------------------------------------------------


class TestRAGToolInterface:
    def test_name(self, rag: RAGTool) -> None:
        assert rag.name == "rag"

    def test_description(self, rag: RAGTool) -> None:
        assert "ChromaDB" in rag.description or "vector" in rag.description.lower()


class TestRAGToolStore:
    @pytest.mark.asyncio
    async def test_store_documents(self, rag: RAGTool, ephemeral_client) -> None:
        await rag.store(
            ["Document one about transformers", "Document two about attention"],
            collection="test_col",
            ids=["doc1", "doc2"],
        )
        col = ephemeral_client.get_collection("test_col")
        assert col.count() == 2

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, rag: RAGTool, ephemeral_client) -> None:
        await rag.store(
            ["Neural network architectures"],
            collection="test_col",
            metadatas=[{"topic": "deep_learning"}],
            ids=["nn1"],
        )
        col = ephemeral_client.get_collection("test_col")
        result = col.get(ids=["nn1"], include=["metadatas"])
        assert result["metadatas"][0]["topic"] == "deep_learning"

    @pytest.mark.asyncio
    async def test_store_empty_list(self, rag: RAGTool) -> None:
        # Should not raise
        await rag.store([], collection="test_col")

    @pytest.mark.asyncio
    async def test_store_auto_generates_ids(self, rag: RAGTool, ephemeral_client) -> None:
        await rag.store(["doc one", "doc two"], collection="auto_ids_col")
        col = ephemeral_client.get_collection("auto_ids_col")
        assert col.count() == 2


class TestRAGToolQuery:
    @pytest.mark.asyncio
    async def test_query_returns_results(self, rag: RAGTool) -> None:
        await rag.store(
            [
                "Attention mechanisms in neural networks",
                "Convolutional neural networks for images",
                "Recurrent networks for sequences",
            ],
            collection="test_query",
            ids=["a1", "a2", "a3"],
        )
        results = await rag.query("attention", collection="test_query", k=2)
        assert len(results) <= 2
        assert all("document" in r for r in results)
        assert all("metadata" in r for r in results)
        assert all("distance" in r for r in results)

    @pytest.mark.asyncio
    async def test_query_empty_question(self, rag: RAGTool) -> None:
        results = await rag.query("", collection="test_col")
        assert results == []

    @pytest.mark.asyncio
    async def test_query_nonexistent_collection(self, rag: RAGTool) -> None:
        results = await rag.query("anything", collection="does_not_exist")
        assert results == []

    @pytest.mark.asyncio
    async def test_query_empty_collection(self, rag: RAGTool) -> None:
        # Create an empty collection
        rag._client.get_or_create_collection("empty_col")
        results = await rag.query("test", collection="empty_col")
        assert results == []

    @pytest.mark.asyncio
    async def test_query_with_where_filter(self, rag: RAGTool) -> None:
        await rag.store(
            ["Deep learning for NLP", "Deep learning for vision"],
            collection="filter_col",
            metadatas=[{"domain": "nlp"}, {"domain": "vision"}],
            ids=["f1", "f2"],
        )
        results = await rag.query(
            "deep learning",
            collection="filter_col",
            k=5,
            where={"domain": "nlp"},
        )
        assert len(results) >= 1
        assert results[0]["metadata"]["domain"] == "nlp"


class TestRAGToolExecute:
    @pytest.mark.asyncio
    async def test_execute_delegates_to_query(self, rag: RAGTool) -> None:
        await rag.store(
            ["Test document for execute"],
            collection=DOMAIN_KNOWLEDGE,
            ids=["exec1"],
        )
        results = await rag.execute(query="test document", collection=DOMAIN_KNOWLEDGE, k=1)
        assert len(results) >= 1


class TestRAGToolDeleteCollection:
    @pytest.mark.asyncio
    async def test_delete_collection(self, rag: RAGTool, ephemeral_client) -> None:
        await rag.store(["will be deleted"], collection="to_delete", ids=["d1"])
        assert ephemeral_client.get_collection("to_delete").count() == 1

        await rag.delete_collection("to_delete")

        # Collection should be gone
        results = await rag.query("anything", collection="to_delete")
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_nonexistent_collection(self, rag: RAGTool) -> None:
        # Should not raise
        await rag.delete_collection("nonexistent")


# ---------------------------------------------------------------------------
# ChromaDB singleton
# ---------------------------------------------------------------------------


class TestGetChromaClient:
    def test_returns_client(self) -> None:
        # Clear any cached client
        get_chroma_client.cache_clear()
        client = get_chroma_client()
        assert client is not None
        # Call again - should return same instance
        client2 = get_chroma_client()
        assert client is client2
        get_chroma_client.cache_clear()


# ---------------------------------------------------------------------------
# Journal guideline loader
# ---------------------------------------------------------------------------


class TestYamlToText:
    def test_converts_full_config(self) -> None:
        data = {
            "name": "Test Journal",
            "scope": "AI research",
            "review_criteria": {
                "quality": {"weight": 0.5, "description": "Technical quality"},
                "novelty": {"weight": 0.5, "description": "Originality"},
            },
            "formatting_rules": {
                "page_limit": 10,
                "double_blind": True,
            },
            "ethics_policy": "Be ethical.",
            "review_timeline": {
                "first_decision": "8 weeks",
            },
        }
        text = _yaml_to_text(data)
        assert "Test Journal" in text
        assert "AI research" in text
        assert "quality" in text
        assert "weight: 0.5" in text
        assert "page_limit" in text
        assert "Be ethical" in text
        assert "8 weeks" in text

    def test_handles_minimal_config(self) -> None:
        data = {"name": "Minimal"}
        text = _yaml_to_text(data)
        assert "Minimal" in text


class TestLoadJournalGuidelines:
    @pytest.mark.asyncio
    async def test_loads_yaml_files(self, rag: RAGTool) -> None:
        count = await load_journal_guidelines(rag)
        # Should load the 5 YAML files we created
        assert count == 5

    @pytest.mark.asyncio
    async def test_stores_in_journal_collection(self, rag: RAGTool) -> None:
        await load_journal_guidelines(rag)
        results = await rag.query("machine learning conference", collection=JOURNAL_GUIDELINES, k=5)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_metadata_contains_journal_name(self, rag: RAGTool) -> None:
        await load_journal_guidelines(rag)
        results = await rag.query("neural information processing", collection=JOURNAL_GUIDELINES, k=1)
        assert len(results) >= 1
        assert "journal_name" in results[0]["metadata"]

    @pytest.mark.asyncio
    async def test_no_journals_dir(self, rag: RAGTool) -> None:
        with patch("tools.knowledge.journal_loader._JOURNALS_DIR", Path("/nonexistent")):
            count = await load_journal_guidelines(rag)
        assert count == 0

    @pytest.mark.asyncio
    async def test_reload_replaces_old_data(self, rag: RAGTool) -> None:
        await load_journal_guidelines(rag)
        first_count = await load_journal_guidelines(rag)
        # Reload should still have the same count (not doubled)
        col = rag._client.get_collection(JOURNAL_GUIDELINES)
        assert col.count() == first_count
