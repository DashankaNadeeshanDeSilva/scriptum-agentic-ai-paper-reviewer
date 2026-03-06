# SCRIPTUM Development Guide

This guide covers the system architecture, how to extend SCRIPTUM, and development workflows.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 16)                        │
│  Dashboard │ Upload │ Progress │ Report │ Chat │ Settings       │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST + WebSocket
┌─────────────────────────┴───────────────────────────────────────┐
│                    Backend (FastAPI)                             │
│  Routers → Services → Orchestrator → Agent System               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              6-Stage Orchestrator Pipeline              │     │
│  │  1. Parse Document (Docling)                           │     │
│  │  2. Desk Check (Meta Reviewer)                         │     │
│  │  3. Research & RAG Setup                               │     │
│  │  4. Independent Review (3 agents in parallel)          │     │
│  │  5. Aggregation (Meta Reviewer)                        │     │
│  │  6. Report Generation & Persistence                    │     │
│  └────────────────────────────────────────────────────────┘     │
└──────┬──────────┬──────────┬──────────┬─────────────────────────┘
       │          │          │          │
   SQLAlchemy  ChromaDB   Docling   LiteLLM
   (SQLite/    (RAG)    (PDF/LaTeX) (LLM Gateway)
    Postgres)
```

## Key Design Principles

1. **Agent Independence** — Reviewer agents never share state during review. Each gets the same paper and tools but works autonomously. State merging happens only at Meta Reviewer aggregation.

2. **Adapter Pattern** — Agent framework is swappable. `AgentInterface` (ABC) defines the contract. `LangGraphAdapter` is the primary implementation, with stubs for CrewAI and SmolAgents.

3. **Config Priority** — Environment variables > `~/.scriptum/config.yaml` > built-in defaults.

4. **Async Everywhere** — All I/O-bound operations use `async/await`. The orchestrator uses `asyncio.gather()` for parallel reviewer execution.

5. **Error Hierarchy** — All domain errors subclass `ScriptumError` for consistent API error responses.

## Project Structure

```
scriptum/
├── backend/
│   ├── api/v1/
│   │   ├── reviews.py       # Review lifecycle CRUD
│   │   ├── files.py          # File upload/download
│   │   ├── settings.py       # Configuration management
│   │   ├── metrics.py        # Observability endpoints
│   │   ├── chat.py           # Post-review chat (REST + WS)
│   │   └── websocket.py      # Review progress streaming
│   ├── core/
│   │   ├── config.py         # AppSettings (Pydantic Settings)
│   │   ├── database.py       # SQLAlchemy async engine & session
│   │   ├── exceptions.py     # ScriptumError hierarchy
│   │   ├── llm.py            # LiteLLM wrapper
│   │   ├── logging.py        # Structured logging (loguru)
│   │   ├── metrics.py        # MetricsCollector singleton
│   │   └── security.py       # API key encryption
│   ├── models/review.py      # 7 SQLAlchemy models
│   ├── schemas/review.py     # Pydantic request/response schemas
│   └── services/
│       ├── orchestrator.py   # 6-stage review pipeline
│       └── document.py       # Document processing service
│
├── agents/
│   ├── core/
│   │   ├── base.py           # AgentInterface ABC + ReviewResult
│   │   ├── factory.py        # Agent registry & creation
│   │   └── adapters/
│   │       ├── langgraph.py  # LangGraph adapter (primary)
│   │       ├── crewai.py     # CrewAI adapter (stub)
│   │       └── smolagents.py # SmolAgents adapter (stub)
│   ├── meta_reviewer/
│   │   ├── agent.py          # MetaReviewerAgent (2 LangGraph graphs)
│   │   ├── prompts.py        # Desk check + aggregation prompts
│   │   └── tools.py          # Meta reviewer-specific tools
│   ├── reviewers/
│   │   ├── base.py           # BaseReviewer (4-node graph template)
│   │   ├── core_expert.py    # Deep domain specialist
│   │   ├── adjacent_expert.py # Cross-disciplinary perspective
│   │   ├── methods_specialist.py # Methodology & statistics
│   │   └── prompts.py        # Reviewer system prompts
│   └── shared_prompts.py     # SCORING_RUBRIC, DEBIASING_INSTRUCTIONS, etc.
│
├── tools/
│   ├── research/
│   │   ├── base.py           # ResearchTool base class
│   │   ├── arxiv_tool.py     # arXiv API
│   │   ├── semantic_scholar.py # S2 Academic Graph API
│   │   ├── perplexity.py     # Perplexity AI search
│   │   ├── google_search.py  # Google Custom Search
│   │   └── crossref.py       # CrossRef metadata
│   ├── document/
│   │   ├── pdf_parser.py     # Docling PDF extraction
│   │   ├── latex_parser.py   # LaTeX processing
│   │   ├── models.py         # ParsedDocument, Section, Table, etc.
│   │   └── reference_resolver.py # Reference enrichment (stub)
│   └── knowledge/
│       ├── rag.py            # ChromaDB RAG operations
│       └── journal_loader.py # Journal config YAML loader
│
├── config/
│   ├── config.yaml           # Default configuration template
│   └── journals/             # Journal-specific review criteria
│       ├── aaai.yaml
│       ├── acm.yaml
│       ├── ieee.yaml
│       ├── nature.yaml
│       └── neurips.yaml
│
├── cli/__main__.py           # Typer CLI entry point
├── frontend/                 # Next.js 16 + Shadcn UI
├── docker/                   # Docker Compose + Dockerfiles
└── tests/                    # pytest + vitest test suites
```

## How to Add a New Reviewer Agent

Reviewers follow a 4-step LangGraph pipeline: **RESEARCH → ANALYZE → EVALUATE → GENERATE**.

### 1. Create the Agent File

Create `agents/reviewers/your_reviewer.py`:

```python
from agents.reviewers.base import BaseReviewer
from agents.reviewers.prompts import YOUR_REVIEWER_SYSTEM_PROMPT

