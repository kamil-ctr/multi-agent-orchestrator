"""Export a PipelineResult to Markdown or PDF."""
from __future__ import annotations

import datetime
from pathlib import Path

from core.schemas import PipelineResult


def to_markdown(result: PipelineResult) -> str:
    ts = datetime.datetime.fromtimestamp(result.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Multi-Agent Comparison Report",
        "",
        f"**Query:** {result.query}",
        "",
        f"**Query type:** {result.query_type}  |  **Generated:** {ts}  |  "
        f"**Confidence:** {result.confidence_score:.1f}%  |  **Evaluator:** {result.evaluator_used}",
        "",
        "## Synthesized Best Answer",
        "",
        result.synthesized_answer,
        "",
    ]

    if result.attribution:
        lines.append("**Attribution:**")
        for agent, note in result.attribution.items():
            lines.append(f"- **{agent}**: {note}")
        lines.append("")

    lines.append("## Comparison Table")
    lines.append("")
    lines.append("| Agent | Score | Latency | Status | Strengths | Weaknesses |")
    lines.append("|---|---|---|---|---|---|")

    eval_by_agent = {e.agent: e for e in result.evaluations}
    resp_by_agent = {r.agent: r for r in result.agent_responses}
    ordered_agents = [e.agent for e in result.evaluations] + [
        r.agent for r in result.agent_responses if r.agent not in eval_by_agent
    ]
    for agent in ordered_agents:
        resp = resp_by_agent.get(agent)
        ev = eval_by_agent.get(agent)
        status = resp.status.value if resp else "unknown"
        latency = f"{resp.latency_ms:.0f}ms" if resp and resp.latency_ms else "-"
        score = f"{ev.overall:.1f}/10" if ev else "-"
        strengths = ev.strengths if ev else "-"
        weaknesses = ev.weaknesses if ev else "-"
        lines.append(f"| {agent} | {score} | {latency} | {status} | {strengths} | {weaknesses} |")

    lines.append("")
    lines.append("## Individual Agent Responses")
    lines.append("")
    for agent in ordered_agents:
        resp = resp_by_agent.get(agent)
        if not resp or not resp.response_text:
            continue
        lines.append(f"### {agent}")
        lines.append("")
        lines.append(resp.response_text)
        lines.append("")

    lines.append("---")
    lines.append(
        f"*Total tokens: {result.total_tokens_estimate} | Est. cost: ${result.estimated_cost_usd:.4f} "
        f"| Wall time: {result.total_latency_ms:.0f}ms*"
    )
    return "\n".join(lines)


def export_markdown(result: PipelineResult, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_markdown(result), encoding="utf-8")
    return out_path


def export_pdf(result: PipelineResult, out_path: Path) -> Path:
    """Renders the Markdown report to PDF. Requires the optional `markdown`
    and `xhtml2pdf` packages (see requirements.txt)."""
    try:
        import markdown as md_lib
        from xhtml2pdf import pisa
    except ImportError as e:
        raise RuntimeError(
            "PDF export requires the 'markdown' and 'xhtml2pdf' packages. "
            "Install them with: pip install markdown xhtml2pdf"
        ) from e

    html_body = md_lib.markdown(to_markdown(result), extensions=["tables"])
    html = f"""<html><head><meta charset="utf-8"><style>
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #999; padding: 4px 8px; font-size: 9pt; }}
        h1 {{ font-size: 18pt; }} h2 {{ font-size: 14pt; margin-top: 16pt; }}
        h3 {{ font-size: 12pt; }}
    </style></head><body>{html_body}</body></html>"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        status = pisa.CreatePDF(html, dest=f)
    if status.err:
        raise RuntimeError(f"PDF generation failed with {status.err} error(s)")
    return out_path
