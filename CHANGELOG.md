# Changelog

All notable changes to SCRIPTUM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-06

### Added

**Multi-Agent Review System**
- Meta Reviewer agent with desk check (scope/formatting gate) and aggregation (consensus synthesis)
- Core Expert agent — deep domain evaluation (novelty, technical depth, significance)
- Adjacent Expert agent — cross-disciplinary perspective (breadth, clarity, impact)
- Methods Specialist agent — rigor evaluation (experimental design, reproducibility, statistics)
- 6-stage orchestrator pipeline with async parallel reviewer execution
- Agent independence protocol — reviewers never share state until aggregation
- Swappable agent framework via adapter pattern (LangGraph primary, CrewAI/SmolAgents adapters)

**Document Processing**
- PDF and LaTeX parsing via Docling (IBM, MIT license)
- Section, table, figure, equation, and reference extraction
- OCR support for scanned PDFs
- In-process execution (no external services required)

**Research Tools**
- arXiv search and paper retrieval
- Semantic Scholar academic graph queries (search, citations, references)
- Perplexity AI-powered search with synthesis
- Google Custom Search integration
- CrossRef DOI and metadata lookup

**Knowledge Base**
- ChromaDB-backed RAG system for journal guidelines and domain knowledge
- Journal configuration files for AAAI, ACM Computing Surveys, IEEE TASLP, Nature, NeurIPS

**Backend API**
- FastAPI REST API with full review lifecycle (upload, start, status, report, feedback)
- WebSocket streaming for real-time review progress
- Settings API with encrypted API key storage
- LLM connection testing endpoint
- Ollama model discovery
- Metrics API (dashboard stats, per-review timings, cost breakdown)
- Chat API for post-review conversation with Meta Reviewer (REST + WebSocket streaming)
- Global exception handling with ScriptumError hierarchy
- Request ID correlation and structured JSON logging

**Frontend**
- Next.js 16 with Shadcn UI component library
- Dashboard with review history and metrics widget
- Drag-and-drop file upload with validation
- Real-time review progress page with WebSocket updates
- Structured review report display with PDF export
- Chat interface with Meta Reviewer (streaming responses)
- Settings page with connection testing and Ollama model discovery
- First-time setup wizard
- Privacy policy page
- React ErrorBoundary for graceful error handling
- YAML settings export/import

**Infrastructure**
- Docker Compose stack (backend, frontend, PostgreSQL, ChromaDB)
- SQLite for development, PostgreSQL for production
- Alembic database migrations
- Typer CLI skeleton (start, review, init, doctor commands)
- Configurable CORS origins

**Testing**
- 381 backend tests (pytest, async)
- 28 frontend tests (Vitest, Testing Library)
- Integration tests covering full review lifecycle

**Observability**
- MetricsCollector with stage timing instrumentation
- Shared prompt constants (scoring rubric, debiasing instructions, evidence requirements)
- Structured logging with loguru
