"""SCRIPTUM CLI entry point.

Run with: python -m scriptum_ai.cli or scriptum (after installation)

Commands:
    scriptum start   — Start the SCRIPTUM server (backend + frontend)
    scriptum review  — Submit a paper for CLI-based review
    scriptum init    — Initialize ~/.scriptum/config.yaml
    scriptum doctor  — Check system health and dependencies
"""

import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="scriptum",
    help="SCRIPTUM - Agentic AI Academic Paper Review System",
    add_completion=False,
)
console = Console()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPTUM_HOME = Path.home() / ".scriptum"
CONFIG_PATH = SCRIPTUM_HOME / "config.yaml"
PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # scriptum_ai/
PROJECT_ROOT = PACKAGE_ROOT.parent  # scriptum/ (dev) or site-packages/ (installed)


# ---------------------------------------------------------------------------
# scriptum start
# ---------------------------------------------------------------------------


@app.command()
def start(
    port: int = typer.Option(8000, "--port", "-p", help="Port for the backend server"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev mode)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser on start"),
) -> None:
    """Start the SCRIPTUM server (backend API + frontend UI)."""
    import uvicorn

    _ensure_home_dir()

    frontend_dir = _find_frontend_out()
    if frontend_dir is not None:
        console.print(f"[green]Frontend:[/green] serving static build from {frontend_dir}")
    else:
        console.print(
            "[yellow]Frontend not built.[/yellow] "
            "Run [bold]scriptum build-frontend[/bold] or start the Next.js dev server separately."
        )

    url = f"http://{host}:{port}"
    console.print(
        Panel(
            f"[bold blue]SCRIPTUM[/bold blue] starting at [link={url}]{url}[/link]\n"
            f"API docs: {url}/api/docs\n"
            "Press [bold]Ctrl+C[/bold] to stop.",
            title="SCRIPTUM",
        )
    )

    if not no_browser:
        # Open browser after a short delay to let uvicorn start
        import threading

        def _open_browser() -> None:
            import time

            time.sleep(1.5)
            webbrowser.open(url)

        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(
        "scriptum_ai.backend.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ---------------------------------------------------------------------------
# scriptum review
# ---------------------------------------------------------------------------


@app.command()
def review(
    paper_path: str = typer.Argument(..., help="Path to the paper (PDF or LaTeX)"),
    journal: str = typer.Option("neurips", "--journal", "-j", help="Target journal name"),
    domain: str = typer.Option("machine learning", "--domain", "-d", help="Research domain"),
    provider: str = typer.Option("anthropic", "--provider", help="LLM provider"),
    model: str = typer.Option("claude-sonnet-4-6", "--model", help="LLM model name"),
    server: str = typer.Option(
        "http://localhost:8000", "--server", "-s", help="SCRIPTUM server URL"
    ),
) -> None:
    """Submit a paper for review (requires a running SCRIPTUM server)."""
    import httpx

    paper = Path(paper_path)
    if not paper.exists():
        console.print(f"[red]File not found:[/red] {paper_path}")
        raise typer.Exit(1)

    ext = paper.suffix.lower()
    if ext not in {".pdf", ".tex", ".bib"}:
        console.print(f"[red]Unsupported file type:[/red] {ext}. Use .pdf, .tex, or .bib")
        raise typer.Exit(1)

    base = server.rstrip("/")

    with console.status("Uploading paper..."):
        try:
            with httpx.Client(timeout=60) as client:
                # Step 1: Upload file
                with open(paper, "rb") as f:
                    resp = client.post(
                        f"{base}/api/v1/files/upload",
                        files={"files": (paper.name, f)},
                    )
                resp.raise_for_status()
                file_ids = [item["file_id"] for item in resp.json()]

                # Step 2: Start review
                resp = client.post(
                    f"{base}/api/v1/reviews",
                    json={
                        "file_ids": file_ids,
                        "journal_name": journal,
                        "domain_general": domain,
                        "llm_provider": provider,
                        "llm_model": model,
                    },
                )
                resp.raise_for_status()
                review_data = resp.json()
        except httpx.ConnectError:
            console.print(
                f"[red]Cannot connect to SCRIPTUM server at {base}[/red]\n"
                "Start the server first: [bold]scriptum start[/bold]"
            )
            raise typer.Exit(1) from None
        except httpx.HTTPStatusError as exc:
            console.print(
                f"[red]Server error:[/red] {exc.response.status_code} — {exc.response.text}"
            )
            raise typer.Exit(1) from None

    review_id = review_data.get("review_id") or review_data.get("id")
    console.print(f"[green]Review started![/green] ID: {review_id}")
    console.print(f"Track progress at: {base.replace('http', 'http')}/review/{review_id}")
    console.print(f"Or via API: GET {base}/api/v1/reviews/{review_id}")


# ---------------------------------------------------------------------------
# scriptum init
# ---------------------------------------------------------------------------


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
) -> None:
    """Initialize SCRIPTUM configuration at ~/.scriptum/config.yaml."""
    _ensure_home_dir()

    if CONFIG_PATH.exists() and not force:
        console.print(f"[yellow]Config already exists:[/yellow] {CONFIG_PATH}")
        console.print("Use [bold]--force[/bold] to overwrite.")
        raise typer.Exit(0)

    # Copy the default config template
    template = PACKAGE_ROOT / "config" / "config.yaml"
    if template.exists():
        shutil.copy2(template, CONFIG_PATH)
    else:
        # Inline minimal config if template not found
        CONFIG_PATH.write_text(
            "# SCRIPTUM Configuration\n"
            "# See: https://github.com/DashankaNadeeshanDeSilva/scriptum-agentic-ai-paper-reviewer\n"
            "\n"
            "llm:\n"
            '  default_provider: "anthropic"\n'
            "  providers:\n"
            "    anthropic:\n"
            '      api_key: ""  # or set ANTHROPIC_API_KEY env var\n'
            '      default_model: "claude-sonnet-4-6"\n'
            "      enabled: true\n"
            "    openai:\n"
            '      api_key: ""\n'
            '      default_model: "gpt-4-turbo"\n'
            "      enabled: false\n"
            "    ollama:\n"
            '      base_url: "http://localhost:11434"\n'
            '      default_model: "llama2"\n'
            "      enabled: false\n"
            "\n"
            "agents:\n"
            '  framework: "langgraph"\n'
            "  max_parallel: 3\n"
            "  timeout: 300\n"
        )

    console.print(f"[green]Config created:[/green] {CONFIG_PATH}")
    console.print("Edit it to add your LLM API keys, then run [bold]scriptum start[/bold].")


