import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid, LabelList } from "recharts";
import { Crown, TriangleAlert } from "lucide-react";
import { fetchLeaderboard } from "../api/client";
import { agentColor, agentInitial, agentLabel } from "../api/agentMeta";
import Skeleton from "../components/Skeleton";

const QUERY_TYPES = [
  { value: null, label: "All" },
  { value: "factual", label: "Factual" },
  { value: "creative", label: "Creative" },
  { value: "analytical", label: "Analytical" },
  { value: "coding", label: "Coding" },
  { value: "conversational", label: "Conversational" },
];

function AgentLabel({ agent }) {
  const color = agentColor(agent);
  return (
    <span className="text-2xs uppercase" style={{ color, letterSpacing: "var(--tracking-label)" }}>
      {agentInitial(agent)} {agentLabel(agent)}
    </span>
  );
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="border px-3 py-2 text-xs" style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}>
      <div className="mb-1" style={{ color: "var(--text-primary)" }}>
        {agentLabel(row.agent)}
      </div>
      <div className="numeric" style={{ color: "var(--text-secondary)" }}>avg score: {row.avg_score?.toFixed(2) ?? "—"}/10</div>
      <div className="numeric" style={{ color: "var(--text-secondary)" }}>success rate: {(row.success_rate * 100).toFixed(0)}%</div>
      <div className="numeric" style={{ color: "var(--text-secondary)" }}>runs: {row.total_runs}</div>
    </div>
  );
}

function ScoreLabel({ x, y, width, value }) {
  if (value == null) return null;
  return (
    <text x={x + width / 2} y={y - 6} textAnchor="middle" className="numeric" fontSize={11} fill="var(--text-secondary)">
      {value.toFixed(1)}
    </text>
  );
}

