/**
 * A loading placeholder bar. Reuses the app's existing pulse-soft keyframe
 * (already prefers-reduced-motion-aware — see styles/base.css) rather than
 * introducing a second animation for the same purpose.
 *
 * @param {Object} props
 * @param {string} [props.className=""] - Extra classes, typically width/height utilities.
 * @param {Object} [props.style={}] - Extra inline styles.
 * @returns {JSX.Element}
 */
export default function Skeleton({ className = "", style = {} }) {
  return <div className={`animate-pulse-soft rounded-2 ${className}`} style={{ background: "var(--border-strong)", ...style }} />;
}
