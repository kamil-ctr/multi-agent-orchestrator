import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Search, MessageSquarePlus, Pencil, Trash2, MessagesSquare, TriangleAlert } from "lucide-react";
import { fetchConversations, renameConversation, deleteConversation } from "../api/client";
import Skeleton from "./Skeleton";

function formatTime(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

/**
 * Collapsible left sidebar listing conversations (not individual queries) —
 * click to load a conversation's full multi-turn history, right-click for a
 * Rename/Delete menu, "New chat" to start a fresh one. Client-side search
 * filters by title match against whatever page of conversations is loaded.
 *
 * @param {Object} props
 * @param {boolean} props.collapsed
 * @param {() => void} props.onToggle
 * @param {number | null} props.activeId - The currently-open conversation's id, for highlighting.
 * @param {(id: number) => void} props.onSelect
 * @param {() => void} props.onNewChat
 * @param {*} props.refreshKey - Any value whose identity change triggers a re-fetch.
 * @returns {JSX.Element}
 */
export default function ConversationSidebar({ collapsed, onToggle, activeId, onSelect, onNewChat, refreshKey }) {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [menu, setMenu] = useState(null); // { id, x, y }
  const [renamingId, setRenamingId] = useState(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [confirmingDeleteId, setConfirmingDeleteId] = useState(null);
  const menuRef = useRef(null);

  const load = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const data = await fetchConversations({ page: 1, pageSize: 50 });
      setItems(data.items);
    } catch {
      // A fetch failure and a genuinely empty history look identical unless
      // told apart — "No conversations yet" would be actively misleading if
      // the server just isn't reachable.
      setItems([]);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (collapsed) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collapsed, refreshKey]);

  useEffect(() => {
    if (!menu) return;
    const close = () => {
      setMenu(null);
      setConfirmingDeleteId(null);
    };
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, [menu]);

  const filtered = search.trim()
    ? items.filter((i) => i.title.toLowerCase().includes(search.trim().toLowerCase()))
    : items;

  const openMenu = (e, id) => {
    e.preventDefault();
    setMenu({ id, x: e.clientX, y: e.clientY });
    setConfirmingDeleteId(null);
  };

  const startRename = (item) => {
    setRenamingId(item.id);
    setRenameDraft(item.title);
    setMenu(null);
  };

  const commitRename = async (id) => {
    const title = renameDraft.trim();
    setRenamingId(null);
    if (!title) return;
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, title } : i)));
    try {
      await renameConversation(id, title);
    } catch {
      load();
    }
  };

  const handleDelete = async (id) => {
    setMenu(null);
    setConfirmingDeleteId(null);
    setItems((prev) => prev.filter((i) => i.id !== id));
    try {
      await deleteConversation(id);
    } finally {
      if (id === activeId) onNewChat();
    }
  };

  if (collapsed) {
    return (
      <button
        data-gsap="sidebar"
        onClick={onToggle}
        className="flex w-9 shrink-0 flex-col items-center gap-2 border-r py-3"
        style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
        title="Show conversations"
      >
        <ChevronRight size={16} style={{ color: "var(--text-muted)" }} />
        <MessageSquarePlus size={14} style={{ color: "var(--text-muted)" }} />
      </button>
    );
  }

  return (
    <aside
      data-gsap="sidebar"
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
        <button
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors hover:opacity-80"
          style={{ borderColor: "var(--border)", background: "var(--surface-2)", color: "var(--text-primary)" }}
        >
          <MessageSquarePlus size={15} />
          New chat
        </button>
      </div>

      <div className="px-2 pb-2">
        <div
          className="flex items-center gap-2 rounded-lg border px-2 py-1.5"
          style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
        >
          <Search size={14} style={{ color: "var(--text-muted)" }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations..."
            className="w-full bg-transparent text-xs outline-none"
            style={{ color: "var(--text-primary)" }}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {loading && (
          <div className="flex flex-col gap-1">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="flex flex-col gap-1.5 px-2.5 py-2">
                <Skeleton className="h-3" style={{ width: `${70 - i * 8}%` }} />
                <Skeleton className="h-2.5" style={{ width: "40%" }} />
              </div>
            ))}
          </div>
        )}
        {!loading && loadError && (
          <div className="flex flex-col items-center gap-1.5 px-2 py-6 text-center">
            <TriangleAlert size={16} style={{ color: "var(--text-muted)" }} />
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Couldn't load conversations.
            </p>
            <button onClick={load} className="text-xs font-medium hover:opacity-80" style={{ color: "var(--accent)" }}>
              Retry
            </button>
          </div>
        )}
        {!loading && !loadError && filtered.length === 0 && (
          <div className="flex flex-col items-center gap-1.5 px-2 py-6 text-center">
            <MessagesSquare size={16} style={{ color: "var(--text-muted)" }} />
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {search.trim() ? "No matches." : "No conversations yet."}
            </p>
          </div>
        )}
        <div className="flex flex-col gap-1">
          {filtered.map((item) => (
            <div
              key={item.id}
              onContextMenu={(e) => openMenu(e, item.id)}
              className="group relative flex flex-col gap-0.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:opacity-90"
              style={{
                background: item.id === activeId ? "var(--surface-2)" : "transparent",
                border: item.id === activeId ? "1px solid var(--border-strong)" : "1px solid transparent",
                cursor: renamingId === item.id ? "default" : "pointer",
              }}
              onClick={() => renamingId !== item.id && onSelect(item.id)}
            >
              {renamingId === item.id ? (
                <input
                  autoFocus
                  value={renameDraft}
                  onChange={(e) => setRenameDraft(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitRename(item.id);
                    if (e.key === "Escape") setRenamingId(null);
                  }}
                  onBlur={() => commitRename(item.id)}
                  className="rounded border bg-transparent px-1 text-xs font-medium outline-none"
                  style={{ borderColor: "var(--border-strong)", color: "var(--text-primary)" }}
                />
              ) : (
                <div className="flex items-start justify-between gap-1">
                  <span className="line-clamp-2 text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                    {item.title}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openMenu(e, item.id);
                    }}
                    className="shrink-0 rounded px-1 text-xs opacity-0 transition-opacity group-hover:opacity-100"
                    style={{ color: "var(--text-muted)" }}
                    title="More options"
                  >
                    ⋯
                  </button>
                </div>
              )}
              <span className="flex items-center gap-2 text-[11px]" style={{ color: "var(--text-muted)" }}>
                <span>{formatTime(item.updated_at)}</span>
                {item.message_count > 0 && (
                  <>
                    <span>·</span>
                    <span>{item.message_count} msg{item.message_count === 1 ? "" : "s"}</span>
                  </>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>

      {menu && (
        <div
          ref={menuRef}
          onClick={(e) => e.stopPropagation()}
          className="fixed z-50 flex w-40 flex-col overflow-hidden rounded-lg border shadow-lg"
          style={{ top: menu.y, left: menu.x, borderColor: "var(--border)", background: "var(--surface-2)" }}
        >
          <button
            onClick={() => startRename(items.find((i) => i.id === menu.id))}
            className="flex items-center gap-2 px-3 py-2 text-left text-xs hover:opacity-80"
            style={{ color: "var(--text-primary)" }}
          >
            <Pencil size={13} /> Rename
          </button>
          <button
            onClick={() =>
              confirmingDeleteId === menu.id ? handleDelete(menu.id) : setConfirmingDeleteId(menu.id)
            }
            className="flex items-center gap-2 px-3 py-2 text-left text-xs hover:opacity-80"
            style={{ color: "var(--status-critical)" }}
          >
            <Trash2 size={13} /> {confirmingDeleteId === menu.id ? "Confirm delete?" : "Delete"}
          </button>
        </div>
      )}
    </aside>
  );
}
