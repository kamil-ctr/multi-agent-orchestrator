import { agentColor, agentInitial, agentLabel } from "../api/agentMeta";

/**
 * Colored initial-letter avatar for one agent, optionally with its name label.
 *
 * Color is always paired with the initial/label text — identity is never
 * conveyed by color alone, per the app's accessibility rule (see
 * frontend/src/api/agentMeta.js).
 *
 * @param {Object} props
 * @param {string} props.name - Agent identifier (e.g. "gemini"), looked up in AGENT_META.
 * @param {number} [props.size=28] - Diameter of the avatar circle in pixels.
 * @param {boolean} [props.showLabel=false] - Whether to render the agent's display name next to the avatar.
 * @param {string} [props.className=""] - Extra classes applied to the wrapping element.
 * @returns {JSX.Element}
 */
export default function AgentAvatar({ name, size = 28, showLabel = false, className = "" }) {
  const color = agentColor(name);
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className="flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
        style={{ width: size, height: size, background: color, fontSize: size * 0.4 }}
        title={agentLabel(name)}
      >
        {agentInitial(name)}
      </div>
      {showLabel && (
        <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          {agentLabel(name)}
        </span>
      )}
    </div>
  );
}