class YourReviewer(BaseReviewer):
    @property
    def reviewer_type(self) -> str:
        return "your_reviewer"

    @property
    def system_prompt(self) -> str:
        return YOUR_REVIEWER_SYSTEM_PROMPT
```

### 2. Add the System Prompt

In `agents/reviewers/prompts.py`:

```python
YOUR_REVIEWER_SYSTEM_PROMPT = """\
You are a specialized reviewer focusing on [your area].
...
{scoring_rubric}
{debiasing_instructions}
{evidence_requirement}
"""
```

The `{scoring_rubric}`, `{debiasing_instructions}`, and `{evidence_requirement}` placeholders are automatically filled from `agents/shared_prompts.py`.

### 3. Register in Factory

In `agents/core/factory.py`, add to the registry:

```python
from agents.reviewers.your_reviewer import YourReviewer

REVIEWER_REGISTRY["your_reviewer"] = YourReviewer
```

### 4. Add to Orchestrator

In `backend/services/orchestrator.py`, add to the reviewer list used in stage 4.

### 5. Write Tests

Create `tests/agents/reviewers/test_your_reviewer.py` following the pattern in existing reviewer tests.

## How to Add a New Research Tool

### 1. Create the Tool

Create `tools/research/your_tool.py`:

```python
from tools.research.base import ResearchTool

class YourTool(ResearchTool):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    async def search(
        self, query: str, max_results: int = 10, **kwargs
    ) -> list[dict]:
        """Search your API and return structured results."""
        # Use httpx for async HTTP calls
        async with httpx.AsyncClient() as client:
            response = await client.get(...)

        return [
            {
                "title": ...,
                "authors": ...,
                "abstract": ...,
                "url": ...,
                "source": "your_tool",
            }
        ]
```

### 2. Add Configuration

In `config/config.yaml`:

```yaml
apis:
  your_tool:
    api_key: ""
    enabled: true
```

### 3. Register with Agents

Add the tool to agent tool lists in the relevant reviewer or meta reviewer.

### 4. Write Tests

Create `tests/tools/research/test_your_tool.py`.

## How to Swap Agent Frameworks

SCRIPTUM uses an adapter pattern defined in `agents/core/base.py`:

```python
class AgentInterface(ABC):
    @abstractmethod
    async def run(self, task: dict) -> ReviewResult: ...

    @abstractmethod
    async def stream(self, task: dict) -> AsyncIterator[dict]: ...
```

To add a new framework:

1. Create `agents/core/adapters/your_framework.py` implementing `AgentInterface`
2. Update `agents/core/factory.py` to use your adapter when `agents.framework` config matches
3. Ensure your adapter produces `ReviewResult` objects with the same structure

## Testing

### Backend Tests

```bash
cd scriptum

