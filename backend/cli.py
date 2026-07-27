"""CLI entrypoint for the Multi-Agent AI Comparison & Synthesis Engine.

    python main.py ask "Explain quicksort"
    python main.py history
    python main.py leaderboard
    python main.py benchmark
    python main.py export 3 --format pdf
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from core.config import load_config
from core.history import HistoryStore
from core.logger import setup_logging
from pipeline.orchestrator import Orchestrator
from ui.cli import display_history, display_leaderboard, display_result, offer_individual_responses, run_query_live
from ui.export import export_markdown, export_pdf

app = typer.Typer(add_completion=False, help="Multi-Agent AI Comparison & Synthesis Engine")
console = Console()


def _orchestrator() -> Orchestrator:
    config = load_config()
    setup_logging(config.log_level)
    return Orchestrator(config)


@app.command()
def ask(
    prompt: str = typer.Argument(None, help="The question to dispatch to all agents"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the response cache"),
    interactive_details: bool = typer.Option(
        True, "--details/--no-details", help="Offer to show individual agent responses after"
    ),
) -> None:
    """Dispatch PROMPT to every enabled agent, evaluate, and synthesize a best answer."""
    if not prompt:
        prompt = typer.prompt("Enter your prompt")

    orch = _orchestrator()
    available = orch.availability()
    if not any(available.values()):
        console.print(
            "[bold red]No agents are available.[/bold red] Add at least one API key to .env "
            "(see .env.example) and try again."
        )
        raise typer.Exit(1)

    result = asyncio.run(run_query_live(console, orch, prompt, use_cache=not no_cache))
    display_result(console, result)
    if interactive_details:
        offer_individual_responses(console, result)


@app.command()
def agents() -> None:
    """List configured agents and whether they're currently available."""
    orch = _orchestrator()
    table = Table(title="Configured Agents")
    table.add_column("Agent")
    table.add_column("Model")
    table.add_column("Available")
    table.add_column("Timeout")
    table.add_column("Max Retries")
    for a in orch.agents:
        available = "[green]yes[/green]" if a.is_available else "[red]no (missing API key)[/red]"
        table.add_row(a.name, a.config.model, available, f"{a.config.timeout_s}s", str(a.config.max_retries))
    console.print(table)


@app.command()
def history(limit: int = typer.Option(20, "--limit", "-n")) -> None:
    """Show recent query history."""
    config = load_config()
    store = HistoryStore(config.data_dir / "history.sqlite")
    entries = store.recent(limit)
    if not entries:
        console.print("[dim]No query history yet.[/dim]")
        return
    display_history(console, entries)


@app.command()
def show(query_id: int) -> None:
    """Re-display the full result of a past query by its history ID."""
    config = load_config()
    store = HistoryStore(config.data_dir / "history.sqlite")
    entry = store.get(query_id)
    if entry is None:
        console.print(f"[red]No history entry with id {query_id}[/red]")
        raise typer.Exit(1)
    display_result(console, entry.result())


@app.command()
def leaderboard(query_type: str = typer.Option(None, "--type", "-t", help="Filter by query type")) -> None:
    """Show the agent performance leaderboard, aggregated from query history."""
    config = load_config()
    store = HistoryStore(config.data_dir / "history.sqlite")
    rows = store.leaderboard(query_type)
    if not rows:
        console.print("[dim]No history yet to build a leaderboard from.[/dim]")
        return
    display_leaderboard(console, rows, query_type)


@app.command()
def export(
    query_id: int,
    format: str = typer.Option("md", "--format", "-f", help="md or pdf"),
    output: str = typer.Option(None, "--output", "-o"),
) -> None:
    """Export a past query's comparison report to Markdown or PDF."""
    config = load_config()
    store = HistoryStore(config.data_dir / "history.sqlite")
    entry = store.get(query_id)
    if entry is None:
        console.print(f"[red]No history entry with id {query_id}[/red]")
        raise typer.Exit(1)

    result = entry.result()
    out_path = Path(output) if output else Path(f"export_{query_id}.{format}")

    if format == "md":
        export_markdown(result, out_path)
    elif format == "pdf":
        try:
            export_pdf(result, out_path)
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
    else:
        console.print(f"[red]Unknown format '{format}', use 'md' or 'pdf'[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Exported to {out_path}[/green]")


@app.command()
def benchmark(
    output: str = typer.Option(None, "--output", "-o", help="Write the benchmark report JSON here"),
) -> None:
    """Run the built-in benchmark suite against all enabled agents."""
    from benchmark.runner import run_benchmark

    orch = _orchestrator()
    asyncio.run(run_benchmark(orch, console, output_path=Path(output) if output else None))


if __name__ == "__main__":
    app()
