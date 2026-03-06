# scriptum-ai

**SCRIPTUM** - Smart Critical Review for Iterative Paper Transformation Using Multi-agents

An open-source, agentic AI system that simulates the academic peer review process. A Meta Reviewer orchestrates 3 specialized reviewer agents to provide comprehensive, journal-specific feedback on research manuscripts.

## Quick Start

```bash
npx scriptum-ai@latest
```

This will:
1. Check that Python 3.11+ is installed
2. Create a virtual environment at `~/.scriptum/venv`
3. Install the `scriptum-ai` Python package
4. Start the SCRIPTUM server at http://localhost:3000

## Commands

```bash
npx scriptum-ai start              # Start the server (default)
npx scriptum-ai start --port 9000  # Custom port
npx scriptum-ai doctor             # Check system health
npx scriptum-ai init               # Initialize configuration
npx scriptum-ai review paper.pdf   # Submit a paper for review
```

## Prerequisites

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **pip** — comes with Python

Node.js is only needed for the `npx` launcher itself. All processing happens in Python.

## Alternative Installation

If you prefer to manage the Python environment yourself:

```bash
pip install scriptum-ai
scriptum start
```

Or use Docker:

```bash
git clone https://github.com/DashankaNadeeshanDeSilva/scriptum-agentic-ai-paper-reviewer.git
cd scriptum-agentic-ai-paper-reviewer/scriptum/docker
cp .env.example .env
docker compose up --build
```

## Features

- Multi-agent peer review (Meta Reviewer + 3 specialist agents)
- Journal-specific criteria (AAAI, ACM, IEEE, Nature, NeurIPS)
- LLM flexible (OpenAI, Anthropic, Ollama for full local privacy)
- Evidence-grounded feedback with citations
- Real-time progress via WebSocket
- Post-review chat with the Meta Reviewer

## License

MIT - see [LICENSE](https://github.com/DashankaNadeeshanDeSilva/scriptum-agentic-ai-paper-reviewer/blob/main/LICENSE)
