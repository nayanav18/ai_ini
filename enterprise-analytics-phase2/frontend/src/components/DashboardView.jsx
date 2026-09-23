import MiniChart from "./MiniChart";

function KPICard({ kpi }) {
  const up = kpi.trend === "up", down = kpi.trend === "down";
  return (
    <div style={{ background: "linear-gradient(135deg,#111827,#0f172a)", border: "1px solid #1e3a5f", borderRadius: 12, padding: "14px 18px", flex: 1, minWidth: 140 }}>
      <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>{kpi.label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.02em" }}>{kpi.value}</div>
      <div style={{ fontSize: 11, marginTop: 5, color: up ? "#22c55e" : down ? "#ef4444" : "#94a3b8", fontWeight: 600 }}>
        {up ? "↑" : down ? "↓" : "→"} {kpi.change}
      </div>
    </div>
  );
}

export default function DashboardView({ insights }) {
  if (insights.length === 0) return (
    <div style={{ textAlign: "center", paddingTop: 80, color: "#475569" }}>
      <div style={{ fontSize: 36, marginBottom: 12 }}>📊</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: "#64748b" }}>No dashboards yet</div>
      <div style={{ fontSize: 13, marginTop: 6 }}>Save insights from chat responses to populate your dashboard.</div>
    </div>
  );

  const allKpis = insights.flatMap((ins) => ins.data?.kpis || []);
  const charted = insights.filter((ins) => ins.data?.chart).slice(0, 4);

  return (
    <div style={{ padding: 24, overflowY: "auto", height: "100%" }}>
      {/* KPI Grid */}
      <div style={{ fontSize: 11, color: "#3b82f6", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 16 }}>Live KPI Dashboard</div>
      {allKpis.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 28 }}>
          {allKpis.slice(0, 8).map((k, i) => <KPICard key={i} kpi={k} />)}
        </div>
      )}

      {/* Charts Grid */}
      {charted.length > 0 && (
        <>
          <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 14 }}>Charts</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            {charted.map((ins, i) => (
              <div key={i} style={{ background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 12, padding: "14px 18px" }}>
                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 4, fontWeight: 500 }}>{ins.query}</div>
                <MiniChart chart={ins.data.chart} />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Recent Recommendations */}
      {insights.some((ins) => ins.data?.recommendations?.length > 0) && (
        <>
          <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 14, marginTop: 28 }}>Top Recommendations</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {insights.flatMap((ins) => ins.data?.recommendations || []).slice(0, 5).map((r, i) => (
              <div key={i} style={{ display: "flex", gap: 10, padding: "10px 14px", background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 10 }}>
                <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999, alignSelf: "flex-start",
                  background: r.type === "Strategic" ? "rgba(59,130,246,0.13)" : r.type === "Tactical" ? "rgba(245,158,11,0.13)" : "rgba(239,68,68,0.13)",
                  color: r.type === "Strategic" ? "#60a5fa" : r.type === "Tactical" ? "#fbbf24" : "#f87171" }}>
                  {r.type}
                </span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0" }}>{r.action}</div>
                  <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{r.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
