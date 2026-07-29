import { useState, useEffect } from "react";
import { motion, useReducedMotion } from "framer-motion";

function colorFor(score) {
  if (score >= 70) return "var(--status-good)";
  if (score >= 40) return "var(--status-warning)";
  return "var(--status-critical)";
}

// Tick marks at 0/50/100 turn the arc into a read instrument rather than a
// decorative sliver — you can place the number against the scale before you
// even read the digits.
const TICKS = [0, 50, 100];

function polarToXY(cx, cy, r, angleDeg) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/**
 * Animated semicircular gauge visualizing the pipeline's confidence_score.
 *
 * Color bands: green ≥70%, amber 40-69%, red <40% — matches the same
 * thresholds used nowhere else numerically, just visually, so the reader
 * gets an at-a-glance read before looking at the number.
 *
 * @param {Object} props
 * @param {number} [props.score=0] - Confidence percentage, 0-100.
 * @param {number} [props.size=120] - Gauge diameter in pixels.
 * @returns {JSX.Element}
 */
export default function ConfidenceGauge({ score = 0, size = 120 }) {
  const reducedMotion = useReducedMotion();
  const strokeWidth = size * 0.09;
  const radius = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = Math.PI * radius; // semicircle
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - clamped / 100);
  const color = colorFor(clamped);

  // Count up rather than snapping straight to the final number — cheap on
  // reduced motion (one setState, no interval) since it just skips to the end.
  const [displayed, setDisplayed] = useState(reducedMotion ? clamped : 0);
  useEffect(() => {
    if (reducedMotion) {
      setDisplayed(clamped);
      return undefined;
    }
    const start = performance.now();
    const duration = 900;
    let raf;
    const tick = (t) => {
      const p = Math.min(1, (t - start) / duration);
      setDisplayed(clamped * (1 - Math.pow(1 - p, 3))); // ease-out cubic
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clamped, reducedMotion]);

  return (
    <div className="flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size / 2 + strokeWidth} viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}>
        <path
          d={`M ${strokeWidth / 2} ${cy} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${cy}`}
          fill="none"
          stroke="var(--border-strong)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <motion.path
          d={`M ${strokeWidth / 2} ${cy} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={reducedMotion ? false : { strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: reducedMotion ? 0 : 0.9, ease: [0.16, 1, 0.3, 1] }}
        />
        {/* Ticks paint last, as background-colored notches cut into the ring —
            drawing them before the animated arc left them fully painted over
            wherever the arc had progressed past that tick. */}
        {TICKS.map((t) => {
          const angle = 180 + (t / 100) * 180; // 180deg (left) -> 360deg (right)
          const inner = polarToXY(cx, cy, radius - strokeWidth / 2 - 1, angle);
          const outer = polarToXY(cx, cy, radius + strokeWidth / 2 + 1, angle);
          return (
            <line key={t} x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} stroke="var(--surface-2)" strokeWidth={2} />
          );
        })}
      </svg>
      <div className="-mt-6 text-center">
        <div className="numeric text-2xl font-semibold" style={{ color }}>
          {Math.round(displayed)}%
        </div>
        <div className="label mt-0.5" style={{ color: "var(--text-muted)" }}>
          confidence
        </div>
      </div>
    </div>
  );
}
