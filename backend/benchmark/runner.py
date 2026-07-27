"""Benchmark mode — runs the fixed prompt suite through the full pipeline
and reports per-agent performance across query types."""
from __future__ import annotations

import json
import time
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table

from benchmark.prompts import BENCHMARK_PROMPTS
from core.schemas import AgentStatus
from pipeline.orchestrator import Orchestrator


async def run_benchmark(orch: Orchestrator, console: Console, output_path: Path | None = None) -> dict:
    console.print(f"[bold]Running benchmark suite[/bold] ({len(BENCHMARK_PROMPTS)} prompts)...\n")

    per_agent: dict[str, dict] = {}
    run_records = []

    for i, case in enumerate(BENCHMARK_PROMPTS, start=1):
        console.print(f"[{i}/{len(BENCHMARK_PROMPTS)}] ({case['query_type']}) {case['prompt']}")
        start = time.perf_counter()
        result = await orch.run(case["prompt"], use_cache=False, record_history=True)
        elapsed = (time.perf_counter() - start) * 1000

        eval_by_agent = {e.agent: e for e in result.evaluations}
        for resp in result.agent_responses:
            stats = per_agent.setdefault(
                resp.agent, {"runs": 0, "successes": 0, "score_sum": 0.0, "latency_sum": 0.0}
            )
            stats["runs"] += 1
            if resp.status == AgentStatus.SUCCESS:
                stats["successes"] += 1
                stats["latency_sum"] += resp.latency_ms or 0.0
                ev = eval_by_agent.get(resp.agent)
                if ev:
                    stats["score_sum"] += ev.overall

        run_records.append(
            {
                "prompt": case["prompt"],
                "query_type": case["query_type"],
                "confidence": result.confidence_score,
                "wall_ms": elapsed,
            }
        )

    table = Table(title="Benchmark Report", box=box.ROUNDED)
    table.add_column("Agent")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Score", justify="right")
    table.add_column("Avg Latency", justify="right")

    report_agents = {}
    for agent, stats in sorted(per_agent.items(), key=lambda kv: -kv[1]["successes"]):
        success_rate = stats["successes"] / stats["runs"] if stats["runs"] else 0
        avg_score = stats["score_sum"] / stats["successes"] if stats["successes"] else None
        avg_latency = stats["latency_sum"] / stats["successes"] if stats["successes"] else None
        table.add_row(
            agent,
            f"{success_rate*100:.0f}%",
            f"{avg_score:.2f}/10" if avg_score is not None else "-",
            f"{avg_latency:.0f}ms" if avg_latency is not None else "-",
        )
        report_agents[agent] = {
            "runs": stats["runs"],
            "successes": stats["successes"],
            "success_rate": success_rate,
            "avg_score": avg_score,
            "avg_latency_ms": avg_latency,
        }

    console.print()
    console.print(table)

    report = {"generated_at": time.time(), "agents": report_agents, "runs": run_records}
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2))
        console.print(f"\n[green]Report written to {output_path}[/green]")

    return report
