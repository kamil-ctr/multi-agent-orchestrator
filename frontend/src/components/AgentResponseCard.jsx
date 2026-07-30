import { useState } from "react";
import { ChevronDown } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { agentColor, agentInitial, agentLabel, STATUS_META } from "../api/agentMeta";

const DIMENSIONS = ["accuracy", "depth", "clarity", "relevance", "conciseness"];

function ScoreBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-20 shrink-0 capitalize" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
      <div className="h-1 flex-1" style={{ background: "var(--surface-2)" }}>
        <div className="h-full" style={{ width: `${((value ?? 0) / 10) * 100}%`, background: color }} />
      </div>
      <span className="numeric w-8 shrink-0 text-right" style={{ color: "var(--text-secondary)" }}>
        {value != null ? value.toFixed(1) : "—"}
      </span>
    </div>
  );
}

/**
 * Collapsible card showing one agent's full response with a per-dimension
 * score breakdown (accuracy/depth/clarity/relevance/conciseness bars).
 *
 * Used in the "Individual Responses" section of ResultsPanel, one per
 * agent that was dispatched (including failed/disabled agents, which
 * render collapsed with just their error message).
 *
 * @param {Object} props
 * @param {Object} props.response - The agent's AgentResponse (agent, status, response_text, latency_ms, model, error).
 * @param {Object} [props.evaluation] - The agent's EvaluationScore, if it succeeded and was scored.
 * @param {boolean} [props.defaultOpen=false] - Whether the card starts expanded.
 * @returns {JSX.Element}
 */
export default function AgentResponseCard({ response, evaluation, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const color = agentColor(response.agent);
  const statusMeta = STATUS_META[response.status] ?? STATUS_META.disabled;
  const hasText = !!response.response_text;

  return (
    <div className="border-t" style={{ borderColor: "var(--border-strong)" }}>
      <button
        onClick={() => hasText && setOpen((o) => !o)}
        className={`flex w-full items-center justify-between gap-3 py-3 text-left ${hasText ? "" : "cursor-default"}`}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xs uppercase" style={{ color, letterSpacing: "var(--tracking-label)" }}>
            {agentInitial(response.agent)} {agentLabel(response.agent)}
          </span>
          <span className="text-xs" style={{ color: statusMeta.color }}>
            {statusMeta.label}
          </span>
          {response.model && (
            <span className="numeric hidden text-xs sm:inline" style={{ color: "var(--text-muted)" }}>
              {response.model}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {evaluation?.overall != null && (
            <span className="numeric text-sm" style={{ color }}>
              {evaluation.overall.toFixed(1)}/10
            </span>
          )}
          {response.latency_ms != null && (
            <span className="numeric text-xs" style={{ color: "var(--text-muted)" }}>
              {Math.round(response.latency_ms)}ms
            </span>
          )}
          {hasText && (
            <ChevronDown
              size={16}
              style={{
                color: "var(--text-muted)",
                transform: open ? "rotate(180deg)" : "none",
                transition: "transform var(--duration-base) var(--ease-vivid)",
              }}
            />
          )}
        </div>
      </button>

      {open && hasText && (
        <div className="pb-4">
          {evaluation?.overall != null && (
            <div className="mb-3 flex flex-col gap-1.5">
              {DIMENSIONS.map((dim) => (
                <ScoreBar key={dim} label={dim} value={evaluation[dim]} color={color} />
              ))}
              <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                {evaluation.strengths} · {evaluation.weaknesses}
              </p>
            </div>
          )}
          <div className="prose prose-sm max-w-none text-base" style={{ color: "var(--text-primary)" }}>
            <ReactMarkdown>{response.response_text}</ReactMarkdown>
          </div>
        </div>
      )}

      {!hasText && response.error && (
        <div className="pb-3 text-xs" style={{ color: "var(--text-muted)" }}>
          {response.error}
        </div>
      )}
    </div>
  );
}
