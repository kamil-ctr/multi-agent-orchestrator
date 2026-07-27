"""Stage 6 — Output Display. Rich-powered terminal UI: live per-agent
progress while the pipeline runs, then a comparison dashboard."""
from __future__ import annotations

from rich import box
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from core.history import HistoryEntry
from core.schemas import AgentResponse, AgentStatus, PipelineResult
from pipeline.orchestrator import Orchestrator

_STATUS_COLOR = {
    "pending": "yellow",
    "success": "green",
    "timeout": "red",
    "error": "red",
    "rate_limited": "orange3",
    "disabled": "grey50",
}

_STATUS_ICON = {
    "pending": "…",
    "success": "✓",
    "timeout": "⏱",
    "error": "✗",
    "rate_limited": "⚠",
    "disabled": "–",
}


def _agent_table(agent_names: list[str], status: dict[str, str], latencies: dict[str, str]) -> Table:
    table = Table(title="Dispatching to agents...", box=box.ROUNDED, show_lines=False)
    table.add_column("Agent", style="bold")
    table.add_column("Status")
    table.add_column("Latency", justify="right")
    for name in agent_names:
        st = status[name]
        color = _STATUS_COLOR.get(st, "white")
        icon = _STATUS_ICON.get(st, "?")
        table.add_row(name, f"[{color}]{icon} {st}[/{color}]", latencies.get(name, "-"))
    return table


async def run_query_live(
    console: Console, orch: Orchestrator, prompt: str, use_cache: bool = True
) -> PipelineResult:
    agent_names = [a.name for a in orch.agents]
    status = {
        name: ("disabled" if not orch.agents_by_name[name].is_available else "pending")
        for name in agent_names
    }
    latencies: dict[str, str] = {}

    live = Live(_agent_table(agent_names, status, latencies), console=console, refresh_per_second=8)

    def on_result(resp: AgentResponse) -> None:
        status[resp.agent] = resp.status.value
        latencies[resp.agent] = f"{resp.latency_ms:.0f}ms" if resp.latency_ms else "-"
        live.update(_agent_table(agent_names, status, latencies))

    with live:
        result = await orch.run(prompt, use_cache=use_cache, on_agent_result=on_result)

    return result


def _confidence_bar(score: float) -> Text:
    filled = int(score / 5)
    bar = "█" * filled + "░" * (20 - filled)
    color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
    return Text(f"{bar} {score:.1f}%", style=color)


def display_result(console: Console, result: PipelineResult) -> None:
    console.print()
    if result.cached:
        console.print("[dim](served from cache)[/dim]")

    console.print(
        Panel(
            Markdown(result.synthesized_answer),
            title="[bold]Synthesized Best Answer[/bold]",
            subtitle=f"query type: {result.query_type}",
            border_style="cyan",
            box=box.HEAVY,
        )
    )

    console.print(Text("Confidence: ", end=""), _confidence_bar(result.confidence_score))

    if result.attribution:
        attribution_text = " | ".join(f"[bold]{k}[/bold]: {v}" for k, v in result.attribution.items())
        console.print(f"Attribution: {attribution_text}")

    table = Table(title="Comparison Report", box=box.ROUNDED)
    table.add_column("Agent", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Latency", justify="right")
    table.add_column("Status")
    table.add_column("Strengths")
    table.add_column("Weaknesses")

    eval_by_agent = {e.agent: e for e in result.evaluations}
    resp_by_agent = {r.agent: r for r in result.agent_responses}

    ordered_agents = [e.agent for e in result.evaluations] + [
        r.agent for r in result.agent_responses if r.agent not in eval_by_agent
    ]
    for agent in ordered_agents:
        resp = resp_by_agent.get(agent)
        ev = eval_by_agent.get(agent)
        status = resp.status.value if resp else "unknown"
        color = _STATUS_COLOR.get(status, "white")
        latency = f"{resp.latency_ms:.0f}ms" if resp and resp.latency_ms else "-"
        score = f"{ev.overall:.1f}/10" if ev else "-"
        strengths = ev.strengths if ev else (resp.error or "-") if resp else "-"
        weaknesses = ev.weaknesses if ev else "-"
        table.add_row(agent, score, latency, f"[{color}]{status}[/{color}]", strengths, weaknesses)

    console.print(table)
    console.print(
        f"[dim]evaluator: {result.evaluator_used} | total tokens: {result.total_tokens_estimate} | "
        f"est. cost: ${result.estimated_cost_usd:.4f} | wall time: {result.total_latency_ms:.0f}ms[/dim]"
    )


def offer_individual_responses(console: Console, result: PipelineResult) -> None:
    resp_by_agent = {r.agent: r for r in result.agent_responses if r.response_text}
    if not resp_by_agent:
        return
    names = ", ".join(resp_by_agent.keys())
    while True:
        choice = Prompt.ask(
            f"\nView full response from an agent? [{names}] (or Enter to skip)", default=""
        )
        if not choice:
            return
        if choice not in resp_by_agent:
            console.print(f"[red]Unknown agent '{choice}'[/red]")
            continue
        console.print(Panel(Markdown(resp_by_agent[choice].response_text or ""), title=choice, border_style="magenta"))


def display_history(console: Console, entries: list[HistoryEntry]) -> None:
    table = Table(title="Query History", box=box.ROUNDED)
    table.add_column("ID")
    table.add_column("Query")
    table.add_column("Type")
    table.add_column("Confidence", justify="right")
    table.add_column("Latency", justify="right")
    table.add_column("When")
    import datetime

    for e in entries:
        query_preview = e.query if len(e.query) <= 60 else e.query[:57] + "..."
        when = datetime.datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d %H:%M")
        table.add_row(
            str(e.id), query_preview, e.query_type, f"{e.confidence_score:.1f}%",
            f"{e.total_latency_ms:.0f}ms", when,
        )
    console.print(table)


def display_leaderboard(console: Console, rows: list[dict], query_type: str | None) -> None:
    title = f"Agent Leaderboard ({query_type})" if query_type else "Agent Leaderboard (all query types)"
    table = Table(title=title, box=box.ROUNDED)
    table.add_column("Rank")
    table.add_column("Agent", style="bold")
    table.add_column("Avg Score", justify="right")
    table.add_column("Avg Latency", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Total Runs", justify="right")

    for i, row in enumerate(rows, start=1):
        avg_score = f"{row['avg_score']:.2f}/10" if row["avg_score"] is not None else "-"
        avg_latency = f"{row['avg_latency_ms']:.0f}ms" if row["avg_latency_ms"] is not None else "-"
        table.add_row(
            str(i), row["agent"], avg_score, avg_latency,
            f"{row['success_rate']*100:.0f}%", str(row["total_runs"]),
        )
    console.print(table)