# ---------------------------------------------------------------------------
# scriptum doctor
# ---------------------------------------------------------------------------


@app.command()
def doctor() -> None:
    """Check system health and dependencies."""
    table = Table(title="SCRIPTUM Health Check", show_lines=True)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    all_ok = True

    # 1. Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 11):  # noqa: UP036
        table.add_row("Python", "[green]OK[/green]", py_ver)
    else:
        table.add_row("Python", "[red]FAIL[/red]", f"{py_ver} (need 3.11+)")
        all_ok = False

    # 2. Node.js (optional, for frontend dev)
    node_ver = _check_command("node", "--version")
    if node_ver:
        table.add_row("Node.js", "[green]OK[/green]", node_ver.strip())
    else:
        table.add_row(
            "Node.js", "[yellow]SKIP[/yellow]", "Not found (optional, needed for frontend dev)"
        )

    # 3. Docker (optional)
    docker_ver = _check_command("docker", "--version")
    if docker_ver:
        table.add_row("Docker", "[green]OK[/green]", docker_ver.strip())
    else:
        table.add_row(
            "Docker", "[yellow]SKIP[/yellow]", "Not found (optional, needed for Docker deploy)"
        )

    # 4. Config file
    if CONFIG_PATH.exists():
        table.add_row("Config", "[green]OK[/green]", str(CONFIG_PATH))
    else:
        table.add_row("Config", "[yellow]MISSING[/yellow]", "Run [bold]scriptum init[/bold]")

    # 5. SCRIPTUM home directory
    if SCRIPTUM_HOME.exists():
        table.add_row("Data directory", "[green]OK[/green]", str(SCRIPTUM_HOME))
    else:
        table.add_row("Data directory", "[yellow]MISSING[/yellow]", "Will be created on first run")

    # 6. Docling availability
    try:
        import docling  # noqa: F401

        table.add_row("Docling", "[green]OK[/green]", "Installed (PDF/LaTeX processing)")
    except ImportError:
        table.add_row("Docling", "[red]MISSING[/red]", "pip install docling")
        all_ok = False

    # 7. ChromaDB
    try:
        import chromadb  # noqa: F401

        table.add_row("ChromaDB", "[green]OK[/green]", "Installed (embedded vector store)")
    except ImportError:
        table.add_row("ChromaDB", "[red]MISSING[/red]", "pip install chromadb")
        all_ok = False

    # 8. LiteLLM
    try:
        import litellm  # noqa: F401

        table.add_row("LiteLLM", "[green]OK[/green]", "Installed (LLM gateway)")
    except ImportError:
        table.add_row("LiteLLM", "[red]MISSING[/red]", "pip install litellm")
        all_ok = False

    # 9. Frontend build
    frontend_dir = _find_frontend_out()
    if frontend_dir is not None:
        table.add_row("Frontend build", "[green]OK[/green]", str(frontend_dir))
    else:
        table.add_row(
            "Frontend build",
            "[yellow]NOT BUILT[/yellow]",
            "Run: cd frontend && NEXT_OUTPUT=export npm run build",
        )

    # 10. API key check
    import os

    has_key = any(os.getenv(k) for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"))
    if has_key:
        table.add_row("LLM API key", "[green]OK[/green]", "Found in environment")
    elif CONFIG_PATH.exists():
        content = CONFIG_PATH.read_text()
        if 'api_key: "sk-' in content or "api_key: sk-" in content:
            table.add_row("LLM API key", "[green]OK[/green]", "Found in config")
        else:
            table.add_row(
                "LLM API key",
                "[yellow]NOT SET[/yellow]",
                "Set via env var or config (Ollama needs no key)",
            )
    else:
        table.add_row(
            "LLM API key",
            "[yellow]NOT SET[/yellow]",
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY (Ollama needs no key)",
        )

    console.print(table)

    if all_ok:
        console.print("\n[bold green]All critical checks passed![/bold green]")
    else:
        console.print("\n[bold yellow]Some checks failed.[/bold yellow] Fix the issues above.")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# scriptum build-frontend
# ---------------------------------------------------------------------------


@app.command(name="build-frontend")
def build_frontend() -> None:
    """Build the Next.js frontend as a static export for single-process serving."""
    frontend_dir = PROJECT_ROOT / "frontend"

    if not (frontend_dir / "package.json").exists():
        console.print(f"[red]Frontend not found at {frontend_dir}[/red]")
        raise typer.Exit(1)

    # Check Node.js
    if not _check_command("node", "--version"):
        console.print("[red]Node.js is required to build the frontend.[/red]")
        raise typer.Exit(1)

    with console.status("Installing frontend dependencies..."):
        result = subprocess.run(
            ["npm", "ci"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]npm ci failed:[/red]\n{result.stderr}")
            raise typer.Exit(1)

    with console.status("Building frontend (static export)..."):
        env = {**subprocess.os.environ, "NEXT_OUTPUT": "export"}
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            console.print(f"[red]Build failed:[/red]\n{result.stderr}")
            raise typer.Exit(1)

    out_dir = frontend_dir / "out"
    if out_dir.is_dir() and (out_dir / "index.html").exists():
        console.print(f"[green]Frontend built successfully![/green] Output: {out_dir}")
    else:
        console.print("[red]Build completed but output directory not found.[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_frontend_out() -> Path | None:
    """Locate the pre-built frontend/out directory.

    Checks inside the installed package first (pip install with bundled frontend),
    then falls back to the project-level frontend directory (development mode).
    """
    for base in (PACKAGE_ROOT, PROJECT_ROOT):
        candidate = base / "frontend" / "out"
        if candidate.is_dir() and (candidate / "index.html").exists():
            return candidate
    return None


def _ensure_home_dir() -> None:
    """Create ~/.scriptum/ if it doesn't exist."""
    SCRIPTUM_HOME.mkdir(parents=True, exist_ok=True)


def _check_command(*cmd: str) -> str | None:
    """Run a command and return its stdout, or None if it fails."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
