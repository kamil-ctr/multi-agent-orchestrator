import { AnimatePresence, motion } from "framer-motion";
import AgentCard from "./AgentCard";
import { sortByAgentOrder } from "../api/client";

const TERMINAL = new Set(["success", "error", "timeout", "rate_limited", "disabled"]);

/**
 * Grid of live AgentCard tiles plus an overall "X/N done" progress bar.
 *
 * Renders directly from the agentStates map ChatPage builds up as SSE
 * events arrive — this component has no knowledge of EventSource/fetch
 * itself, it's purely a presentation layer over whatever state it's given.
 *
 * @param {Object} props
 * @param {Object.<string, {status: string, latencyMs?: number, score?: number, error?: string, text?: string, tokenCount?: number}>} props.agentStates
 *   Map of agent name to its current live state, keyed by agent identifier.
 * @returns {JSX.Element}
 */
export default function AgentProgressPanel({ agentStates }) {
  const entries = sortByAgentOrder(
    Object.entries(agentStates).map(([name, s]) => ({ agent: name, ...s })),
    (x) => x.agent
  );
  const total = entries.length;
  const done = entries.filter((e) => TERMINAL.has(e.status)).length;
  const pct = total ? Math.round((done / total) * 100) : 0;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium" style={{ color: "var(--text-primary)" }}>
          Dispatching to {total} agents
        </span>
        <span style={{ color: "var(--text-muted)" }}>
          {done}/{total} done
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: "var(--border-strong)" }}>
        <motion.div
          className="h-full rounded-full bg-blue-500"
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        <AnimatePresence>
          {entries.map((e) => (
            <AgentCard
              key={e.agent}
              name={e.agent}
              status={e.status}
              latencyMs={e.latencyMs}
              score={e.score}
              error={e.error}
              text={e.text}
              tokenCount={e.tokenCount}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
