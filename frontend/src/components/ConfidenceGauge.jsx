function colorFor(score) {
  if (score >= 70) return "var(--status-good)";
  if (score >= 40) return "var(--status-warning)";
  return "var(--status-critical)";
}

/**
 * Confidence readout: a single horizontal bar, not an animated arc — the
 * number is the point, the bar is just a scale to place it against.
 *
 * Color bands: green ≥70%, amber 40-69%, red <40% — matches the same
 * thresholds used nowhere else numerically, just visually, so the reader
 * gets an at-a-glance read before looking at the number.
 *
 * @param {Object} props
 * @param {number} [props.score=0] - Confidence percentage, 0-100.
 * @param {number} [props.size=120] - Minimum width in pixels.
 * @returns {JSX.Element}
 */
export default function ConfidenceGauge({ score = 0, size = 120 }) {
  const clamped = Math.max(0, Math.min(100, score));
  const color = colorFor(clamped);

  return (
    <div className="flex flex-col gap-1.5" style={{ minWidth: size }}>
      <div className="label">confidence</div>
      <div className="flex items-center gap-3">
        <div className="h-1.5 flex-1" style={{ background: "var(--surface-2)" }}>
          <div className="h-full" style={{ width: `${clamped}%`, background: color }} />
        </div>
        <span className="numeric shrink-0 text-sm" style={{ color }}>
          {Math.round(clamped)}%
        </span>
      </div>
    </div>
  );
}
