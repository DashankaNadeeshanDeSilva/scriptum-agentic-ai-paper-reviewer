# SCRIPTUM

**Smart Critical Review for Iterative Paper Transformation Using Multi-agents**

An open-source, agentic AI system that simulates the academic peer review process. A Meta Reviewer orchestrates 3 specialized reviewer agents (Core Expert, Adjacent Expert, Methods Specialist) to provide comprehensive, journal-specific feedback on research manuscripts.

## Features

- **Multi-Agent Review**: Independent reviewers evaluate novelty, methodology, and clarity
- **Journal-Specific**: Configurable criteria per target journal
- **LLM Flexible**: OpenAI, Anthropic, Ollama via LiteLLM
- **Evidence-Grounded**: Every critique includes citations and paper section references
- **Privacy-First**: Full local deployment with Ollama

## Architecture

```
Frontend (Next.js) <-> Backend (FastAPI) <-> Agents (LangGraph)
                            |
      ChromaDB + PostgreSQL + GROBID + External APIs
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
