import { useEffect, useRef, useState } from "react";
import RaceLane from "./RaceLane";
import { sortByAgentOrder } from "../api/client";
import { TERMINAL_STATUSES } from "../api/agentMeta";

const AXIS_FLOOR_MS = 800;
const AXIS_HEADROOM = 1.15;

function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

/**
 * Live race view: every dispatched agent on one shared time axis, so the gap
 * between agents — not just each one's own progress — is the thing you read
 * at a glance.
 *
 * Renders directly from the agentStates map ChatPage builds up as SSE events
 * arrive — this component has no knowledge of EventSource/fetch itself, it's
 * purely a presentation layer over whatever state it's given. `agent_start`
 * carries no timestamp from the server, so ChatPage stamps `startedAt` with
 * `performance.now()` client-side when it arrives; this component turns that
 * into a live elapsed time via a throttled rAF loop, then snaps to the
 * authoritative `latencyMs` the moment a lane resolves.
 *
 * Degrades in place: once every lane is terminal (including the
 * client-synthesized "interrupted" status ChatPage applies on stream drop),
 * the ticker stops itself and the bars simply stay where they are — nothing
 * here spins forever waiting for events that already stopped coming.
 *
 * @param {Object} props
 * @param {Object.<string, {status: string, startedAt?: number, latencyMs?: number, score?: number, error?: string, text?: string, tokenCount?: number}>} props.agentStates
 *   Map of agent name to its current live state, keyed by agent identifier.
 * @returns {JSX.Element}
 */
export default function AgentProgressPanel({ agentStates }) {
  const reducedMotion = useReducedMotion();
  const [now, setNow] = useState(() => performance.now());
  const rafRef = useRef(null);
  const lastTickRef = useRef(0);
  const axisRef = useRef(AXIS_FLOOR_MS);

  const entries = sortByAgentOrder(
    Object.entries(agentStates).map(([name, s]) => ({ agent: name, ...s })),
    (x) => x.agent
  );
  const total = entries.length;
  const done = entries.filter((e) => TERMINAL_STATUSES.has(e.status)).length;
  const anyRunning = entries.some((e) => e.status === "running");
  const anyStarted = entries.some((e) => e.status !== "waiting");

  useEffect(() => {
    if (!anyRunning) return undefined;
    const stepMs = reducedMotion ? 1000 : 50; // 20fps — plenty for a linear bar, cheap to re-render
    const tick = (t) => {
      if (t - lastTickRef.current >= stepMs) {
        lastTickRef.current = t;
        setNow(performance.now());
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [anyRunning, reducedMotion]);

  const elapsedFor = (e) => {
    if (e.latencyMs != null) return e.latencyMs; // authoritative, from the server (or frozen at disconnect)
    if (e.status === "running" && e.startedAt != null) return Math.max(0, now - e.startedAt);
    return 0;
  };

  // The axis only grows, never shrinks — a slower sibling extending it mid-race
  // is correct (everyone's bar is relative to total elapsed time), but a
  // shrinking axis would make a finished lane's bar visibly retreat.
  const observedMax = Math.max(AXIS_FLOOR_MS, ...entries.map(elapsedFor));
  axisRef.current = Math.max(axisRef.current, observedMax * AXIS_HEADROOM);
  const axisMax = axisRef.current;
  const totalElapsed = Math.max(0, ...entries.map(elapsedFor));

  const headerLabel = anyRunning
    ? `Dispatching to ${total} agents`
    : !anyStarted
      ? `${total} agents queued`
      : `Stopped — ${done}/${total} resolved`;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="label">{headerLabel}</span>
        <div className="flex items-center gap-3">
          <span className="numeric text-xs" style={{ color: "var(--text-muted)" }}>
            {(totalElapsed / 1000).toFixed(1)}s
          </span>
          <span className="numeric text-xs" style={{ color: "var(--text-muted)" }}>
            {done}/{total}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {entries.map((e) => (
          <RaceLane key={e.agent} entry={e} elapsedMs={elapsedFor(e)} axisMax={axisMax} reducedMotion={reducedMotion} />
        ))}
      </div>
    </div>
  );
}
