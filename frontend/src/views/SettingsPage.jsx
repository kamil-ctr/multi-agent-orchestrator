import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, XCircle, Volume2, Zap, TriangleAlert } from "lucide-react";
import { fetchAgents } from "../api/client";
import { agentColor, agentInitial, agentLabel } from "../api/agentMeta";
import Skeleton from "../components/Skeleton";
import { useSettings } from "../context/SettingsContext";

function AgentLabel({ agent }) {
  const color = agentColor(agent);
  return (
    <span className="text-2xs uppercase" style={{ color, letterSpacing: "var(--tracking-label)" }}>
      {agentInitial(agent)} {agentLabel(agent)}
    </span>
  );
}

export default function SettingsPage() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const { settings, toggleAgent, update } = useSettings();

  const loadAgents = useCallback(() => {
    setLoading(true);
    setLoadError(false);
    fetchAgents()
      .then(setAgents)
      .catch(() => setLoadError(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(loadAgents, [loadAgents]);

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-8 overflow-y-auto px-4 py-8 sm:px-8" style={{ background: "var(--surface-0)" }}>
      <h1
        className="uppercase"
        style={{
          fontSize: "var(--text-xl)",
          fontWeight: "var(--weight-regular)",
          letterSpacing: "var(--tracking-heading)",
          color: "var(--text-primary)",
        }}
      >
        Settings
      </h1>

      <section>
        <h2 className="label mb-2">Voice</h2>
        <div className="flex flex-col gap-4 border p-4" style={{ borderColor: "var(--border-strong)" }}>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm" style={{ color: "var(--text-primary)" }}>
                Auto-read answers
              </div>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                Speak the synthesized answer aloud as soon as it's ready.
              </div>
            </div>
            <button
              onClick={() => update({ voiceAutoplay: !settings.voiceAutoplay })}
              className="relative h-6 w-11 rounded-full transition-colors"
              style={{ background: settings.voiceAutoplay ? "var(--accent)" : "var(--border-strong)" }}
            >
              <span
                className="absolute top-0.5 h-5 w-5 rounded-full transition-transform"
                style={{
                        background: settings.voiceAutoplay ? "var(--accent-contrast)" : "var(--text-secondary)",
                        transform: settings.voiceAutoplay ? "translateX(22px)" : "translateX(2px)",
                      }}
              />
            </button>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-primary)" }}>
              <Volume2 size={14} /> Speech rate
            </div>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="0.5"
                max="1.75"
                step="0.05"
                value={settings.voiceRate}
                onChange={(e) => update({ voiceRate: Number(e.target.value) })}
              />
              <span className="numeric w-10 text-right text-xs" style={{ color: "var(--text-muted)" }}>
                {settings.voiceRate.toFixed(2)}x
              </span>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="label mb-2">Caching</h2>
        <div className="flex flex-col gap-4 border p-4" style={{ borderColor: "var(--border-strong)" }}>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-sm" style={{ color: "var(--text-primary)" }}>
                <Zap size={13} /> Semantic cache
              </div>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                Reuse a cached answer for paraphrased repeat questions, not just exact-text repeats.
              </div>
            </div>
            <button
              onClick={() => update({ semanticCacheEnabled: !settings.semanticCacheEnabled })}
              className="relative h-6 w-11 rounded-full transition-colors"
              style={{ background: settings.semanticCacheEnabled ? "var(--accent)" : "var(--border-strong)" }}
            >
              <span
                className="absolute top-0.5 h-5 w-5 rounded-full transition-transform"
                style={{
                        background: settings.semanticCacheEnabled ? "var(--accent-contrast)" : "var(--text-secondary)",
                        transform: settings.semanticCacheEnabled ? "translateX(22px)" : "translateX(2px)",
                      }}
              />
            </button>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div className="text-sm" style={{ color: "var(--text-primary)" }}>
              Similarity threshold
            </div>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="0.85"
                max="0.98"
                step="0.01"
                disabled={!settings.semanticCacheEnabled}
                value={settings.semanticCacheThreshold}
                onChange={(e) => update({ semanticCacheThreshold: Number(e.target.value) })}
              />
              <span className="numeric w-10 text-right text-xs" style={{ color: "var(--text-muted)" }}>
                {settings.semanticCacheThreshold.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="label mb-2">Agents</h2>
        <p className="mb-3 text-xs" style={{ color: "var(--text-muted)" }}>
          Toggle which agents are dispatched on new queries. Key status is read from the server's{" "}
          <code>.env</code> — never shown here.
        </p>
        {loading && (
          <div className="flex flex-col">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="flex items-center justify-between border-t p-3" style={{ borderColor: "var(--border-strong)" }}>
                <div className="flex items-center gap-3">
                  <Skeleton className="h-3 w-20" />
                </div>
                <Skeleton className="h-6 w-11 rounded-full" />
              </div>
            ))}
          </div>
        )}
        {!loading && loadError && (
          <div className="flex flex-col items-center gap-2 border p-6 text-center" style={{ borderColor: "var(--border-strong)" }}>
            <TriangleAlert size={18} style={{ color: "var(--text-muted)" }} />
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Couldn't load agents — check that the backend is running.
            </p>
            <button
              onClick={loadAgents}
              className="text-xs opacity-70 transition-opacity duration-[var(--duration-base)] ease-vivid hover:opacity-100"
              style={{ color: "var(--text-primary)" }}
            >
              Retry
            </button>
          </div>
        )}
        {!loading && !loadError && (
        <div className="flex flex-col">
          {agents.map((agent) => {
            const isOn = !settings.disabledAgents.includes(agent.name);
            return (
              <div
                key={agent.name}
                className="flex items-center justify-between border-t p-3"
                style={{ borderColor: "var(--border-strong)" }}
              >
                <div className="flex items-center gap-3">
                  <AgentLabel agent={agent.name} />
                  <span className="numeric text-xs" style={{ color: "var(--text-muted)" }}>
                    {agent.model}
                  </span>
                  {agent.supports_vision && (
                    <span className="text-2xs uppercase" style={{ color: "var(--text-muted)", letterSpacing: "var(--tracking-label)" }}>
                      vision
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-4">
                  {agent.key_configured ? (
                    <span className="flex items-center gap-1 text-xs" style={{ color: "var(--status-good)" }}>
                      <CheckCircle2 size={13} /> configured
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                      <XCircle size={13} /> missing key
                    </span>
                  )}
                  <button
                    onClick={() => toggleAgent(agent.name)}
                    className="relative h-6 w-11 rounded-full transition-colors"
                    style={{ background: isOn ? "var(--accent)" : "var(--border-strong)" }}
                  >
                    <span
                      className="absolute top-0.5 h-5 w-5 rounded-full transition-transform"
                      style={{
                        background: isOn ? "var(--accent-contrast)" : "var(--text-secondary)",
                        transform: isOn ? "translateX(22px)" : "translateX(2px)",
                      }}
                    />
                  </button>
                </div>
              </div>
            );
          })}
          {agents.length === 0 && (
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              No agents configured — add API keys to the backend's <code>.env</code>.
            </p>
          )}
        </div>
        )}
      </section>
    </div>
  );
}
