// Display metadata per agent — color always paired with the label/initial
// below, never the sole way identity is conveyed (accessibility: identity
// is never color-alone).
//
// Each agent carries three color slots, defined in styles/tokens.css:
//   var   the mark  — fills, lanes, bars, avatar grounds (>= 3:1 vs surface)
//   ink   the text  — scores and labels drawn in the agent's hue (>= 4.5:1)
//   on    the foreground placed ON the mark (>= 4.5:1 against it)
// `on` differs per agent and per theme: white clears 4.5:1 on Gemini blue and
// Groq red but only reaches 3.15:1 on Mistral amber, which needs ink instead.
export const AGENT_META = {
  gemini: { label: "Gemini", initial: "G", var: "--agent-gemini", ink: "--agent-gemini-ink", on: "--agent-gemini-on" },
  mistral: { label: "Mistral", initial: "M", var: "--agent-mistral", ink: "--agent-mistral-ink", on: "--agent-mistral-on" },
  cohere: { label: "Cohere", initial: "Co", var: "--agent-cohere", ink: "--agent-cohere-ink", on: "--agent-cohere-on" },
  groq: { label: "Groq", initial: "Gq", var: "--agent-groq", ink: "--agent-groq-ink", on: "--agent-groq-on" },
};

export function agentColor(name) {
  const meta = AGENT_META[name];
  return meta ? `var(${meta.var})` : "var(--text-muted)";
}

/** The agent's hue tuned for use as text on a page surface. */
export function agentInk(name) {
  const meta = AGENT_META[name];
  return meta ? `var(${meta.ink})` : "var(--text-secondary)";
}

/** Legible foreground for text drawn on top of the agent's mark color. */
export function agentOn(name) {
  const meta = AGENT_META[name];
  return meta ? `var(${meta.on})` : "var(--surface-2)";
}

export function agentLabel(name) {
  return AGENT_META[name]?.label ?? name;
}

export function agentInitial(name) {
  return AGENT_META[name]?.initial ?? name.slice(0, 1).toUpperCase();
}

export const STATUS_META = {
  waiting: { label: "waiting", color: "var(--text-muted)" },
  running: { label: "running", color: "var(--text-secondary)" },
  success: { label: "done", color: "var(--status-good)" },
  error: { label: "failed", color: "var(--status-critical)" },
  timeout: { label: "timed out", color: "var(--status-warning)" },
  rate_limited: { label: "rate limited", color: "var(--status-warning)" },
  disabled: { label: "disabled", color: "var(--text-muted)" },
};