# Full suite (excluding docling-dependent tests)
pytest --ignore=tests/backend/services/test_document.py -k "not TestFullPipeline" -v

# With coverage
pytest --ignore=tests/backend/services/test_document.py -k "not TestFullPipeline" --cov=backend --cov=agents --cov=tools --cov-report=term-missing

# Run specific test class
pytest tests/backend/api/test_reviews.py::TestStartReview -v

# Run specific test
pytest -k "test_upload_valid_pdf" -v
```

### Frontend Tests

```bash
cd scriptum/frontend

npm test              # single run
npm run test:watch    # watch mode
```

### Test Structure

```
tests/
├── conftest.py                           # Root fixtures (sample_config)
├── backend/
│   ├── api/
│   │   ├── conftest.py                   # db_session, client, tmp_upload_dir fixtures
│   │   ├── test_files.py                 # File upload endpoint tests
│   │   ├── test_reviews.py               # Review lifecycle tests
│   │   ├── test_error_handling.py        # Exception handler tests
│   │   ├── test_integration.py           # End-to-end workflow tests
│   │   └── test_metrics.py              # Metrics API tests
│   ├── core/
│   │   ├── test_exceptions.py            # Error hierarchy tests
│   │   └── test_metrics.py              # MetricsCollector tests
│   └── services/
│       ├── test_orchestrator.py          # Pipeline stage tests
│       └── test_document.py             # Docling tests (requires docling)
├── agents/
│   ├── meta_reviewer/                    # Desk check + aggregation tests
│   ├── reviewers/                        # Per-reviewer tests
│   └── test_shared_prompts.py           # Shared prompt constant tests
├── tools/
│   ├── research/                         # Per-tool API tests
│   ├── document/                         # Parser tests
│   └── knowledge/                        # RAG tests
├── test_llm.py                          # LLM provider tests
└── test_agent_framework.py              # Framework adapter tests
```

### Key Fixtures

| Fixture | Location | Purpose |
|---------|----------|---------|
| `db_session` | `tests/backend/api/conftest.py` | In-memory SQLite async session |
| `client` | `tests/backend/api/conftest.py` | httpx AsyncClient with DI overrides |
| `tmp_upload_dir` | `tests/backend/api/conftest.py` | Temporary upload directory |
| `mock_llm_response` | `tests/agents/*/conftest.py` | LLM response factory |
| `sample_paper_dict` | `tests/agents/*/conftest.py` | Parsed paper structure |
| `mock_rag_tool` | `tests/agents/*/conftest.py` | Mock ChromaDB RAG tool |

## Code Style

### Python

- **Formatter/Linter**: ruff (line length 100)
- **Type checker**: mypy (strict mode)
- **Import sorting**: isort via ruff

```bash
ruff check .               # lint
ruff format .              # format
ruff check --fix .         # auto-fix
mypy backend/ agents/ tools/ cli/
```

### TypeScript

- **Linter**: ESLint with `next/core-web-vitals` and `next/typescript`
- **Strict mode**: enabled in `tsconfig.json`

```bash
cd frontend
npx eslint .
npx tsc --noEmit
```

## Database

- **Dev**: SQLite via aiosqlite (zero setup)
- **Production**: PostgreSQL via asyncpg
- **Migrations**: Alembic

```bash
# Create a new migration
cd scriptum
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Models

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | User accounts (optional) |
| `Review` | `reviews` | Review sessions with status lifecycle |
| `ReviewerResult` | `reviewer_results` | Individual agent review outputs |
| `File` | `files` | Uploaded documents linked to reviews |
| `Feedback` | `feedback` | User ratings on completed reviews |
| `Metric` | `metrics` | Performance and cost tracking |
| `ChatMessage` | `chat_messages` | Post-review chat history |

### Review Status Lifecycle

```
pending → processing → desk_check → reviewing → aggregating → completed
                                                              → failed
                                                              → cancelled
```

## Error Handling

All domain errors subclass `ScriptumError`:

```
ScriptumError (base, 500)
├── ConfigError (500)
├── ReviewError (400)
│   ├── ReviewNotFoundError (404)
│   └── ReviewStateError (409)
├── AgentError (500)
│   └── AgentTimeoutError (504)
├── DocumentProcessingError (422)
├── LLMError (502)
└── ParsingError (422)
```

Global exception handlers in `backend/main.py` automatically map these to JSON error responses with `request_id` for correlation.
