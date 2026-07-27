import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Volume2, VolumeX, Download } from "lucide-react";
import ConfidenceGauge from "./ConfidenceGauge";
import ComparisonTable from "./ComparisonTable";
import AgentResponseCard from "./AgentResponseCard";
import { agentColor, agentLabel } from "../api/agentMeta";
import { useTextToSpeech } from "../hooks/useVoice";
import { exportUrl } from "../api/client";
import { useSettings } from "../context/SettingsContext";

/**
 * Full results view for one completed query: synthesized answer (markdown,
 * with optional TTS playback via useTextToSpeech), confidence gauge,
 * attribution chips, the sortable ComparisonTable, and one collapsible
 * AgentResponseCard per dispatched agent.
 *
 * Auto-speaks the synthesized answer on mount if the user has enabled
 * Settings → Voice → Auto-read answers.
 *
 * @param {Object} props
 * @param {Object} props.result - A full PipelineResult (query, synthesized_answer, evaluations, agent_responses, confidence_score, attribution, ...).
 * @param {number} [props.historyId] - The result's history row id, used to build the Export link; omitted for cache hits that weren't persisted.
 * @returns {JSX.Element}
 */
export default function ResultsPanel({ result, historyId }) {
  const { speaking, speak, stop, supported } = useTextToSpeech();
  const { settings } = useSettings();
  const autoplayedRef = useRef(false);

  useEffect(() => {
    if (settings.voiceAutoplay && supported && !autoplayedRef.current && result.synthesized_answer) {
      autoplayedRef.current = true;
      speak(result.synthesized_answer, settings.voiceRate);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result.synthesized_answer]);

  const evalByAgent = Object.fromEntries((result.evaluations || []).map((e) => [e.agent, e]));
  const responses = result.agent_responses || [];

  const tableRows = responses.map((r) => {
    const ev = evalByAgent[r.agent];
    return {
      agent: r.agent,
      status: r.status,
      latency_ms: r.latency_ms,
      overall: ev?.overall ?? null,
      depth: ev?.depth ?? null,
      clarity: ev?.clarity ?? null,
    };
  });

  const rankedAgents = [...(result.evaluations || [])].sort((a, b) => b.overall - a.overall).map((e) => e.agent);
  const orderedResponses = [...responses].sort((a, b) => {
    const ai = rankedAgents.indexOf(a.agent);
    const bi = rankedAgents.indexOf(b.agent);
    if (ai === -1 && bi === -1) return 0;
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });

  const handleSpeak = () => (speaking ? stop() : speak(result.synthesized_answer, settings.voiceRate));

  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-2xl border p-5" style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex items-center gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
                Synthesized Answer
              </h2>
              {result.cached && (
                <span className="rounded-full px-2 py-0.5 text-xs" style={{ background: "var(--surface-1)", color: "var(--text-muted)" }}>
                  cached
                </span>
              )}
              {supported && (
                <button
                  onClick={handleSpeak}
                  className="ml-auto flex items-center gap-1 rounded-full px-2 py-0.5 text-xs transition-colors hover:opacity-80 sm:ml-0"
                  style={{ background: "var(--surface-1)", color: "var(--text-secondary)" }}
                >
                  {speaking ? <VolumeX size={13} /> : <Volume2 size={13} />}
                  {speaking ? "Stop" : "Listen"}
                </button>
              )}
            </div>
            <div className="prose prose-sm max-w-none leading-relaxed" style={{ color: "var(--text-primary)" }}>
              <ReactMarkdown>{result.synthesized_answer}</ReactMarkdown>
            </div>

            {result.attribution && Object.keys(result.attribution).length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.entries(result.attribution).map(([agent, note]) => (
                  <span
                    key={agent}
                    className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs"
                    style={{ borderColor: agentColor(agent), color: "var(--text-secondary)" }}
                  >
                    <span className="h-1.5 w-1.5 rounded-full" style={{ background: agentColor(agent) }} />
                    <b style={{ color: "var(--text-primary)" }}>{agentLabel(agent)}</b>
                    <span>{note}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex shrink-0 flex-col items-center gap-2 self-center">
            <ConfidenceGauge score={result.confidence_score} />
          </div>
        </div>

        <div
          className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 border-t pt-3 text-xs"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
        >
          <span>evaluator: {result.evaluator_used}</span>
          <span>{result.total_tokens_estimate} tokens</span>
          <span>${result.estimated_cost_usd.toFixed(4)} est. cost</span>
          <span>{Math.round(result.total_latency_ms)}ms wall time</span>
          {historyId != null && (
            <a
              href={exportUrl(historyId, "md")}
              className="ml-auto flex items-center gap-1 hover:underline"
              style={{ color: "var(--text-secondary)" }}
            >
              <Download size={12} /> Export
            </a>
          )}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Comparison
        </h3>
        <ComparisonTable rows={tableRows} />
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Individual Responses
        </h3>
        <div className="flex flex-col gap-2">
          {orderedResponses.map((r) => (
            <AgentResponseCard key={r.agent} response={r} evaluation={evalByAgent[r.agent]} />
          ))}
        </div>
      </div>
    </div>
  );
}
