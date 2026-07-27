import { motion } from "framer-motion";

function colorFor(score) {
  if (score >= 70) return "var(--status-good)";
  if (score >= 40) return "var(--status-warning)";
  return "var(--status-critical)";
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
  const strokeWidth = size * 0.1;
  const radius = (size - strokeWidth) / 2;
  const circumference = Math.PI * radius; // semicircle
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - clamped / 100);
  const color = colorFor(clamped);

  return (
    <div className="flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size / 2 + strokeWidth / 2} viewBox={`0 0 ${size} ${size / 2 + strokeWidth / 2}`}>
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke="var(--border-strong)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <motion.path
          d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        />
      </svg>
      <div className="-mt-6 text-center">
        <div className="text-2xl font-bold tabular-nums" style={{ color }}>
          {clamped.toFixed(0)}%
        </div>
        <div className="text-xs" style={{ color: "var(--text-muted)" }}>
          confidence
        </div>
      </div>
    </div>
  );
}
