# SCRIPTUM Release Guide

Step-by-step instructions for publishing a new release of SCRIPTUM.

---

## Prerequisites

- Python 3.11+ with `build` and `twine` installed
- Node.js 20+ with npm
- A [PyPI account](https://pypi.org/account/register/) with an API token
- An [npmjs.com account](https://www.npmjs.com/signup)
- GitHub CLI (`gh`) installed and authenticated

```bash
pip install build twine
```

---

## Pre-Release Checklist

Before tagging a release, verify everything is clean:

```bash
cd scriptum

# 1. Lint and format
ruff check . && ruff format --check .

# 2. Type check
mypy scriptum_ai/ --ignore-missing-imports

# 3. Run tests (408 backend + 28 frontend)
pytest --ignore=tests/backend/services/test_document.py -k "not TestFullPipeline" -q

# 4. Frontend tests
cd frontend && npm test && cd ..

# 5. Build the wheel (without frontend — smoke test)
cp ../README.md README.md
python -m build
```

If any step fails, fix the issue before proceeding.

---

## Step 1: Version Bump

Update the version number in **all three locations**:

| File | Field |
|------|-------|
| `scriptum/pyproject.toml` | `version = "X.Y.Z"` |
| `scriptum/scriptum_ai/backend/main.py` | `version="X.Y.Z"` (in FastAPI constructor) |
| `packages/scriptum-ai-npm/package.json` | `"version": "X.Y.Z"` |

Update `CHANGELOG.md` with the new version and release date.

---

## Step 2: Build Frontend for Bundling (Optional but Recommended)

Building the frontend before the wheel bundles the UI into the pip package,
so `pip install scriptum-ai && scriptum start` serves the full application.

```bash
cd scriptum/frontend
npm ci
NEXT_OUTPUT=export npm run build
# Creates frontend/out/ with static HTML files
cd ..
```

Verify it was created:
```bash
ls frontend/out/index.html
```

---

## Step 3: Build Python Package

```bash
cd scriptum

# Copy README for package metadata
cp ../README.md README.md

# Clean previous builds
rm -rf dist/

# Build wheel and sdist
python -m build
```

This produces:
- `dist/scriptum_ai-X.Y.Z.tar.gz` (source distribution)
- `dist/scriptum_ai-X.Y.Z-py3-none-any.whl` (wheel)

If you built the frontend in Step 2, the wheel will include `scriptum_ai/frontend/out/`.

---

## Step 4: Test the Package Locally

```bash
# Create a fresh virtual environment
python -m venv /tmp/scriptum-release-test
source /tmp/scriptum-release-test/bin/activate

# Install from the built wheel
pip install dist/scriptum_ai-*.whl

# Verify CLI works
scriptum --help
scriptum doctor

# Clean up
deactivate
rm -rf /tmp/scriptum-release-test
```

---

## Step 5: Commit, Tag, and Push

```bash
# Commit all changes
git add -A
git commit -m "release: v0.1.0"

# Merge to main
git checkout main
git merge dev  # or your feature branch

# Tag the release
git tag -a v0.1.0 -m "v0.1.0 — Initial alpha release"

# Push
git push origin main --tags
```

---

## Step 6: Publish to PyPI

### Option A: Upload to TestPyPI first (recommended for first release)

```bash
twine upload --repository testpypi dist/*
```

Test the installation:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ scriptum-ai
scriptum --help
```

### Option B: Upload to production PyPI

```bash
twine upload dist/*
```

When prompted:
- **Username**: `__token__`
- **Password**: your PyPI API token (starts with `pypi-`)

To create an API token: https://pypi.org/manage/account/token/

Alternatively, configure `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE
```

---

## Step 7: Publish NPM Package

```bash
cd packages/scriptum-ai-npm

# Login to npm (first time only)
npm login

# Dry run to verify contents
npm publish --dry-run

# Publish
npm publish

cd ../..
```

---

## Step 8: Create GitHub Release

```bash
gh release create v0.1.0 \
  scriptum/dist/scriptum_ai-*.tar.gz \
  scriptum/dist/scriptum_ai-*.whl \
  --title "v0.1.0 — Initial Alpha Release" \
  --notes "$(cat <<'EOF'
## SCRIPTUM v0.1.0

First public release of SCRIPTUM — an agentic AI system that simulates academic peer review.

### Highlights
- Multi-agent review: Meta Reviewer + 3 specialized reviewer agents
- PDF and LaTeX manuscript support via Docling (IBM)
- 5 research tools: arXiv, Semantic Scholar, Perplexity, Google Search, CrossRef
- RAG knowledge base with ChromaDB
- Real-time WebSocket progress streaming
- Chat with the Meta Reviewer post-review
- Full web UI (Next.js + Shadcn) with PDF export
- CLI: `scriptum start`, `scriptum review`, `scriptum doctor`, `scriptum init`
- LLM flexible: Anthropic, OpenAI, or local Ollama

### Install
```bash
pip install scriptum-ai
scriptum start
```

See the [Setup Guide](guide/SETUP.md) for full configuration instructions.
EOF
)"
```

---

## Step 9: Post-Release Verification

```bash
# Verify pip install from PyPI
pip install scriptum-ai
scriptum --help
scriptum doctor

# Verify npx
npx scriptum-ai@latest doctor
```

---

## Troubleshooting

### Wheel build fails with "Readme file does not exist"
Run `cp ../README.md README.md` from the `scriptum/` directory before building.

### Frontend not included in wheel
Build the frontend first (`cd frontend && NEXT_OUTPUT=export npm run build`), then rebuild the wheel. The custom build hook (`hatch_build.py`) auto-detects `frontend/out/`.

### TestPyPI install fails with dependency errors
TestPyPI doesn't have all dependencies. Use `--extra-index-url https://pypi.org/simple/` to fall back to production PyPI for dependencies.

### `scriptum doctor` shows missing packages after install
All dependencies should be installed automatically. If not, verify `pyproject.toml` lists the missing dependency.
