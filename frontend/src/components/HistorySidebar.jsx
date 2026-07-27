import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Search, Clock } from "lucide-react";
import { fetchHistory } from "../api/client";

function formatTime(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

/**
 * Collapsible left sidebar listing past queries, with a debounced search
 * box and click-to-reload. Re-fetches from /api/history whenever the
 * search term changes or `refreshKey` increments (bumped by ChatPage after
 * each new query completes, so a just-finished query appears without a
 * manual refresh).
 *
 * @param {Object} props
 * @param {boolean} props.collapsed - Whether the sidebar is collapsed to its icon-only rail.
 * @param {() => void} props.onToggle - Called when the collapse/expand control is clicked.
 * @param {(historyId: number) => void} props.onSelect - Called with a history row's id when the user clicks it.
 * @param {*} props.refreshKey - Any value whose identity change triggers a re-fetch (typically an incrementing counter).
 * @returns {JSX.Element}
 */
export default function HistorySidebar({ collapsed, onToggle, onSelect, refreshKey }) {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (collapsed) return;
    const handle = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await fetchHistory({ page: 1, pageSize: 30, search });
        setItems(data.items);
      } catch {
        setItems([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [search, collapsed, refreshKey]);

  if (collapsed) {
    return (
      <button
        onClick={onToggle}
        className="flex w-9 shrink-0 flex-col items-center gap-2 border-r py-3"
        style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
        title="Show history"
      >
        <ChevronRight size={16} style={{ color: "var(--text-muted)" }} />
        <Clock size={14} style={{ color: "var(--text-muted)" }} />
      </button>
    );
  }

  return (
    <aside
      className="flex w-72 shrink-0 flex-col border-r"
      style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
    >
      <div className="flex items-center justify-between gap-2 border-b p-3" style={{ borderColor: "var(--border)" }}>
        <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          History
        </span>
        <button onClick={onToggle} title="Collapse" style={{ color: "var(--text-muted)" }}>
          <ChevronLeft size={16} />
        </button>
      </div>

      <div className="p-2">
        <div
          className="flex items-center gap-2 rounded-lg border px-2 py-1.5"
          style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
        >
          <Search size={14} style={{ color: "var(--text-muted)" }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search queries..."
            className="w-full bg-transparent text-xs outline-none"
            style={{ color: "var(--text-primary)" }}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {loading && <div className="px-2 py-4 text-xs" style={{ color: "var(--text-muted)" }}>Loading...</div>}
        {!loading && items.length === 0 && (
          <div className="px-2 py-4 text-xs" style={{ color: "var(--text-muted)" }}>No queries yet.</div>
        )}
        <div className="flex flex-col gap-1">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelect(item.id)}
              className="flex flex-col gap-0.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:opacity-80"
              style={{ background: "var(--surface-2)" }}
            >
              <span className="line-clamp-2 text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                {item.query}
              </span>
              <span className="flex items-center gap-2 text-[11px]" style={{ color: "var(--text-muted)" }}>
                <span>{formatTime(item.timestamp)}</span>
                <span>·</span>
                <span>{item.query_type}</span>
                <span>·</span>
                <span>{item.confidence_score.toFixed(0)}%</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
