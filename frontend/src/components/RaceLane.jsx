import { useState } from "react";
import { motion } from "framer-motion";
import { Check, X, Clock, AlertTriangle, MinusCircle, WifiOff, ChevronDown } from "lucide-react";
import AgentAvatar from "./AgentAvatar";
import { agentColor, agentInk, agentLabel, STATUS_META } from "../api/agentMeta";

const STATUS_ICON = {
  waiting: MinusCircle,
  running: Clock,
  success: Check,
  error: X,
  timeout: AlertTriangle,
  rate_limited: AlertTriangle,
  disabled: MinusCircle,
  interrupted: WifiOff,
};

const FAILED = new Set(["error", "timeout", "rate_limited"]);

// Failure lanes get a diagonal hatch on top of the agent's own mark color —
// identity is never color-alone, so the texture (plus the icon and label
// text) has to carry "this one failed," not the hue.
function fillStyle(status, color) {
  switch (status) {
    case "success":
    case "running":
      return { background: color };
    case "error":
    case "timeout":
    case "rate_limited":
      return {
        background: `repeating-linear-gradient(135deg, ${color} 0 5px, color-mix(in srgb, ${color} 45%, transparent) 5px 9px)`,
      };
    case "interrupted":
      return { background: "var(--text-muted)", opacity: 0.5 };
    default:
      return { background: "transparent" };
  }
}

/**
 * One row of the live race view — an agent's identity, its current status,
 * and a bar whose length is that agent's elapsed (or final) time against the
 * shared axis every other lane is drawn on.
 *
 * @param {Object} props
 * @param {{agent: string, status: string, latencyMs?: number, error?: string, text?: string, tokenCount?: number}} props.entry
 * @param {number} props.elapsedMs - This lane's current position on the axis: running elapsed, frozen elapsed, or final latency.
 * @param {number} props.axisMax - The shared axis length in ms, computed by the parent from every lane.
 * @param {boolean} props.reducedMotion
 * @returns {JSX.Element}
 */
export default function RaceLane({ entry, elapsedMs, axisMax, reducedMotion }) {
  const [open, setOpen] = useState(false);
  const { status } = entry;
  const meta = STATUS_META[status] ?? STATUS_META.waiting;
  const Icon = STATUS_ICON[status] ?? MinusCircle;
  const color = agentColor(entry.agent);
  const isRunning = status === "running";
  const isWaiting = status === "waiting";
  const isFailed = FAILED.has(status);
  const hasText = !!entry.text;

  const rawPct = axisMax > 0 ? (elapsedMs / axisMax) * 100 : 0;
  const pct = isWaiting || status === "disabled" ? 0 : Math.min(100, Math.max(rawPct, 2));

  const timeLabel = isWaiting || status === "disabled" ? "—" : `${Math.round(elapsedMs).toLocaleString()}ms`;

  return (
    <motion.div
      layout="position"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col gap-1.5 rounded-3 border p-2.5"
      style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
    >
      <div className="flex items-center gap-2">
        <AgentAvatar name={entry.agent} size={20} />
        {/* Identity (agent name) never shrinks — it's the one thing that must
            always be legible. Only the status label truncates, and only under
            real space pressure (narrow viewports, "connection lost"-length
            labels); min-w-0 is required here for that truncate to take effect
            inside a flex row. */}
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <span className="shrink-0 text-xs font-medium" style={{ color: agentInk(entry.agent) }}>
            {agentLabel(entry.agent)}
          </span>
          <Icon
            size={12}
            className={isRunning && !reducedMotion ? "shrink-0 animate-pulse-soft" : "shrink-0"}
            style={{ color: meta.color }}
          />
          <span className="truncate text-xs" style={{ color: meta.color }} title={meta.label}>
            {meta.label}
          </span>
        </div>
        {isRunning && entry.tokenCount > 0 && (
          <span className="numeric hidden shrink-0 text-2xs sm:inline" style={{ color: "var(--text-muted)" }}>
            {entry.tokenCount} tok
          </span>
        )}
        {hasText && (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Hide streamed response" : "Show streamed response"}
            aria-expanded={open}
            className="shrink-0"
            style={{ color: "var(--text-muted)" }}
          >
            <ChevronDown size={12} style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
          </button>
        )}
        <span className="numeric shrink-0 text-xs" style={{ color: "var(--text-muted)" }}>
          {timeLabel}
        </span>
      </div>

      <div
        role="progressbar"
        aria-label={`${entry.agent} progress`}
        aria-valuenow={Math.round(elapsedMs)}
        aria-valuemax={Math.round(axisMax)}
        aria-valuemin={0}
        className="relative h-2 w-full overflow-hidden rounded-1"
        style={{
          background: "var(--surface-1)",
          border: `1px solid var(--border)`,
          borderStyle: isWaiting || status === "disabled" ? "dashed" : "solid",
        }}
      >
        <div
          className="h-full"
          style={{
            width: `${pct}%`,
            ...fillStyle(status, color),
            transition: reducedMotion ? "none" : "width var(--dur-2) var(--ease-lane)",
          }}
        />
      </div>

      {isFailed && entry.error && (
        <p className="truncate text-2xs" style={{ color: "var(--text-muted)" }} title={entry.error}>
          {entry.error}
        </p>
      )}

      {open && hasText && (
        <div
          className="max-h-24 overflow-y-auto whitespace-pre-wrap break-words rounded-2 px-2 py-1.5 text-xs leading-snug"
          style={{ background: "var(--surface-1)", color: "var(--text-secondary)" }}
        >
          {entry.text}
          {isRunning && (
            <span className="animate-blink-cursor" style={{ color }}>
              ▍
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}
