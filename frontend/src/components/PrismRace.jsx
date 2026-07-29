import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { sortByAgentOrder } from "../api/client";
import { agentColor, agentInitial, agentLabel, STATUS_META, TERMINAL_STATUSES } from "../api/agentMeta";

const AXIS_FLOOR_MS = 800;
const AXIS_HEADROOM = 1.15;

// The only three hues that ever appear outside agent identity. Picked
// deterministically from the winner's position in the fixed agent order, not
// randomly — so a screenshot of the same race is reproducible.
const PRISM_HUES = ["var(--prism-red)", "var(--prism-cyan)", "var(--prism-lime)"];

const TERMINAL_GLYPH = {
  success: "✓", // ✓
  error: "✗", // ✗
  timeout: "⏸", // ⏸
  rate_limited: "⏸",
  disabled: "—", // —
  interrupted: "—",
};

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
 * The signature element: four agents on one shared time axis, rendered as
 * hairline tracks rather than filled bars — chrome stays achromatic, so the
 * only saturated color on screen is each agent's own identity hue.
 *
 * Data flow is identical to the panel this replaces: it renders directly
 * from the agentStates map ChatPage builds up from SSE events, has no
 * knowledge of EventSource itself, and turns `agent_start`'s client-stamped
 * `startedAt` into a live elapsed time via a throttled rAF loop, snapping to
 * the authoritative `latencyMs` the moment a lane resolves.
 *
 * The one moment RGB enters the UI: once every lane is terminal, a 1px
 * prism-hued line fades in and out once across the winning lane (highest
 * `score` among the agents that succeeded). Fires exactly once per mount —
 * there's no winner to show if nothing succeeded, and reduced motion means
 * the pulse never plays at all (lanes still show their terminal glyph).
 *
 * @param {Object} props
 * @param {Object.<string, {status: string, startedAt?: number, latencyMs?: number, score?: number}>} props.agentStates
 * @returns {JSX.Element}
 */
export default function PrismRace({ agentStates }) {
  const reducedMotion = useReducedMotion();
  const [now, setNow] = useState(() => performance.now());
  const rafRef = useRef(null);
  const lastTickRef = useRef(0);
  const axisRef = useRef(AXIS_FLOOR_MS);
  const rootRef = useRef(null);
  const pulseRef = useRef(null);
  const pulsedRef = useRef(false);

  const entries = sortByAgentOrder(
    Object.entries(agentStates).map(([name, s]) => ({ agent: name, ...s })),
    (x) => x.agent
  );
  const total = entries.length;
  const done = entries.filter((e) => TERMINAL_STATUSES.has(e.status)).length;
  const anyRunning = entries.some((e) => e.status === "running");
  const allResolved = total > 0 && done === total;

  useEffect(() => {
    if (!anyRunning) return undefined;
    const stepMs = reducedMotion ? 1000 : 50;
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
    if (e.latencyMs != null) return e.latencyMs;
    if (e.status === "running" && e.startedAt != null) return Math.max(0, now - e.startedAt);
    return 0;
  };

  const observedMax = Math.max(AXIS_FLOOR_MS, ...entries.map(elapsedFor));
  axisRef.current = Math.max(axisRef.current, observedMax * AXIS_HEADROOM);
  const axisMax = axisRef.current;

  const winner = allResolved
    ? entries.reduce(
        (best, e) => (e.status === "success" && (best === null || (e.score ?? -Infinity) > best.score) ? e : best),
        null
      )
    : null;
  const winnerIndex = winner ? entries.findIndex((e) => e.agent === winner.agent) : -1;

  // The pulse is the only animation in this component that isn't driven by
  // elapsed time — gate it on prefers-reduced-motion via gsap.matchMedia so
  // it simply never plays under reduced motion, rather than snapping to a
  // visible end state.
  useGSAP(
    () => {
      if (!winner || pulsedRef.current || !pulseRef.current) return;
      gsap.matchMedia(rootRef.current).add("(prefers-reduced-motion: no-preference)", () => {
        pulsedRef.current = true;
        const tl = gsap.timeline();
        tl.fromTo(pulseRef.current, { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "vivid" }).to(
          pulseRef.current,
          { opacity: 0, duration: 0.7, ease: "vivid" }
        );
        return () => tl.kill();
      });
    },
    { scope: rootRef, dependencies: [allResolved] }
  );

  return (
    <div ref={rootRef} className="flex w-full flex-col">
      {entries.map((e) => {
        const status = e.status;
        const color = agentColor(e.agent);
        const isWaiting = status === "waiting" || status === "disabled";
        const rawPct = axisMax > 0 ? (elapsedFor(e) / axisMax) * 100 : 0;
        const pct = isWaiting ? 0 : Math.min(100, Math.max(rawPct, 2));
        const glyph = TERMINAL_GLYPH[status];
        const glyphColor = status === "success" ? color : (STATUS_META[status] ?? STATUS_META.waiting).color;
        const isWinnerLane = winner && e.agent === winner.agent;

        return (
          <div key={e.agent} className="flex items-center gap-3 py-2">
            <span
              className="w-24 shrink-0 truncate text-2xs uppercase"
              style={{ color: "var(--text-muted)", letterSpacing: "var(--tracking-label)" }}
              title={agentLabel(e.agent)}
            >
              {agentInitial(e.agent)} {agentLabel(e.agent)}
            </span>

            <div className="relative min-w-0 flex-1" style={{ height: 1, background: "var(--border-strong)" }}>
              <div
                className="absolute inset-y-0 left-0"
                style={{
                  width: `${pct}%`,
                  background: color,
                  opacity: status === "success" ? 1 : 0.6,
                  transition: reducedMotion ? "none" : "width var(--dur-2) var(--ease-lane)",
                }}
              />
              {isWinnerLane && (
                <div
                  ref={pulseRef}
                  className="absolute inset-x-0"
                  style={{ top: -1, height: 3, background: PRISM_HUES[winnerIndex % PRISM_HUES.length], opacity: 0 }}
                />
              )}
              {glyph && !isWaiting && (
                <span
                  className="absolute -translate-y-1/2"
                  style={{ left: `calc(${pct}% - 6px)`, top: "50%", color: glyphColor, fontSize: 10, lineHeight: 1 }}
                >
                  {glyph}
                </span>
              )}
            </div>

            <span className="numeric w-14 shrink-0 text-right text-xs" style={{ color: "var(--text-muted)" }}>
              {isWaiting ? "—" : `${Math.round(elapsedFor(e)).toLocaleString()}ms`}
            </span>
          </div>
        );
      })}
    </div>
  );
}
