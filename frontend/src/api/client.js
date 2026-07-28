import axios from "axios";

const API_ROOT = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const API_BASE = `${API_ROOT}/api`;

const http = axios.create({ baseURL: API_BASE });

// Fixed identity order — every card/table/legend renders agents in this
// order so a given agent's color+position never shifts between views.
// Only agents with a working account are listed (see backend/config.yaml);
// unknown agent names (e.g. in old history entries) still render fine —
// they just sort to the end with a generic fallback color/initial.
export const AGENT_ORDER = ["gemini", "groq", "mistral", "cohere"];

export function sortByAgentOrder(items, keyFn = (x) => x.agent ?? x.name) {
  const rank = (name) => {
    const i = AGENT_ORDER.indexOf(name);
    return i === -1 ? AGENT_ORDER.length : i;
  };
  return [...items].sort((a, b) => rank(keyFn(a)) - rank(keyFn(b)));
}

export async function fetchAgents() {
  const { data } = await http.get("/agents");
  return sortByAgentOrder(data, (a) => a.name);
}

export async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await http.post("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function createQuery(payload) {
  const { data } = await http.post("/query", payload);
  return data.query_id;
}

/**
 * Opens an SSE connection for a query_id. Calls onEvent(parsedEvent) for
 * every event, and returns a close() function. Terminal events
 * (synthesis_done / fatal_error) close the connection automatically.
 */
export function streamQuery(queryId, onEvent, onError) {
  const es = new EventSource(`${API_BASE}/query/${queryId}/stream`);
  const types = ["agent_start", "agent_token", "agent_done", "agent_error", "synthesis_done", "fatal_error"];

  const handler = (evt) => {
    try {
      const payload = JSON.parse(evt.data);
      onEvent(payload);
      if (payload.type === "synthesis_done" || payload.type === "fatal_error") {
        es.close();
      }
    } catch (e) {
      console.error("Failed to parse SSE event", e);
    }
  };

  for (const t of types) es.addEventListener(t, handler);
  es.onerror = (e) => {
    if (onError) onError(e);
  };

  return () => es.close();
}

export async function createConversation(title) {
  const { data } = await http.post("/conversations", title ? { title } : {});
  return data;
}

export async function fetchConversations({ page = 1, pageSize = 30, search = "" } = {}) {
  const { data } = await http.get("/conversations", {
    params: { page, page_size: pageSize, search: search || undefined },
  });
  return data;
}

export async function fetchConversation(id) {
  const { data } = await http.get(`/conversations/${id}`);
  return data;
}

export async function sendMessage(conversationId, payload) {
  const { data } = await http.post(`/conversations/${conversationId}/messages`, payload);
  return data.query_id;
}

export async function renameConversation(id, title) {
  const { data } = await http.patch(`/conversations/${id}`, { title });
  return data;
}

export async function deleteConversation(id) {
  await http.delete(`/conversations/${id}`);
}

export async function fetchLeaderboard(queryType) {
  const { data } = await http.get("/leaderboard", { params: queryType ? { query_type: queryType } : {} });
  return { ...data, rows: sortByAgentOrder(data.rows, (r) => r.agent) };
}

export function exportUrl(id, format) {
  return `${API_BASE}/export/${id}?format=${format}`;
}

export default http;
