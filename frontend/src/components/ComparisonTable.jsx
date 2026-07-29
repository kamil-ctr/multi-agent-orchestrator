import { useMemo, useState } from "react";
import { ArrowUp, ArrowDown, ArrowUpDown, Crown } from "lucide-react";
import AgentAvatar from "./AgentAvatar";
import { STATUS_META, agentColor } from "../api/agentMeta";

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
 * Built to be readable in one glance: the Score column carries an inline
 * bar in the agent's own color (the same visual language as the live race
 * lanes) so relative magnitude reads before anyone parses the number, the
 * winner's row gets a colored rail plus crown, and the judge's own
 * strengths note sits right under the agent name as the one-line "why."
 *
 * @param {Object} props
 * @param {Array<{agent: string, status: string, overall?: number, latency_ms?: number, depth?: number, clarity?: number, strengths?: string}>} props.rows
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
      <table className="w-full min-w-[620px] text-left text-sm">
        <thead>
          <tr style={{ background: "var(--surface-2)" }}>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => col.sortable && toggleSort(col.key)}
                className={`label px-3 py-2 ${col.sortable ? "cursor-pointer select-none" : ""}`}
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  {col.sortable &&
                    (sortKey === col.key ? (
                      sortDir === "asc" ? (
                        <ArrowUp size={11} />
                      ) : (
                        <ArrowDown size={11} />
                      )
                    ) : (
                      <ArrowUpDown size={11} className="opacity-40" />
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
            const color = agentColor(row.agent);
            return (
              <tr
                key={row.agent}
                className="border-t"
                style={{
                  borderColor: "var(--border)",
                  background: isWinner ? "var(--accent-soft)" : "transparent",
                  boxShadow: isWinner ? `inset 3px 0 0 0 ${color}` : "none",
                }}
              >
                <td className="px-3 py-2">
                  <AgentAvatar name={row.agent} size={22} showLabel />
                  {row.strengths && (
                    <p
                      className="mt-0.5 max-w-[220px] truncate text-2xs"
                      style={{ color: "var(--text-muted)" }}
                      title={row.strengths}
                    >
                      {row.strengths}
                    </p>
                  )}
                </td>
                <td className="px-3 py-2">
                  {row.overall != null ? (
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 w-16 shrink-0 overflow-hidden rounded-1"
                        style={{ background: "var(--border-strong)" }}
                      >
                        <div
                          className="h-full rounded-1"
                          style={{ width: `${(row.overall / 10) * 100}%`, background: color }}
                        />
                      </div>
                      <span
                        className="numeric shrink-0"
                        style={{ color: "var(--text-primary)", fontWeight: isWinner ? 600 : 400 }}
                      >
                        {row.overall.toFixed(1)}
                      </span>
                      {isWinner && <Crown size={13} style={{ color: "var(--status-warning)", flexShrink: 0 }} />}
                    </div>
                  ) : (
                    <span className="numeric" style={{ color: "var(--text-muted)" }}>
                      —
                    </span>
                  )}
                </td>
                <td className="numeric px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                  {row.latency_ms != null ? `${Math.round(row.latency_ms)}ms` : "—"}
                </td>
                <td className="numeric px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                  {row.depth != null ? row.depth.toFixed(1) : "—"}
                </td>
                <td className="numeric px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                  {row.clarity != null ? row.clarity.toFixed(1) : "—"}
                </td>
                <td className="px-3 py-2">
                  <span className="text-xs" style={{ color: statusMeta.color }}>
                    {statusMeta.label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
