<p align="center">
  <strong>SCRIPTUM</strong><br>
  <em>Smart Critical Review for Iterative Paper Transformation Using Multi-agents</em>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/node-20%2B-green" alt="Node 20+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="MIT License"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.109%2B-009688" alt="FastAPI"></a>
  <a href="https://nextjs.org/"><img src="https://img.shields.io/badge/Next.js-16-black" alt="Next.js"></a>
  <a href="https://github.com/langchain-ai/langgraph"><img src="https://img.shields.io/badge/LangGraph-agents-purple" alt="LangGraph"></a>
</p>

---

An open-source, agentic AI system that simulates the academic peer review process. A **Meta Reviewer** orchestrates 3 specialized reviewer agents to provide comprehensive, journal-specific feedback on research manuscripts.

<!-- TODO: Replace with actual screenshot -->
<!-- ![SCRIPTUM Dashboard](docs/assets/screenshot.png) -->

## Install

Choose one:

```bash
# Option 1: pip (recommended)
pip install scriptum-ai
scriptum start

# Option 2: npx (auto-installs Python package)
npx scriptum-ai@latest

# Option 3: Docker (full stack)
cd scriptum/docker
cp .env.example .env
docker compose up --build
```

Then open [http://localhost:3000](http://localhost:3000) and configure your LLM provider in the Setup Wizard.

## How It Works

```
                         Upload Paper (PDF / LaTeX)
                                   |
                            Meta Reviewer
                          (Desk Check Gate)
                          /       |       \
                   Core Expert  Adjacent  Methods
                   (Novelty &   Expert    Specialist
                    Depth)      (Breadth  (Rigor &
                                & Clarity) Stats)
                          \       |       /
                            Meta Reviewer
                          (Aggregation)
                                   |
                          Final Review Report
```

1. **Upload** a PDF or LaTeX manuscript and select a target journal
2. **Desk Check** — Meta Reviewer screens for scope and formatting
3. **Independent Review** — 3 specialized agents review in parallel, each with research tools (arXiv, Semantic Scholar, Perplexity, Google Search, CrossRef) and RAG-backed knowledge
4. **Aggregation** — Meta Reviewer synthesizes scores, resolves disagreements, produces a consensus report
5. **Report** — View structured feedback with scores, evidence, and improvement suggestions
6. **Chat** — Discuss the review with the Meta Reviewer in real time

## Features

- **Multi-Agent Peer Review** — 3 independent reviewers + Meta Reviewer aggregation, mimicking real journal review panels
- **Journal-Specific Criteria** — Pre-configured for AAAI, ACM Computing Surveys, IEEE TASLP, Nature, NeurIPS (custom journals supported)
- **LLM Flexible** — OpenAI, Anthropic, or fully local with Ollama via LiteLLM gateway
- **Evidence-Grounded** — Every critique cites specific paper sections and external sources
- **5 Research Tools** — arXiv, Semantic Scholar, Perplexity AI, Google Search, CrossRef for real-time literature validation
- **Deep Document Analysis** — Docling (IBM) extracts sections, tables, figures, equations, references, and OCR from scanned PDFs
- **RAG Knowledge Base** — ChromaDB-backed retrieval from journal guidelines and domain knowledge
- **Real-Time Progress** — WebSocket streaming of review stages with per-agent status
- **Chat with Reviewer** — Post-review conversation with the Meta Reviewer about your paper
- **PDF Export** — Download the full review report as PDF
- **Privacy-First** — Full local deployment possible with Ollama (no data leaves your machine)
- **Swappable Agent Framework** — LangGraph primary, with adapter pattern for CrewAI and SmolAgents

## Architecture

```
scriptum/
├── frontend/          Next.js 16 + Shadcn UI + Tailwind
│   └── src/app/       9 routes: dashboard, upload, progress, report, chat, settings, setup, privacy
├── backend/           FastAPI + SQLAlchemy (async) + Alembic migrations
│   ├── api/v1/        REST endpoints + WebSocket handlers
│   ├── core/          Config, database, logging, metrics, exceptions
│   ├── models/        7 database tables (Review, File, Feedback, ChatMessage, etc.)
│   └── services/      6-stage orchestrator pipeline
├── agents/            LangGraph-based agent system
│   ├── meta_reviewer/ Desk check + aggregation (2 separate graphs)
│   ├── reviewers/     BaseReviewer + 3 specialists (4-node graph each)
│   └── core/          AgentInterface ABC + framework adapters
├── tools/             Shared agent tooling
│   ├── research/      5 external API tools
│   ├── document/      Docling PDF/LaTeX processing
│   └── knowledge/     ChromaDB RAG system
├── config/            YAML configs + journal criteria definitions
├── cli/               Typer CLI (scriptum start/review/init/doctor)
├── docker/            Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
└── tests/             381 backend + 28 frontend tests
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, Shadcn UI, Tailwind CSS, TypeScript |
| Backend | FastAPI, SQLAlchemy (async), Alembic, Pydantic v2 |
| Agents | LangGraph, LangChain, LiteLLM |
| Document Processing | Docling (IBM, MIT license) |
| Vector Store | ChromaDB |
| Database | SQLite (dev) / PostgreSQL (production) |
| Testing | pytest (381 tests), Vitest (28 tests) |

## Documentation

- [Setup Guide](guide/SETUP.md) — Installation, configuration, and environment setup
- [Development Guide](guide/DEVELOPMENT.md) — Architecture, extending agents/tools, testing
- [API Reference](guide/API.md) — REST endpoints, WebSocket protocol, examples
- [Contributing](CONTRIBUTING.md) — How to contribute
- [Changelog](CHANGELOG.md) — Version history

## Quick Development Setup

```bash
# Backend
cd scriptum
pip install -e ".[dev]"
pytest --ignore=tests/backend/services/test_document.py -k "not TestFullPipeline" -v

# Frontend
cd scriptum/frontend
npm install
npm run dev

# Lint & type check
ruff check . && ruff format --check .
cd frontend && npx tsc --noEmit
```

## License

MIT License — see [LICENSE](LICENSE) for details.

Copyright (c) 2026 Dashanka De Silva
