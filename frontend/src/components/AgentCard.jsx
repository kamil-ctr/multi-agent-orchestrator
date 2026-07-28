import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Check, X, Clock, AlertTriangle, MinusCircle } from "lucide-react";
import AgentAvatar from "./AgentAvatar";
import { agentColor, agentLabel, STATUS_META } from "../api/agentMeta";

const FAILED_STATUSES = new Set(["error", "timeout", "rate_limited"]);

const STATUS_ICON = {
  waiting: MinusCircle,
  running: Clock,
  success: Check,
  error: X,
  timeout: AlertTriangle,
  rate_limited: AlertTriangle,
  disabled: MinusCircle,
};

/**
 * Live status card for one agent in the dispatch progress panel.
 *
 * Animates in via Framer Motion, shows a status icon/label driven by SSE
 * events (waiting → running → success/error/timeout/rate_limited/disabled),
 * a latency badge, and — once resolved successfully — a provisional score
 * bar. See AgentProgressPanel for how these are laid out as a grid.
 *
 * @param {Object} props
 * @param {string} props.name - Agent identifier (e.g. "gemini").
 * @param {string} [props.status="waiting"] - One of the AgentStatus values from STATUS_META.
 * @param {number} [props.latencyMs] - Response latency in milliseconds, once known.
 * @param {number} [props.score] - Provisional heuristic score (0-10), shown only on success.
 * @param {string} [props.error] - Error message, shown for error/timeout/rate_limited states.
 * @param {string} [props.text] - Text streamed so far (agent_token events); shown live while running,
 *   and left visible (dimmed) if the agent fails mid-stream instead of disappearing.
 * @param {number} [props.tokenCount] - Number of agent_token chunks received so far.
 * @returns {JSX.Element}
 */
export default function AgentCard({ name, status = "waiting", latencyMs, score, error, text, tokenCount }) {
  const meta = STATUS_META[status] ?? STATUS_META.waiting;
  const Icon = STATUS_ICON[status] ?? MinusCircle;
  const color = agentColor(name);
  const isRunning = status === "running";
  const isFailed = FAILED_STATUSES.has(status);
  const showStreamedText = !!text && (isRunning || isFailed);
  const textRef = useRef(null);

  useEffect(() => {
    if (textRef.current) {
      textRef.current.scrollTop = textRef.current.scrollHeight;
    }
  }, [text]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="flex flex-col gap-2 rounded-xl border p-3"
      style={{
        background: "var(--surface-2)",
        borderColor: status === "success" ? color : "var(--border)",
        borderWidth: status === "success" ? 1.5 : 1,
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <AgentAvatar name={name} size={26} showLabel />
        <div className={isRunning ? "animate-pulse-soft" : ""} style={{ color: meta.color }}>
          <Icon size={16} />
        </div>
      </div>

      <div className="flex items-center justify-between text-xs" style={{ color: "var(--text-muted)" }}>
        <span style={{ color: meta.color }}>{meta.label}</span>
        {isRunning && tokenCount > 0 ? (
          <span className="tabular-nums">{tokenCount} tok</span>
        ) : (
          latencyMs != null && <span>{Math.round(latencyMs)}ms</span>
        )}
      </div>

      {showStreamedText && (
        <div
          ref={textRef}
          className="max-h-16 overflow-y-auto whitespace-pre-wrap break-words rounded-md px-2 py-1.5 text-xs leading-snug"
          style={{ background: "var(--surface-1)", color: "var(--text-secondary)", opacity: isFailed ? 0.7 : 1 }}
        >
          {text}
          {isRunning && (
            <span className="animate-blink-cursor" style={{ color }}>
              ▍
            </span>
          )}
        </div>
      )}

      {status === "success" && score != null && (
        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: "var(--border-strong)" }}>
            <motion.div
              className="h-full rounded-full"
              style={{ background: color }}
              initial={{ width: 0 }}
              animate={{ width: `${(score / 10) * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <span className="text-xs font-semibold tabular-nums" style={{ color: "var(--text-secondary)" }}>
            {score.toFixed(1)}
          </span>
        </div>
      )}

      {error && (status === "error" || status === "timeout" || status === "rate_limited") && (
        <p className="truncate text-xs" style={{ color: "var(--text-muted)" }} title={error}>
          {error}
        </p>
      )}
    </motion.div>
  );
}

export function agentDisplayName(name) {
  return agentLabel(name);
}
