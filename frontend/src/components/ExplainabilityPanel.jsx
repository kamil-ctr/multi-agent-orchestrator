import { useState } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";

/**
 * "Why this synthesis?" — an on-demand panel explaining why the judge
 * prioritized certain agents' responses over others, beyond the per-agent
 * strengths/weaknesses one-liners already shown in AgentResponseCard.
 *
 * Renders nothing when `explanation` is absent (heuristic-only evaluation,
 * or the judge ran but didn't produce a well-formed explanation) — no
 * placeholder "not available" clutter, matching the app's existing
 * graceful-degradation pattern elsewhere (Export link, cache badge, etc.).
 *
 * @param {Object} props
 * @param {{summary: string, key_differentiators: string[]} | null | undefined} props.explanation
 * @returns {JSX.Element | null}
 */
export default function ExplainabilityPanel({ explanation }) {
  const [open, setOpen] = useState(false);

  if (!explanation) return null;

  return (
    <div className="mt-3 border-t pt-3" style={{ borderColor: "var(--border-strong)" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex items-center gap-1.5 text-xs opacity-70 transition-opacity duration-[var(--duration-base)] ease-vivid hover:opacity-100"
        style={{ color: "var(--text-primary)" }}
      >
        <Lightbulb size={13} />
        Why this synthesis?
        <ChevronDown
          size={13}
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform var(--duration-base) var(--ease-vivid)" }}
        />
      </button>

      {open && (
        <div className="mt-2 flex flex-col gap-2 border-t pt-2 text-base" style={{ borderColor: "var(--border)" }}>
          <p style={{ color: "var(--text-primary)" }}>{explanation.summary}</p>
          {explanation.key_differentiators?.length > 0 && (
            <ol className="ml-4 list-decimal space-y-1" style={{ color: "var(--text-primary)" }}>
              {explanation.key_differentiators.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
