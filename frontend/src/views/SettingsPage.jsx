import { useEffect, useState } from "react";
import { SettingsIcon, Sun, Moon, CheckCircle2, XCircle, Volume2, Zap } from "lucide-react";
import { fetchAgents } from "../api/client";
import AgentAvatar from "../components/AgentAvatar";
import { useSettings } from "../context/SettingsContext";
import { useTheme } from "../context/ThemeContext";

export default function SettingsPage() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const { settings, toggleAgent, update } = useSettings();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    fetchAgents()
      .then(setAgents)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-8 overflow-y-auto px-4 py-8 sm:px-8">
      <div className="flex items-center gap-2">
        <SettingsIcon size={22} className="text-blue-500" />
        <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
          Settings
        </h1>
      </div>

      <section>
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Appearance
        </h2>
        <div
          className="flex items-center justify-between rounded-xl border p-4"
          style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
        >
          <div>
            <div className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
              Theme
            </div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
              Dark by default — toggle for light mode.
            </div>
          </div>
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm"
            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
          >
            {theme === "dark" ? <Moon size={14} /> : <Sun size={14} />}
            {theme === "dark" ? "Dark" : "Light"}
          </button>
        </div>
      </section>

      <section>
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Voice
        </h2>
        <div
          className="flex flex-col gap-4 rounded-xl border p-4"
          style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                Auto-read answers
              </div>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                Speak the synthesized answer aloud as soon as it's ready.
              </div>
            </div>
            <button
              onClick={() => update({ voiceAutoplay: !settings.voiceAutoplay })}
              className="relative h-6 w-11 rounded-full transition-colors"
              style={{ background: settings.voiceAutoplay ? "#2a78d6" : "var(--border-strong)" }}
            >
              <span
                className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform"
                style={{ transform: settings.voiceAutoplay ? "translateX(22px)" : "translateX(2px)" }}
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
              <span className="w-10 text-right text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
                {settings.voiceRate.toFixed(2)}x
              </span>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Caching
        </h2>
        <div
          className="flex flex-col gap-4 rounded-xl border p-4"
          style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                <Zap size={13} /> Semantic cache
              </div>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                Reuse a cached answer for paraphrased repeat questions, not just exact-text repeats.
              </div>
            </div>
            <button
              onClick={() => update({ semanticCacheEnabled: !settings.semanticCacheEnabled })}
              className="relative h-6 w-11 rounded-full transition-colors"
              style={{ background: settings.semanticCacheEnabled ? "#2a78d6" : "var(--border-strong)" }}
            >
              <span
                className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform"
                style={{ transform: settings.semanticCacheEnabled ? "translateX(22px)" : "translateX(2px)" }}
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
              <span className="w-10 text-right text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
                {settings.semanticCacheThreshold.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Agents
        </h2>
        <p className="mb-3 text-xs" style={{ color: "var(--text-muted)" }}>
          Toggle which agents are dispatched on new queries. Key status is read from the server's{" "}
          <code>.env</code> — never shown here.
        </p>
        {loading && <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading...</div>}
        <div className="flex flex-col gap-2">
          {agents.map((agent) => {
            const isOn = !settings.disabledAgents.includes(agent.name);
            return (
              <div
                key={agent.name}
                className="flex items-center justify-between rounded-xl border p-3"
                style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
              >
                <div className="flex items-center gap-3">
                  <AgentAvatar name={agent.name} showLabel />
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {agent.model}
                  </span>
                  {agent.supports_vision && (
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      style={{ background: "var(--surface-1)", color: "var(--text-muted)" }}
                    >
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
                    style={{ background: isOn ? "#2a78d6" : "var(--border-strong)" }}
                  >
                    <span
                      className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform"
                      style={{ transform: isOn ? "translateX(22px)" : "translateX(2px)" }}
                    />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