export default function LeaderboardPage() {
  const [queryType, setQueryType] = useState(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError(false);
    fetchLeaderboard(queryType)
      .then((data) => setRows(data.rows))
      .catch(() => setLoadError(true))
      .finally(() => setLoading(false));
  }, [queryType]);

  useEffect(load, [load]);

  const chartData = useMemo(
    () => rows.map((r) => ({ ...r, avg_score_display: r.avg_score ?? 0 })),
    [rows]
  );

  const leader = useMemo(() => {
    const scored = rows.filter((r) => r.avg_score != null);
    if (!scored.length) return null;
    return scored.reduce((best, r) => (r.avg_score > best.avg_score ? r : best));
  }, [rows]);

  return (
    <div
      className="mx-auto flex h-full max-w-5xl flex-col gap-6 overflow-y-auto px-4 py-8 sm:px-8"
      style={{ background: "var(--surface-0)" }}
    >
      <h1
        className="uppercase"
        style={{
          fontSize: "var(--text-xl)",
          fontWeight: "var(--weight-regular)",
          letterSpacing: "var(--tracking-heading)",
          color: "var(--text-primary)",
        }}
      >
        Leaderboard
      </h1>

      <div className="flex flex-wrap gap-2">
        {QUERY_TYPES.map((qt) => {
          const active = queryType === qt.value;
          return (
            <button
              key={qt.label}
              onClick={() => setQueryType(qt.value)}
              className="border px-3 py-1.5 text-xs transition-opacity duration-[var(--duration-base)] ease-vivid hover:opacity-100"
              style={{
                borderColor: "var(--border-strong)",
                color: "var(--text-primary)",
                opacity: active ? 1 : 0.6,
              }}
            >
              {qt.label}
            </button>
          );
        })}
      </div>

      {loading && (
        <>
          <div className="border p-5" style={{ borderColor: "var(--border-strong)" }}>
            <div className="flex items-center gap-4">
              <Skeleton className="h-11 w-11 rounded-full" />
              <div className="flex flex-1 flex-col gap-2">
                <Skeleton className="h-2.5 w-24" />
                <Skeleton className="h-5 w-32" />
              </div>
            </div>
          </div>
          <div className="border p-4" style={{ borderColor: "var(--border-strong)" }}>
            <div className="flex h-[280px] items-end justify-around gap-4 px-4">
              {[0.85, 0.65, 0.55, 0.4].map((h, i) => (
                <Skeleton key={i} className="w-full" style={{ height: `${h * 100}%` }} />
              ))}
            </div>
          </div>
        </>
      )}

      {!loading && loadError && (
        <div className="flex flex-col items-center gap-2 border py-12 text-center" style={{ borderColor: "var(--border-strong)" }}>
          <TriangleAlert size={20} style={{ color: "var(--text-muted)" }} />
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Couldn't load the leaderboard — check that the backend is running.
          </p>
          <button
            onClick={load}
            className="text-xs opacity-70 transition-opacity duration-[var(--duration-base)] ease-vivid hover:opacity-100"
            style={{ color: "var(--text-primary)" }}
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !loadError && rows.length === 0 && (
        <div className="py-12 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          No completed queries yet — run some in Chat first.
        </div>
      )}

      {!loading && !loadError && rows.length > 0 && (
        <>
          {leader && (
            <div className="flex items-center gap-4 border p-5" style={{ borderColor: "var(--border-strong)" }}>
              <div className="min-w-0 flex-1">
                <div className="label">
                  Current leader
                  {queryType ? ` — ${QUERY_TYPES.find((q) => q.value === queryType)?.label}` : ""}
                </div>
                <div className="flex items-baseline gap-2">
                  <span
                    style={{
                      fontFamily: "var(--font-display)",
                      fontSize: "var(--text-xl)",
                      color: agentColor(leader.agent),
                      letterSpacing: "var(--tracking-heading)",
                    }}
                  >
                    {agentLabel(leader.agent)}
                  </span>
                  <Crown size={18} style={{ color: "var(--status-warning)" }} />
                </div>
              </div>
              <div className="flex shrink-0 gap-6 text-right">
                <div>
                  <div className="numeric text-lg" style={{ color: "var(--text-primary)" }}>
                    {leader.avg_score.toFixed(2)}
                  </div>
                  <div className="label">avg score</div>
                </div>
                <div>
                  <div className="numeric text-lg" style={{ color: "var(--text-primary)" }}>
                    {(leader.success_rate * 100).toFixed(0)}%
                  </div>
                  <div className="label">success</div>
                </div>
              </div>
            </div>
          )}

          <div className="border p-4" style={{ borderColor: "var(--border-strong)" }}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} margin={{ top: 20, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-strong)" vertical={false} />
                <XAxis
                  dataKey="agent"
                  tickFormatter={agentLabel}
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={{ stroke: "var(--border-strong)" }}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 10]}
                  tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                  axisLine={{ stroke: "var(--border-strong)" }}
                  tickLine={false}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--surface-1)" }} />
                <Bar dataKey="avg_score_display" radius={0} maxBarSize={40}>
                  {chartData.map((row) => (
                    <Cell key={row.agent} fill={agentColor(row.agent)} />
                  ))}
                  <LabelList dataKey="avg_score" content={ScoreLabel} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto border" style={{ borderColor: "var(--border-strong)" }}>
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr className="border-b" style={{ borderColor: "var(--border-strong)" }}>
                  {["Rank", "Agent", "Avg Score", "Avg Latency", "Success Rate", "Runs"].map((h) => (
                    <th key={h} className="label px-3 py-2">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr
                    key={row.agent}
                    style={{
                      borderTop: i > 0 ? "1px solid var(--border-strong)" : "none",
                      borderLeft: i === 0 ? `1px solid ${agentColor(row.agent)}` : "1px solid transparent",
                    }}
                  >
                    <td className="numeric px-3 py-2" style={{ color: "var(--text-muted)" }}>
                      {i + 1}
                    </td>
                    <td className="px-3 py-2">
                      <AgentLabel agent={row.agent} />
                    </td>
                    <td className="numeric px-3 py-2" style={{ color: "var(--text-primary)" }}>
                      {row.avg_score != null ? row.avg_score.toFixed(2) : "—"}
                    </td>
                    <td className="numeric px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                      {row.avg_latency_ms != null ? `${Math.round(row.avg_latency_ms)}ms` : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div className="h-1 w-16 shrink-0" style={{ background: "var(--surface-2)" }}>
                          <div
                            className="h-full"
                            style={{ width: `${row.success_rate * 100}%`, background: agentColor(row.agent) }}
                          />
                        </div>
                        <span className="numeric shrink-0" style={{ color: "var(--text-secondary)" }}>
                          {(row.success_rate * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="numeric px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                      {row.total_runs}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
