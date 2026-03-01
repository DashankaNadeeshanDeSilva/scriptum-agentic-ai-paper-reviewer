# SCRIPTUM

**Smart Critical Review for Iterative Paper Transformation Using Multi-agents**

An open-source, agentic AI system that simulates the academic peer review process. A Meta Reviewer orchestrates 3 specialized reviewer agents (Core Expert, Adjacent Expert, Methods Specialist) to provide comprehensive, journal-specific feedback on research manuscripts.

## Features

- **Multi-Agent Review**: Independent reviewers evaluate novelty, methodology, and clarity
- **Journal-Specific**: Configurable criteria per target journal
- **LLM Flexible**: OpenAI, Anthropic, Ollama via LiteLLM
- **Evidence-Grounded**: Every critique includes citations and paper section references
- **Privacy-First**: Full local deployment with Ollama

## Document Processing

SCRIPTUM uses [Docling](https://github.com/docling-project/docling) (IBM, MIT license) for deep document analysis. Every uploaded paper is automatically processed to extract:

- **Sections & headings** — full hierarchical structure with page locations
- **Tables** — cell-level extraction with 97.9% accuracy (TableFormer)
- **Figures** — captions and page references
- **Equations** — LaTeX representation with surrounding context
- **References** — raw bibliography entries (structured enrichment via LLM in Phase 3)
- **OCR** — scanned PDF support via built-in OCR engine

All processing runs **in-process** within the Python backend — no external services or Java runtime required. Supports PDF and LaTeX input formats. See [Document Processing Guide](Docs/DOCUMENT-PROCESSING.md) for details.

## Architecture

```
Frontend (Next.js) <-> Backend (FastAPI) <-> Agents (LangGraph)
                            |
      ChromaDB + PostgreSQL + Docling + External APIs
```

## Quick Start

```bash
pip install -e ".[dev]"
scriptum --help
scriptum start
```

## Project Structure

```
scriptum/
├── frontend/       # Next.js + Shadcn UI
├── backend/        # FastAPI + SQLAlchemy
├── agents/         # LangGraph agents
├── tools/          # Shared agent tools
├── config/         # Configuration & prompts
├── docker/         # Docker configurations
├── cli/            # CLI entry point
└── tests/          # Test suites
```

## Development

```bash
pip install -e ".[dev]"
pytest                         # run tests
ruff check . && ruff format .  # lint & format
mypy backend/ agents/ tools/   # type check
```

## License

MIT License - see [LICENSE](LICENSE) for details.
