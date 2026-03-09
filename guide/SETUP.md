# SCRIPTUM Setup Guide

This guide covers all installation methods and configuration options for SCRIPTUM.

## Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | 3.11+ | Required for all install methods |
| Node.js | 20+ | Required for frontend development or npx install |
| Docker | 24+ | Required only for Docker install method |
| Git | 2.30+ | For cloning the repository |

## Installation Methods

### Method 1: pip install (Recommended)

```bash
pip install scriptum-ai
scriptum doctor    # verify installation
scriptum start     # launches backend + frontend at http://localhost:3000
```

### Method 2: npx (Auto-installs)

```bash
npx scriptum-ai@latest
```

This checks for Python 3.11+, creates a virtual environment at `~/.scriptum/venv`, installs the pip package, and starts the server.

### Method 3: Docker Compose (Full Stack)

```bash
git clone https://github.com/DashankaNadeeshanDeSilva/scriptum-agentic-ai-paper-reviewer.git
cd scriptum-agentic-ai-paper-reviewer/scriptum/docker
cp .env.example .env    # edit with your API keys
docker compose up --build
```

Services started:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **PostgreSQL**: localhost:5432
- **ChromaDB**: localhost:8001

### Method 4: Manual Development Setup

```bash
git clone https://github.com/DashankaNadeeshanDeSilva/scriptum-agentic-ai-paper-reviewer.git
cd scriptum-agentic-ai-paper-reviewer/scriptum

# Backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Frontend
cd frontend
npm install

# Start both (in separate terminals)
# Terminal 1: Backend
cd scriptum && uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd scriptum/frontend && npm run dev
```

## Configuration

SCRIPTUM uses a layered configuration system:

```
Environment variables  (highest priority)
       |
~/.scriptum/config.yaml
       |
Built-in defaults      (lowest priority)
```

### Configuration File

On first run, SCRIPTUM creates `~/.scriptum/config.yaml`. You can also copy the template:

```bash
cp scriptum/config/config.yaml ~/.scriptum/config.yaml
```

### Full Configuration Reference

```yaml
# LLM Provider Configuration
llm:
  default_provider: "anthropic"    # anthropic | openai | ollama
  providers:
    anthropic:
      api_key: ""                  # or set ANTHROPIC_API_KEY env var
      default_model: "claude-opus-4-6"
      enabled: true
    openai:
      api_key: ""                  # or set OPENAI_API_KEY env var
      default_model: "gpt-4-turbo"
      enabled: false
      base_url: null               # for OpenAI-compatible APIs
    ollama:
      base_url: "http://localhost:11434"
      default_model: "llama2"
      enabled: false

# Research Tool API Keys
mcp:
  perplexity:
    api_key: ""                    # or set PERPLEXITY_API_KEY env var
    enabled: false
  google_search:
    api_key: ""                    # or set GOOGLE_SEARCH_API_KEY env var
    cx: ""                         # Google Custom Search Engine ID
    enabled: false

# External Research APIs
apis:
  semantic_scholar:
    api_key: ""                    # optional, increases rate limits
  arxiv:
    enabled: true                  # no auth required
  crossref:
    enabled: true                  # no auth required

# Agent Configuration
agents:
  framework: "langgraph"           # langgraph | crewai | smolagents
  max_parallel: 3                  # concurrent reviewer agents
  timeout: 300                     # seconds per agent

# Database
database:
  url: "sqlite+aiosqlite:///~/.scriptum/scriptum.db"
  # Production: postgresql+asyncpg://user:pass@localhost/scriptum

# Document Processing (Docling)
document:
  device: "auto"                   # auto | cpu | cuda | mps
  ocr_enabled: true
  table_mode: "accurate"           # accurate | fast
  thread_count: 4
  max_file_size_mb: 100

# Vector Store (ChromaDB)
vector_store:
  persist_directory: "~/.scriptum/chroma"
  collection_name: "scriptum_knowledge"

# Logging
logging:
  level: "INFO"
  format: "json"
  directory: "~/.scriptum/logs"

# Security
security:
  encryption_key: ""               # auto-generated if not set
```

### Environment Variables Reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `PERPLEXITY_API_KEY` | Perplexity AI key | — |
| `GOOGLE_SEARCH_API_KEY` | Google Custom Search key | — |
| `GOOGLE_SEARCH_CX` | Google Custom Search Engine ID | — |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar key (optional) | — |
| `DATABASE_URL` | Database connection string | SQLite (dev) |
| `CHROMADB_URL` | ChromaDB server URL | — |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:3000` |
| `DOCLING_DEVICE` | Docling compute device | `auto` |
| `DOCLING_THREADS` | Docling processing threads | `4` |

**Docker-specific variables** (set in `docker/.env`):

| Variable | Default |
|----------|---------|
| `BACKEND_PORT` | `8000` |
| `FRONTEND_PORT` | `3000` |
| `POSTGRES_PORT` | `5432` |
| `CHROMADB_PORT` | `8001` |
| `POSTGRES_DB` | `scriptum` |
| `POSTGRES_USER` | `scriptum` |
| `POSTGRES_PASSWORD` | `scriptum` |

## LLM Provider Setup

### Anthropic (Cloud)

1. Get an API key from [console.anthropic.com](https://console.anthropic.com/)
2. Set via environment variable or Settings UI:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Recommended model: `claude-opus-4-6` or `claude-sonnet-4-6`

### OpenAI (Cloud)

1. Get an API key from [platform.openai.com](https://platform.openai.com/)
2. Set via environment variable:
   ```bash
   export OPENAI_API_KEY=sk-...
   ```
3. Recommended model: `gpt-4-turbo`

### Ollama (Local / Privacy-First)

1. Install Ollama: [ollama.com/download](https://ollama.com/download)
2. Pull a model:
   ```bash
   ollama pull llama3.1:8b       # lighter
   ollama pull llama3.1:70b      # more capable
   ```
3. Start Ollama (it runs at `http://localhost:11434` by default)
4. In SCRIPTUM Settings, enable Ollama and select your model
5. No data leaves your machine

## Docling (Document Processing)

Docling runs **in-process** within the Python backend. No separate service or Java runtime is needed.

- On first use, Docling downloads its ML models (~1.5 GB) to `~/.cache/huggingface/`
- Subsequent runs use the cached models
- GPU acceleration: Set `DOCLING_DEVICE=cuda` (NVIDIA) or `DOCLING_DEVICE=mps` (Apple Silicon)
- For CPU-only: `DOCLING_DEVICE=cpu`

## Supported Journals

Pre-configured review criteria for:

| Journal | Config File |
|---------|------------|
| AAAI | `config/journals/aaai.yaml` |
| ACM Computing Surveys | `config/journals/acm.yaml` |
| IEEE TASLP | `config/journals/ieee.yaml` |
| Nature | `config/journals/nature.yaml` |
| NeurIPS | `config/journals/neurips.yaml` |

Custom journals can be added by creating a new YAML file in `config/journals/`.

## Troubleshooting

### `scriptum doctor` reports issues

Run `scriptum doctor` to diagnose problems. It checks:
- Python version (3.11+ required)
- Docker availability
- Docling model availability
- ChromaDB connectivity
- Configuration validity

### Docling models fail to download

If behind a proxy, set:
```bash
export HF_HUB_OFFLINE=0
export HUGGINGFACE_HUB_CACHE=~/.cache/huggingface
```

### ChromaDB connection refused

For pip install: ChromaDB runs in embedded mode (no separate server needed).
For Docker: Ensure the `chromadb` service is running (`docker compose ps`).

### Database migration errors

```bash
cd scriptum
alembic upgrade head
```
