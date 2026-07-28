import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import ChatInput from "../components/ChatInput";
import ChatMessage from "../components/ChatMessage";
import ConversationSidebar from "../components/ConversationSidebar";
import {
  createConversation,
  fetchAgents,
  fetchConversation,
  sendMessage,
  streamQuery,
  AGENT_ORDER,
} from "../api/client";
import { useSettings } from "../context/SettingsContext";

function newTurnId() {
  return `t_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function seedAgentStates(agentNames) {
  return Object.fromEntries(agentNames.map((n) => [n, { status: "waiting" }]));
}

function messagesToTurns(messages) {
  const turns = [];
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    if (m.role !== "user") continue;
    const next = messages[i + 1];
    if (next && next.role === "assistant") {
      turns.push({
        id: `m_${m.id}`,
        prompt: m.content,
        attachment: null,
        status: "done",
        agentStates: {},
        result: next.agent_responses,
        historyId: null,
        error: null,
      });
      i++;
    } else {
      turns.push({
        id: `m_${m.id}`,
        prompt: m.content,
        attachment: null,
        status: "error",
        agentStates: {},
        result: null,
        historyId: null,
        error: "This message didn't receive a response.",
      });
    }
  }
  return turns;
}

export default function ChatPage() {
  const [turns, setTurns] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [availableAgents, setAvailableAgents] = useState(AGENT_ORDER);
  const { settings } = useSettings();
  const scrollRef = useRef(null);
  const closeStreamRef = useRef(null);
  const activeConversationIdRef = useRef(null);

  useEffect(() => {
    activeConversationIdRef.current = activeConversationId;
  }, [activeConversationId]);

  useEffect(() => {
    fetchAgents()
      .then((agents) => setAvailableAgents(agents.map((a) => a.name)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  useEffect(() => () => closeStreamRef.current?.(), []);

  const updateTurn = useCallback((id, patch) => {
    setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, ...(typeof patch === "function" ? patch(t) : patch) } : t)));
  }, []);

  const handleNewChat = useCallback(() => {
    closeStreamRef.current?.();
    setTurns([]);
    setActiveConversationId(null);
  }, []);

  const handleSelectConversation = useCallback(async (conversationId) => {
    try {
      const conv = await fetchConversation(conversationId);
      closeStreamRef.current?.();
      setActiveConversationId(conversationId);
      setTurns(messagesToTurns(conv.messages));
    } catch {
      // conversation may have been deleted elsewhere — ignore
    }
  }, []);

  const handleSubmit = useCallback(
    async ({ text, attachment }) => {
      const enabledAgents = availableAgents.filter((n) => !settings.disabledAgents.includes(n));
      const id = newTurnId();
      const displayPrompt = text || (attachment ? `[${attachment.filename}]` : "");

      const turn = {
        id,
        prompt: displayPrompt,
        attachment,
        status: "running",
        agentStates: seedAgentStates(enabledAgents),
        result: null,
        historyId: null,
        error: null,
      };
      setTurns((prev) => [...prev, turn]);

      const payload = {
        prompt: text || "Describe what you see.",
        use_cache: true,
        enabled_agents: enabledAgents,
      };
      if (attachment?.kind === "image") {
        payload.image_base64 = attachment.data_base64;
        payload.image_mime = attachment.mime_type;
      } else if (attachment?.kind === "file") {
        payload.file_context = attachment.content;
        payload.file_name = attachment.filename;
      }

      try {
        let conversationId = activeConversationIdRef.current;
        if (conversationId == null) {
          const conv = await createConversation();
          conversationId = conv.id;
          activeConversationIdRef.current = conversationId;
          setActiveConversationId(conversationId);
          setSidebarRefreshKey((k) => k + 1);
        }

        const queryId = await sendMessage(conversationId, payload);
        closeStreamRef.current = streamQuery(
          queryId,
          (evt) => {
            if (evt.type === "agent_start") {
              updateTurn(id, (t) => ({
                agentStates: { ...t.agentStates, [evt.agent]: { status: "running" } },
              }));
            } else if (evt.type === "agent_token") {
              updateTurn(id, (t) => {
                const prev = t.agentStates[evt.agent] || { status: "running" };
                const text = (prev.text || "") + evt.token;
                return {
                  agentStates: {
                    ...t.agentStates,
                    [evt.agent]: { ...prev, status: "running", text, tokenCount: (prev.tokenCount || 0) + 1 },
                  },
                };
              });
            } else if (evt.type === "agent_done") {
              updateTurn(id, (t) => ({
                agentStates: {
                  ...t.agentStates,
                  [evt.agent]: {
                    ...t.agentStates[evt.agent],
                    status: "success",
                    latencyMs: evt.latency_ms,
                    score: evt.score,
                  },
                },
              }));
            } else if (evt.type === "agent_error") {
              updateTurn(id, (t) => ({
                agentStates: {
                  ...t.agentStates,
                  [evt.agent]: {
                    ...t.agentStates[evt.agent],
                    status: evt.status,
                    latencyMs: evt.latency_ms,
                    error: evt.error,
                  },
                },
              }));
            } else if (evt.type === "synthesis_done") {
              updateTurn(id, { status: "done", result: evt.result, historyId: evt.history_id });
              setSidebarRefreshKey((k) => k + 1);
              // A first-turn title is generated asynchronously server-side
              // after the reply — refresh once more so it shows up without
              // requiring a manual reload.
              setTimeout(() => setSidebarRefreshKey((k) => k + 1), 3000);
            } else if (evt.type === "fatal_error") {
              updateTurn(id, { status: "error", error: evt.error });
            }
          },
          () => updateTurn(id, (t) => (t.status === "running" ? { status: "error", error: "Connection lost" } : {}))
        );
      } catch (err) {
        updateTurn(id, { status: "error", error: err.response?.data?.detail || "Failed to submit query" });
      }
    },
    [availableAgents, settings.disabledAgents, updateTurn]
  );

  const isBusy = turns.some((t) => t.status === "running");

  return (
    <div className="flex h-full min-h-0">
      <ConversationSidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((c) => !c)}
        activeId={activeConversationId}
        onSelect={handleSelectConversation}
        onNewChat={handleNewChat}
        refreshKey={sidebarRefreshKey}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          <div className="mx-auto flex max-w-4xl flex-col gap-8">
            {turns.length === 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-1 flex-col items-center justify-center gap-3 py-24 text-center"
              >
                <Sparkles size={32} style={{ color: "var(--text-muted)" }} />
                <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
                  Ask once, hear from multiple agents
                </h1>
                <p className="max-w-sm text-sm" style={{ color: "var(--text-muted)" }}>
                  Type, speak, or attach an image/document. Every enabled agent answers in parallel,
                  gets scored, and gets synthesized into one best answer.
                </p>
              </motion.div>
            )}
            {turns.map((turn) => (
              <ChatMessage key={turn.id} turn={turn} />
            ))}
          </div>
        </div>

        <div className="border-t px-4 py-4 sm:px-8" style={{ borderColor: "var(--border)", background: "var(--surface-0)" }}>
          <div className="mx-auto max-w-4xl">
            <ChatInput onSubmit={handleSubmit} disabled={isBusy} />
          </div>
        </div>
      </div>
    </div>
  );
}
