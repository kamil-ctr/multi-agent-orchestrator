// Display metadata per agent — color always paired with the label/initial
// below, never the sole way identity is conveyed (accessibility: identity
// is never color-alone).
export const AGENT_META = {
  gemini: { label: "Gemini", initial: "G", var: "--agent-gemini" },
  mistral: { label: "Mistral", initial: "M", var: "--agent-mistral" },
  cohere: { label: "Cohere", initial: "Co", var: "--agent-cohere" },
  groq: { label: "Groq", initial: "Gq", var: "--agent-groq" },
};

export function agentColor(name) {
  const meta = AGENT_META[name];
  return meta ? `var(${meta.var})` : "var(--text-muted)";
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
