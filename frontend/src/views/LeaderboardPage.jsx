import { useEffect, useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from "recharts";
import { Trophy } from "lucide-react";
import { fetchLeaderboard } from "../api/client";
import { agentColor, agentLabel } from "../api/agentMeta";
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
    <div className="rounded-lg border px-3 py-2 text-xs shadow-lg" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
      <div className="mb-1 font-semibold" style={{ color: "var(--text-primary)" }}>
        {agentLabel(row.agent)}
      </div>
      <div style={{ color: "var(--text-secondary)" }}>avg score: {row.avg_score?.toFixed(2) ?? "—"}/10</div>
      <div style={{ color: "var(--text-secondary)" }}>success rate: {(row.success_rate * 100).toFixed(0)}%</div>
      <div style={{ color: "var(--text-secondary)" }}>runs: {row.total_runs}</div>
    </div>
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

  return (
    <div className="mx-auto flex h-full max-w-5xl flex-col gap-6 overflow-y-auto px-4 py-8 sm:px-8">
      <div className="flex items-center gap-2">
        <Trophy size={22} className="text-blue-500" />
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
              background: queryType === qt.value ? "#2a78d6" : "var(--surface-2)",
              color: queryType === qt.value ? "#fff" : "var(--text-secondary)",
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
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
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
                <Bar dataKey="avg_score_display" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {chartData.map((row) => (
                    <Cell key={row.agent} fill={agentColor(row.agent)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr style={{ background: "var(--surface-2)" }}>
                  {["Rank", "Agent", "Avg Score", "Avg Latency", "Success Rate", "Total Runs"].map((h) => (
                    <th key={h} className="px-3 py-2 font-medium" style={{ color: "var(--text-secondary)" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={row.agent} className="border-t" style={{ borderColor: "var(--border)" }}>
                    <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-muted)" }}>
                      {i + 1}
                    </td>
                    <td className="px-3 py-2">
                      <AgentAvatar name={row.agent} size={22} showLabel />
                    </td>
                    <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-primary)" }}>
                      {row.avg_score != null ? `${row.avg_score.toFixed(2)}/10` : "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                      {row.avg_latency_ms != null ? `${Math.round(row.avg_latency_ms)}ms` : "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                      {(row.success_rate * 100).toFixed(0)}%
                    </td>
                    <td className="px-3 py-2 tabular-nums" style={{ color: "var(--text-secondary)" }}>
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
