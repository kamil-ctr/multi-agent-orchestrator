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
    <div className="mt-3 border-t pt-3" style={{ borderColor: "var(--border)" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs font-medium transition-colors hover:opacity-80"
        style={{ color: "var(--text-secondary)" }}
      >
        <Lightbulb size={13} />
        Why this synthesis?
        <ChevronDown
          size={13}
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}
        />
      </button>

      {open && (
        <div
          className="mt-2 flex flex-col gap-2 rounded-lg p-3 text-xs leading-relaxed"
          style={{ background: "var(--surface-1)", color: "var(--text-secondary)" }}
        >
          <p>{explanation.summary}</p>
          {explanation.key_differentiators?.length > 0 && (
            <ul className="ml-4 list-disc space-y-1">
              {explanation.key_differentiators.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
