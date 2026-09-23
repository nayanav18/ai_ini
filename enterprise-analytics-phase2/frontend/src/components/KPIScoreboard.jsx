/**
 * KPIScoreboard.jsx
 * The persona-specific KPI cards row at the top of the dashboard.
 *
 * Copy to: frontend/src/components/KPIScoreboard.jsx
 */

function Sparkline({ trend, color }) {
  // Simple 6-point sparkline
  const points =
    trend === "up"      ? [18, 16, 19, 14, 12, 8]
    : trend === "down"  ? [8, 10, 9, 12, 15, 19]
    : [14, 13, 15, 13, 14, 14];

  const pts = points.map((y, i) => `${i * 16},${y}`).join(" ");
  const lineColor = trend === "up" ? "#009900"
    : trend === "down" ? "#E60000" : "#00B0CA";

  return (
    <svg width="100%" height="22" viewBox="0 0 80 22"
      style={{ marginTop: 8 }}>
      <polyline points={pts} fill="none"
        stroke={lineColor} strokeWidth="1.5" strokeLinecap="round" />
      <circle cx={80} cy={points[points.length-1]} r="2.5" fill={lineColor} />
    </svg>
  );
}

function KPICard({ kpi, loading }) {
  if (loading) {
    return (
      <div style={{
        background: "#1a2235", border: "1px solid #1e3a5f",
        borderRadius: 11, padding: "13px 15px",
        position: "relative", overflow: "hidden",
      }}>
        <div style={{ width: "60%", height: 10, background: "#1e3a5f",
                      borderRadius: 4, marginBottom: 12,
                      animation: "pulse 1.5s infinite" }} />
        <div style={{ width: "80%", height: 22, background: "#253650",
                      borderRadius: 4, marginBottom: 8,
                      animation: "pulse 1.5s infinite" }} />
        <div style={{ width: "50%", height: 10, background: "#1e3a5f",
                      borderRadius: 4, animation: "pulse 1.5s infinite" }} />
      </div>
    );
  }

  const trend = kpi.trend || "neutral";
  const bottomColor = trend === "up" ? "#009900"
    : trend === "down" ? "#E60000" : "#00B0CA";
  const changeColor = trend === "up" ? "#4ade80"
    : trend === "down" ? "#f87171" : "#22d3ee";
  const trendArrow = trend === "up" ? "↑" : trend === "down" ? "↓" : "→";

  return (
    <div style={{
      background: "#1a2235",
      border: "1px solid #1e3a5f",
      borderRadius: 11,
      padding: "13px 15px",
      position: "relative",
      overflow: "hidden",
      cursor: "pointer",
      transition: "all 0.2s",
    }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = `${bottomColor}66`;
        e.currentTarget.style.transform = "translateY(-2px)";
        e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.4)";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = "#1e3a5f";
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      {/* Bottom colour bar */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, ${bottomColor}, transparent)`,
      }} />

      {/* Label */}
      <div style={{
        fontSize: 10, color: "#64748b", fontWeight: 600,
        textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 7,
      }}>
        {kpi.label}
      </div>

      {/* Value */}
      <div style={{
        fontSize: 22, fontWeight: 800, color: "#fff",
        letterSpacing: "-0.03em", marginBottom: 3,
      }}>
        {kpi.value}
      </div>

      {/* Change */}
      <div style={{ fontSize: 10, fontWeight: 600, color: changeColor,
                    display: "flex", alignItems: "center", gap: 4 }}>
        <span>{trendArrow} {kpi.change}</span>
      </div>

      {/* Sparkline */}
      <Sparkline trend={trend} color={bottomColor} />

      {/* Smart insight chip */}
      {kpi.insight && (
        <div style={{
          fontSize: 9, fontWeight: 700, marginTop: 6,
          padding: "2px 8px", borderRadius: 999,
          background: `${bottomColor}18`, border: `1px solid ${bottomColor}44`,
          color: changeColor, display: "inline-block",
        }}>
          {kpi.insight}
        </div>
      )}
    </div>
  );
}

export default function KPIScoreboard({ kpis, loading }) {
  const displayKpis = loading
    ? Array(4).fill({})
    : (kpis || []).slice(0, 5);

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: `repeat(${displayKpis.length}, 1fr)`,
      gap: 10,
      marginBottom: 14,
    }}>
      {displayKpis.map((kpi, i) => (
        <KPICard key={i} kpi={kpi} loading={loading} />
      ))}
      <style>{`@keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.5} }`}</style>
    </div>
  );
}
