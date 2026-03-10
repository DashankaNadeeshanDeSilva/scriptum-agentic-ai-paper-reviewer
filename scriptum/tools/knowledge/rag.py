"""ChromaDB RAG (Retrieval-Augmented Generation) tool.

Provides vector-based storage and semantic retrieval for journal guidelines,
domain knowledge, and any other text the agents need at review time.

ChromaDB runs in-process (no external service) with persistent storage
at ``~/.scriptum/chroma/``.  All public methods are async-safe via
``asyncio.to_thread()`` since ChromaDB's Python API is synchronous.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb
from loguru import logger

from agents.core.base import ToolInterface

# ---------------------------------------------------------------------------
# ChromaDB singleton
# ---------------------------------------------------------------------------

_CHROMA_DIR = Path.home() / ".scriptum" / "chroma"

# Well-known collection names
JOURNAL_GUIDELINES = "journal_guidelines"
DOMAIN_KNOWLEDGE = "domain_knowledge"


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.ClientAPI:
    """Return a singleton persistent ChromaDB client.

    Data is stored at ``~/.scriptum/chroma/``.  The ``@lru_cache`` decorator
    ensures only one client is created per process (same pattern as
    ``get_settings()`` and ``get_converter()``).
    """
    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Initializing ChromaDB persistent client at {}", _CHROMA_DIR)
    return chromadb.PersistentClient(path=str(_CHROMA_DIR))


# ---------------------------------------------------------------------------
# RAGTool
# ---------------------------------------------------------------------------


class RAGTool(ToolInterface):
    """Vector store tool backed by ChromaDB.

    Agents use this to:
    * ``query()`` journal guidelines or domain knowledge during review.
    * ``store()`` new knowledge chunks (e.g. from research tools).

    The ``execute()`` method delegates to ``query()`` so agents can call
    this tool uniformly via the ``ToolInterface`` contract.
    """

    def __init__(self, client: chromadb.ClientAPI | None = None) -> None:
        self._client = client or get_chroma_client()

    # -- ToolInterface -------------------------------------------------------

    @property
    def name(self) -> str:
        return "rag"

    @property
    def description(self) -> str:
        return "Retrieve relevant knowledge from the ChromaDB vector store."

    async def execute(self, **kwargs: Any) -> Any:
        """ToolInterface.execute() -- delegates to query()."""
        query = kwargs.pop("query", "")
        collection = kwargs.pop("collection", DOMAIN_KNOWLEDGE)
        k = kwargs.pop("k", 5)
        where = kwargs.pop("where", None)
        return await self.query(query, collection=collection, k=k, where=where)

    # -- Public API ----------------------------------------------------------

    async def store(
        self,
        texts: list[str],
        *,
        collection: str = DOMAIN_KNOWLEDGE,
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """Store text chunks in a ChromaDB collection.

        Args:
            texts: Documents to store.
            collection: Target collection name.
            metadatas: Optional per-document metadata dicts.
            ids: Optional per-document IDs.  If *None*, ChromaDB generates UUIDs.
        """
        if not texts:
            return

        def _store() -> None:
            col = self._client.get_or_create_collection(name=collection)
            # ChromaDB requires IDs; generate if not provided
            doc_ids = ids or [
                f"{collection}_{i}" for i in range(col.count(), col.count() + len(texts))
            ]
            col.add(documents=texts, metadatas=metadatas, ids=doc_ids)

        await asyncio.to_thread(_store)
        logger.debug("Stored {} documents in collection '{}'", len(texts), collection)

    async def query(
        self,
        question: str,
        *,
        collection: str = DOMAIN_KNOWLEDGE,
        k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve the most relevant documents for a question.

        Args:
            question: Natural-language query.
            collection: Collection to search in.
            k: Number of results to return.
            where: Optional ChromaDB ``where`` filter.

        Returns:
            A list of dicts, each containing ``document``, ``metadata``,
            and ``distance`` keys.  Returns ``[]`` on error or if the
            collection does not exist.
        """
        if not question:
            return []

        def _query() -> list[dict[str, Any]]:
            try:
                col = self._client.get_collection(name=collection)
            except Exception:
                logger.warning("Collection '{}' not found", collection)
                return []

            query_kwargs: dict[str, Any] = {
                "query_texts": [question],
                "n_results": min(k, col.count()) if col.count() > 0 else k,
            }
            if where:
                query_kwargs["where"] = where

            if col.count() == 0:
                return []

            results = col.query(**query_kwargs)

            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            return [
                {"document": doc, "metadata": meta, "distance": dist}
                for doc, meta, dist in zip(documents, metadatas, distances, strict=False)
            ]

        try:
            return await asyncio.to_thread(_query)
        except Exception:
            logger.exception("RAG query failed for collection '{}'", collection)
            return []

    async def delete_collection(self, collection: str) -> None:
        """Delete a collection and all its data."""

        def _delete() -> None:
            try:
                self._client.delete_collection(name=collection)
                logger.info("Deleted collection '{}'", collection)
            except Exception:
                logger.warning("Could not delete collection '{}'", collection)

        await asyncio.to_thread(_delete)
