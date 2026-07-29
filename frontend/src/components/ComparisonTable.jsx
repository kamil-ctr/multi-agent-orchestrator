import { useMemo, useState } from "react";
import { ArrowUp, ArrowDown, ArrowUpDown, Crown } from "lucide-react";
import AgentAvatar from "./AgentAvatar";
import { STATUS_META } from "../api/agentMeta";

const COLUMNS = [
  { key: "agent", label: "Agent", sortable: false },
  { key: "overall", label: "Score", sortable: true },
  { key: "latency_ms", label: "Latency", sortable: true },
  { key: "depth", label: "Depth", sortable: true },
  { key: "clarity", label: "Clarity", sortable: true },
  { key: "status", label: "Status", sortable: false },
];

/**
 * Sortable table comparing every dispatched agent's score, latency, depth,
 * clarity, and status. Click a sortable column header to sort by it;
 * clicking the active column again reverses direction.
 *
 * @param {Object} props
 * @param {Array<{agent: string, status: string, overall?: number, latency_ms?: number, depth?: number, clarity?: number}>} props.rows
 *   One row per dispatched agent, built by ResultsPanel from the pipeline result.
 * @returns {JSX.Element}
 */
export default function ComparisonTable({ rows }) {
  const [sortKey, setSortKey] = useState("overall");
  const [sortDir, setSortDir] = useState("desc");

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  const scored = rows.filter((r) => r.overall != null);
  const winner =
    scored.length > 1 ? scored.reduce((best, r) => (r.overall > best.overall ? r : best)).agent : null;

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  return (
    <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead>
          <tr style={{ background: "var(--surface-2)" }}>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => col.sortable && toggleSort(col.key)}
                className={`px-3 py-2 font-medium ${col.sortable ? "cursor-pointer select-none" : ""}`}
                style={{ color: "var(--text-secondary)" }}
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  {col.sortable &&
                    (sortKey === col.key ? (
                      sortDir === "asc" ? (
                        <ArrowUp size={12} />
                      ) : (
                        <ArrowDown size={12} />
                      )
                    ) : (
                      <ArrowUpDown size={12} className="opacity-40" />
                    ))}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => {
            const statusMeta = STATUS_META[row.status] ?? STATUS_META.disabled;
            const isWinner = row.agent === winner;
            return (
              <tr
                key={row.agent}
                className="border-t"
                style={{ borderColor: "var(--border)", background: isWinner ? "var(--accent-soft)" : "transparent" }}
              >
                <td className="px-3 py-2">
                  <AgentAvatar name={row.agent} size={22} showLabel />
                </td>
                <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-primary)" }}>
                  <span className="inline-flex items-center gap-1.5">
                    {row.overall != null ? `${row.overall.toFixed(1)}/10` : "—"}
                    {isWinner && <Crown size={13} style={{ color: "var(--status-warning)" }} />}
                  </span>
                </td>
                <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                  {row.latency_ms != null ? `${Math.round(row.latency_ms)}ms` : "—"}
                </td>
                <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                  {row.depth != null ? row.depth.toFixed(1) : "—"}
                </td>
                <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                  {row.clarity != null ? row.clarity.toFixed(1) : "—"}
                </td>
                <td className="px-3 py-2">
                  <span style={{ color: statusMeta.color }}>{statusMeta.label}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
