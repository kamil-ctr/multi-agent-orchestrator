import { motion } from "framer-motion";
import { FileText, Bot, AlertCircle } from "lucide-react";
import AgentProgressPanel from "./AgentProgressPanel";
import ResultsPanel from "./ResultsPanel";

/**
 * One conversation turn: the user's prompt bubble (with attachment chip, if
 * any) plus the assistant-side response, which renders as one of three
 * states depending on `turn.status` — a live AgentProgressPanel while
 * running, a ResultsPanel once synthesis completes, or an inline error.
 *
 * @param {Object} props
 * @param {Object} props.turn - One entry from ChatPage's `turns` state:
 *   `{id, prompt, attachment, status: "running"|"done"|"error", agentStates, result, historyId, error}`.
 * @returns {JSX.Element}
 */
export default function ChatMessage({ turn }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-end">
        <div className="flex max-w-2xl flex-col items-end gap-2">
          {turn.attachment && (
            <div
              className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs"
              style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
            >
              {turn.attachment.kind === "image" ? (
                <img
                  src={`data:${turn.attachment.mime_type};base64,${turn.attachment.data_base64}`}
                  alt={turn.attachment.filename}
                  className="h-8 w-8 rounded object-cover"
                />
              ) : (
                <FileText size={14} style={{ color: "var(--text-muted)" }} />
              )}
              <span style={{ color: "var(--text-secondary)" }}>{turn.attachment.filename}</span>
            </div>
          )}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-4 rounded-tr-1 px-4 py-2.5 text-sm shadow-[var(--elev-1)]"
            style={{ background: "var(--accent)", color: "var(--accent-contrast)" }}
          >
            {turn.prompt}
          </motion.div>
        </div>
      </div>

      <div className="flex justify-start">
        <div className="flex w-full items-start gap-3">
          <div
            className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
            style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}
          >
            <Bot size={15} />
          </div>
          <div className="min-w-0 flex-1">
            {turn.status === "running" && <AgentProgressPanel agentStates={turn.agentStates} />}
            {turn.status === "done" && turn.result && (
              <ResultsPanel result={turn.result} historyId={turn.historyId} />
            )}
            {turn.status === "error" && (
              <div className="flex flex-col gap-3">
                {/* If any agent got as far as being dispatched, keep the race
                    view visible (frozen — see ChatPage's stream-error handler)
                    instead of replacing it outright. Seeing how far each agent
                    got is more useful than a bare error, and it's what "freeze
                    in place instead of spinning forever" means for this view. */}
                {Object.keys(turn.agentStates || {}).length > 0 && (
                  <AgentProgressPanel agentStates={turn.agentStates} />
                )}
                <div
                  className="flex items-center gap-2 rounded-xl border px-4 py-3 text-sm"
                  style={{ borderColor: "var(--status-critical)", color: "var(--status-critical)" }}
                >
                  <AlertCircle size={16} />
                  {turn.error || "Something went wrong."}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
