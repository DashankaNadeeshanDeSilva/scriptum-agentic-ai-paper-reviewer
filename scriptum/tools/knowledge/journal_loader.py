"""Load journal guideline YAML files into the RAG vector store.

Each YAML file in ``config/journals/`` describes a journal's review
criteria, formatting rules, and scope.  This module converts them to
searchable text documents and stores them in the
``journal_guidelines`` ChromaDB collection so agents can retrieve
relevant guidelines during review.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from tools.knowledge.rag import JOURNAL_GUIDELINES, RAGTool

# Directory containing journal YAML configs (relative to scriptum/)
_JOURNALS_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "journals"


def _yaml_to_text(data: dict[str, Any]) -> str:
    """Convert a journal YAML dict to a searchable text document."""
    parts: list[str] = []

    name = data.get("name", "Unknown Journal")
    parts.append(f"Journal: {name}")

    if scope := data.get("scope", ""):
        parts.append(f"Scope: {scope}")

    if criteria := data.get("review_criteria"):
        parts.append("Review Criteria:")
        for category, details in criteria.items():
            if isinstance(details, dict):
                weight = details.get("weight", "")
                desc = details.get("description", "")
                parts.append(f"  - {category} (weight: {weight}): {desc}")
            else:
                parts.append(f"  - {category}: {details}")

    if rules := data.get("formatting_rules"):
        parts.append("Formatting Rules:")
        for key, value in rules.items():
            parts.append(f"  - {key}: {value}")

    if ethics := data.get("ethics_policy"):
        parts.append(f"Ethics Policy: {ethics}")

    if timeline := data.get("review_timeline"):
        parts.append("Review Timeline:")
        for key, value in timeline.items():
            parts.append(f"  - {key}: {value}")

    return "\n".join(parts)


async def load_journal_guidelines(rag: RAGTool | None = None) -> int:
    """Read all journal YAML files and store them in the RAG tool.

    Args:
        rag: An existing RAGTool instance. If *None*, a new one is created.

    Returns:
        Number of journal configs loaded.
    """
    if rag is None:
        rag = RAGTool()

    if not _JOURNALS_DIR.is_dir():
        logger.warning("Journals directory not found: {}", _JOURNALS_DIR)
        return 0

    yaml_files = sorted(_JOURNALS_DIR.glob("*.yaml"))
    if not yaml_files:
        logger.warning("No YAML files found in {}", _JOURNALS_DIR)
        return 0

    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []

    for path in yaml_files:
        try:
            data = yaml.safe_load(path.read_text())
            if not isinstance(data, dict):
                logger.warning("Skipping invalid YAML: {}", path)
                continue

            text = _yaml_to_text(data)
            journal_name = data.get("name", path.stem)

            texts.append(text)
            metadatas.append(
                {
                    "journal_name": journal_name,
                    "file": path.name,
                }
            )
            ids.append(f"journal_{path.stem}")

        except Exception:
            logger.exception("Failed to load journal config: {}", path)

    if texts:
        # Clear existing guidelines to avoid duplicates on reload
        await rag.delete_collection(JOURNAL_GUIDELINES)
        await rag.store(texts, collection=JOURNAL_GUIDELINES, metadatas=metadatas, ids=ids)
        logger.info("Loaded {} journal guideline(s) into RAG", len(texts))

    return len(texts)
