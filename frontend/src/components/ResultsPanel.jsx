import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import ReactMarkdown from "react-markdown";
import { Volume2, VolumeX, Download, Zap } from "lucide-react";
import ConfidenceGauge from "./ConfidenceGauge";
import ComparisonTable from "./ComparisonTable";
import AgentResponseCard from "./AgentResponseCard";
import ExplainabilityPanel from "./ExplainabilityPanel";
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
 * @param {boolean} [props.reveal=false] - Play the result-reveal sequence on mount. True only for a
 *   result that just finished synthesizing live; false for turns restored from conversation history,
 *   where the "it just landed" payoff moment already happened in a previous session.
 * @returns {JSX.Element}
 */
export default function ResultsPanel({ result, historyId, reveal = false }) {
  const { speaking, speak, stop, supported } = useTextToSpeech();
  const { settings } = useSettings();
  const autoplayedRef = useRef(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (settings.voiceAutoplay && supported && !autoplayedRef.current && result.synthesized_answer) {
      autoplayedRef.current = true;
      speak(result.synthesized_answer, settings.voiceRate);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result.synthesized_answer]);

  // The payoff moment: synthesis just finished, so the reveal gets a beat
  // more theater than the page-load stagger — the card frame first, then the
  // answer, then the score, then the supporting detail underneath. Skipped
  // entirely for history loads (see the `reveal` prop) and for
  // prefers-reduced-motion, where everything simply renders at rest.
  useGSAP(
    () => {
      if (!reveal) return;
      gsap.matchMedia(rootRef.current).add("(prefers-reduced-motion: no-preference)", () => {
        const tl = gsap.timeline({ defaults: { ease: "expo.out" } });
        tl.from("[data-gsap='reveal-card']", { opacity: 0, y: 16, scale: 0.98, duration: 0.35 }, 0)
          .from("[data-gsap='reveal-answer']", { opacity: 0, y: 10, duration: 0.35 }, 0.15)
          .from("[data-gsap='reveal-gauge']", { opacity: 0, scale: 0.9, duration: 0.4 }, 0.3)
          .from("[data-gsap='reveal-meta']", { opacity: 0, y: 6, duration: 0.3 }, 0.4)
          .from("[data-gsap='reveal-comparison']", { opacity: 0, y: 12, duration: 0.35 }, 0.5)
          .from("[data-gsap='reveal-responses']", { opacity: 0, y: 12, duration: 0.35 }, 0.62);
        return () => tl.kill();
      });
    },
    { scope: rootRef, dependencies: [] }
  );

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
    <div className="flex flex-col gap-5" ref={rootRef}>
      <div
        data-gsap="reveal-card"
        className="rounded-2xl border p-5"
        style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div data-gsap="reveal-answer" className="min-w-0 flex-1">
            <div className="mb-2 flex items-center gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
                Synthesized Answer
              </h2>
              {result.cache_hit === "exact" && (
                <span
                  className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs"
                  style={{ background: "var(--surface-1)", color: "var(--text-muted)" }}
                >
                  <Zap size={11} /> Cached (exact match)
                </span>
              )}
              {result.cache_hit === "semantic" && (
                <span
                  className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs"
                  style={{ background: "var(--surface-1)", color: "var(--text-muted)" }}
                  title="Matched a previously-asked, differently-worded question"
                >
                  <Zap size={11} /> Semantic cache hit ({result.cache_similarity?.toFixed(2)} similarity)
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

          <div data-gsap="reveal-gauge" className="flex shrink-0 flex-col items-center gap-2 self-center">
            <ConfidenceGauge score={result.confidence_score} />
          </div>
        </div>

        <div
          data-gsap="reveal-meta"
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

        <ExplainabilityPanel explanation={result.explanation} />
      </div>

      <div data-gsap="reveal-comparison">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
          Comparison
        </h3>
        <ComparisonTable rows={tableRows} />
      </div>

      <div data-gsap="reveal-responses">
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
