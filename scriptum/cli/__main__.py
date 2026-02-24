"""SCRIPTUM CLI entry point.

Run with: python -m cli or scriptum (after installation)
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="scriptum",
    help="SCRIPTUM - Agentic AI Academic Paper Review System",
    add_completion=False,
)
console = Console()


@app.command()
def start(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run the backend server"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
) -> None:
    """Start the SCRIPTUM backend server."""
    console.print(f"[bold blue]Starting SCRIPTUM server on port {port}...[/bold blue]")
    # TODO: Implement server startup with uvicorn
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def review(
    paper_path: str = typer.Argument(..., help="Path to the paper PDF"),
    journal: str | None = typer.Option(None, "--journal", "-j", help="Target journal"),
    domain: str | None = typer.Option(None, "--domain", "-d", help="Research domain"),
) -> None:
    """Submit a paper for review."""
    console.print(f"[bold green]Submitting paper: {paper_path}[/bold green]")
    # TODO: Implement paper submission
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def init() -> None:
    """Initialize SCRIPTUM configuration."""
    console.print("[bold blue]Initializing SCRIPTUM configuration...[/bold blue]")
    # TODO: Create ~/.scriptum/config.yaml with defaults
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def doctor() -> None:
    """Check system health and dependencies."""
    console.print("[bold blue]Running SCRIPTUM health check...[/bold blue]")
    # TODO: Verify all services are accessible
    console.print("[yellow]Not implemented yet[/yellow]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
