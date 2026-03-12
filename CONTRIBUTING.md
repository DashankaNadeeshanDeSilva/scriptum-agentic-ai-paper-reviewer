# Contributing to SCRIPTUM

Thank you for your interest in contributing to SCRIPTUM! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork and set up the development environment (see [docs/SETUP.md](docs/SETUP.md))
3. Create a feature branch from `dev`:
   ```bash
   git checkout dev
   git checkout -b feature/your-feature-name
   ```

## Branch Strategy

```
main          Stable releases only
 └── dev      Integration branch (PR target)
      └── feature/*    New features
      └── fix/*        Bug fixes
      └── refactor/*   Code improvements
```

- **Never push directly to `main` or `dev`**
- All changes go through pull requests targeting `dev`
- `main` is updated only via release merges from `dev`

## Development Workflow

### 1. Set Up Your Environment

```bash
# Backend
cd scriptum
pip install -e ".[dev]"

# Frontend
cd scriptum/frontend
npm install
```

### 2. Make Your Changes

- Follow the existing code style (enforced by ruff and eslint)
- Write tests for new functionality
- Keep commits focused and use conventional commit messages

### 3. Run Tests & Checks

```bash
# Backend tests
cd scriptum
pytest --ignore=tests/backend/services/test_document.py -k "not TestFullPipeline" -v

# Frontend tests
cd scriptum/frontend
npm test

# Linting
cd scriptum
ruff check .
ruff format --check .

# Type checking
mypy scriptum_ai/
cd frontend && npx tsc --noEmit
```

### 4. Submit a Pull Request

- Target the `dev` branch
- Provide a clear description of what changed and why
- Reference any related issues
- Ensure all CI checks pass

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new research tool for PubMed
fix: resolve WebSocket reconnection on network drop
refactor: simplify orchestrator stage transitions
docs: update API reference for chat endpoints
test: add integration tests for file upload
```

## Code Style

### Python (Backend / Agents / Tools)

- **Formatter/Linter**: ruff (line length 100)
- **Type checking**: mypy (strict mode)
- **Python version**: 3.11+
- **Async by default**: Use `async def` for all I/O-bound operations
- **Pydantic v2**: For all request/response schemas

### TypeScript (Frontend)

- **Framework**: Next.js App Router
- **UI Components**: Shadcn UI (do not create custom components when a Shadcn primitive exists)
- **Strict mode**: TypeScript strict enabled
- **Linter**: ESLint with next/core-web-vitals

## Architecture Guidelines

- **Agent independence**: Reviewer agents must never share state until Meta Reviewer aggregation
- **Adapter pattern**: New agent frameworks should implement the `AgentInterface` ABC in `scriptum_ai/agents/core/base.py`
- **Research tools**: Extend the `ResearchTool` base class with async `search()` method
- **Error handling**: Raise `ScriptumError` subclasses (see `scriptum_ai/backend/core/exceptions.py`)
- **Config resolution**: Environment variables > `~/.scriptum/config.yaml` > built-in defaults

## Adding a New Reviewer Agent

1. Create `scriptum_ai/agents/reviewers/your_reviewer.py` subclassing `BaseReviewer`
2. Define its system prompt in `scriptum_ai/agents/reviewers/prompts.py`
3. Register it in `scriptum_ai/agents/core/factory.py`
4. Add it to the orchestrator's reviewer list in `scriptum_ai/backend/services/orchestrator.py`
5. Write tests in `tests/agents/reviewers/`

## Adding a New Research Tool

1. Create `scriptum_ai/tools/research/your_tool.py` extending `ResearchTool`
2. Implement `async search(query, max_results, **kwargs) -> list[dict]`
3. Add configuration entries in `scriptum_ai/config/config.yaml`
4. Register the tool in agent tool lists
5. Write tests in `tests/tools/research/`

## Reporting Issues

- Use GitHub Issues with a clear title and description
- Include reproduction steps, expected vs actual behavior
- Mention your environment (OS, Python version, Node version)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
