import { useEffect, useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid, LabelList } from "recharts";
import { Trophy, Crown } from "lucide-react";
import { fetchLeaderboard } from "../api/client";
import { agentColor, agentInk, agentLabel } from "../api/agentMeta";
import AgentAvatar from "../components/AgentAvatar";

const QUERY_TYPES = [
  { value: null, label: "All" },
  { value: "factual", label: "Factual" },
  { value: "creative", label: "Creative" },
  { value: "analytical", label: "Analytical" },
  { value: "coding", label: "Coding" },
  { value: "conversational", label: "Conversational" },
];

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-lg border px-3 py-2 text-xs shadow-[var(--elev-2)]" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
      <div className="mb-1 font-semibold" style={{ color: "var(--text-primary)" }}>
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

  useEffect(() => {
    setLoading(true);
    fetchLeaderboard(queryType)
      .then((data) => setRows(data.rows))
      .finally(() => setLoading(false));
  }, [queryType]);

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
    <div className="mx-auto flex h-full max-w-5xl flex-col gap-6 overflow-y-auto px-4 py-8 sm:px-8">
      <div className="flex items-center gap-2">
        <Trophy size={22} style={{ color: "var(--accent)" }} />
        <h1 className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
          Agent Leaderboard
        </h1>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {QUERY_TYPES.map((qt) => (
          <button
            key={qt.label}
            onClick={() => setQueryType(qt.value)}
            className="rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              background: queryType === qt.value ? "var(--accent)" : "var(--surface-2)",
              color: queryType === qt.value ? "var(--accent-contrast)" : "var(--text-secondary)",
            }}
          >
            {qt.label}
          </button>
        ))}
      </div>

      {loading && <div className="py-12 text-center text-sm" style={{ color: "var(--text-muted)" }}>Loading...</div>}

      {!loading && rows.length === 0 && (
        <div className="py-12 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          No completed queries yet — run some in Chat first.
        </div>
      )}

      {!loading && rows.length > 0 && (
        <>
          {leader && (
            <div
              className="flex items-center gap-4 rounded-3 border p-5"
              style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
            >
              <AgentAvatar name={leader.agent} size={44} />
              <div className="min-w-0 flex-1">
                <div className="label">
                  Current leader
                  {queryType ? ` — ${QUERY_TYPES.find((q) => q.value === queryType)?.label}` : ""}
                </div>
                <div className="flex items-baseline gap-2">
                  <span
                    style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", color: agentInk(leader.agent), letterSpacing: "var(--tracking-display)" }}
                  >
                    {agentLabel(leader.agent)}
                  </span>
                  <Crown size={18} style={{ color: "var(--status-warning)" }} />
                </div>
              </div>
              <div className="flex shrink-0 gap-6 text-right">
                <div>
                  <div className="numeric text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                    {leader.avg_score.toFixed(2)}
                  </div>
                  <div className="label">avg score</div>
                </div>
                <div>
                  <div className="numeric text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                    {(leader.success_rate * 100).toFixed(0)}%
                  </div>
                  <div className="label">success</div>
                </div>
              </div>
            </div>
          )}

          <div className="rounded-3 border p-4" style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}>
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
                <Bar dataKey="avg_score_display" radius={[2, 2, 0, 0]} maxBarSize={40}>
                  {chartData.map((row) => (
                    <Cell key={row.agent} fill={agentColor(row.agent)} />
                  ))}
                  <LabelList dataKey="avg_score" content={ScoreLabel} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr style={{ background: "var(--surface-2)" }}>
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
                    className="border-t"
                    style={{
                      borderColor: "var(--border)",
                      background: i === 0 ? "var(--accent-soft)" : "transparent",
                      boxShadow: i === 0 ? `inset 3px 0 0 0 ${agentColor(row.agent)}` : "none",
                    }}
                  >
                    <td className="numeric px-3 py-2" style={{ color: "var(--text-muted)" }}>
                      {i + 1}
                    </td>
                    <td className="px-3 py-2">
                      <AgentAvatar name={row.agent} size={22} showLabel />
                    </td>
                    <td className="numeric px-3 py-2" style={{ color: "var(--text-primary)", fontWeight: i === 0 ? 600 : 400 }}>
                      {row.avg_score != null ? row.avg_score.toFixed(2) : "—"}
                    </td>
                    <td className="numeric px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                      {row.avg_latency_ms != null ? `${Math.round(row.avg_latency_ms)}ms` : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-16 shrink-0 overflow-hidden rounded-1" style={{ background: "var(--border-strong)" }}>
                          <div
                            className="h-full rounded-1"
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
