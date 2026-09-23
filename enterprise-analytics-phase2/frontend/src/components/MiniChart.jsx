import { useId, useState } from "react";

const SERIES_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#06b6d4", "#ef4444"];

function formatValue(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "0");
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function shortLabel(raw) {
  if (!raw) return "";
  const value = String(raw);
  const match = value.match(/(\d{4})[.\-/](\d{1,2})/);
  if (match) {
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${months[Number(match[2]) - 1] || match[2]}-${match[1].slice(2)}`;
  }
  return value.length <= 9 ? value : `${value.slice(0, 8)}…`;
}

function KpiChart({ chart }) {
  const point = chart.data?.[0];
  if (!point) return null;
  return (
    <div style={{ minHeight: 100, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
      <div style={{ fontSize: 30, fontWeight: 800, color: "#f8fafc", letterSpacing: "-0.03em" }}>
        {Number(point.value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
      </div>
      <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>{point.label}</div>
    </div>
  );
}

function BarChart({ chart }) {
  const [hovered, setHovered] = useState(null);
  const data = (chart.data || []).slice(0, 10);
  if (!data.length) return null;
  const values = data.map((point) => Number(point.value) || 0);
  const max = Math.max(...values.map(Math.abs), 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 125, padding: "0 4px" }}>
      {data.map((point, index) => {
        const value = values[index];
        const height = Math.max(4, Math.abs(value) / max * 92);
        const color = SERIES_COLORS[index % SERIES_COLORS.length];
        return (
          <div key={`${point.label}-${index}`} style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
            <span style={{ fontSize: 8, color, fontWeight: 700 }}>{formatValue(value)}</span>
            <div
              onMouseEnter={() => setHovered(index)}
              onMouseLeave={() => setHovered(null)}
              title={`${point.label}: ${formatValue(value)}`}
              style={{ width: "100%", height, maxWidth: 42, borderRadius: "4px 4px 0 0", background: `linear-gradient(180deg, ${color}, ${color}66)`, opacity: hovered !== null && hovered !== index ? 0.45 : 1, transition: "opacity .15s" }}
            />
            <span style={{ fontSize: 8, color: "#64748b", maxWidth: 54, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {shortLabel(point.label)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function DonutChart({ chart }) {
  const [hovered, setHovered] = useState(null);
  const data = (chart.data || []).slice(0, 6);
  if (!data.length) return null;
  const total = data.reduce((sum, point) => sum + Math.max(Number(point.value) || 0, 0), 0) || 1;
  const cx = 55;
  const cy = 55;
  const radius = 42;
  let angle = -Math.PI / 2;

  const arcs = data.map((point, index) => {
    const value = Math.max(Number(point.value) || 0, 0);
    const sweep = (value / total) * Math.PI * 2;
    const startX = cx + radius * Math.cos(angle);
    const startY = cy + radius * Math.sin(angle);
    angle += sweep;
    const endX = cx + radius * Math.cos(angle);
    const endY = cy + radius * Math.sin(angle);
    const largeArc = sweep > Math.PI ? 1 : 0;
    return {
      ...point,
      pct: Math.round(value / total * 100),
      color: SERIES_COLORS[index % SERIES_COLORS.length],
      path: `M ${cx} ${cy} L ${startX} ${startY} A ${radius} ${radius} 0 ${largeArc} 1 ${endX} ${endY} Z`,
    };
  });

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, minHeight: 105 }}>
      <svg width="105" height="105" viewBox="0 0 110 110" style={{ flexShrink: 0 }}>
        {arcs.map((arc, index) => (
          <path key={index} d={arc.path} fill={arc.color} opacity={hovered !== null && hovered !== index ? 0.4 : 1} stroke="#111827" strokeWidth="1" onMouseEnter={() => setHovered(index)} onMouseLeave={() => setHovered(null)} />
        ))}
        <circle cx={cx} cy={cy} r="26" fill="#0f172a" />
        <text x={cx} y={cy - 2} textAnchor="middle" fontSize="10" fontWeight="800" fill="#f8fafc">
          {hovered === null ? formatValue(total) : `${arcs[hovered].pct}%`}
        </text>
        <text x={cx} y={cy + 11} textAnchor="middle" fontSize="7" fill="#64748b">
          {hovered === null ? "total" : shortLabel(arcs[hovered].label)}
        </text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 0 }}>
        {arcs.map((arc, index) => (
          <div key={index} style={{ display: "flex", alignItems: "center", gap: 6 }} onMouseEnter={() => setHovered(index)} onMouseLeave={() => setHovered(null)}>
            <span style={{ width: 7, height: 7, borderRadius: 2, background: arc.color, flexShrink: 0 }} />
            <span style={{ fontSize: 9, color: "#cbd5e1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{arc.label}</span>
            <span style={{ fontSize: 9, color: arc.color, fontWeight: 700 }}>{arc.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LineChart({ chart }) {
  const gradientId = `mini-area-${useId().replace(/:/g, "")}`;
  const data = (chart.data || []).slice(0, 12);
  if (!data.length) return null;
  const values = data.map((point) => Number(point.value) || 0);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 460;
  const H = 120;
  const PAD = 18;
  const points = data.map((point, index) => ({
    x: data.length === 1 ? W / 2 : PAD + index / (data.length - 1) * (W - PAD * 2),
    y: PAD + (1 - (values[index] - min) / range) * (H - PAD * 2),
  }));
  const path = points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const area = `${path} L${points.at(-1).x},${H - PAD} L${points[0].x},${H - PAD} Z`;

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H + 18}`} style={{ overflow: "visible" }}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
        </linearGradient>
      </defs>
      {chart.type === "area" && <path d={area} fill={`url(#${gradientId})`} />}
      <path d={path} fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" />
      {points.map((point, index) => (
        <g key={index}>
          <circle cx={point.x} cy={point.y} r={index === values.indexOf(max) || index === values.indexOf(min) ? 4 : 2.8} fill="#3b82f6" stroke="#0f172a" strokeWidth="1" />
          {(index === values.indexOf(max) || index === values.indexOf(min) || index === data.length - 1) && (
            <text x={point.x} y={point.y - 7} textAnchor="middle" fontSize="8" fontWeight="700" fill="#93c5fd">{formatValue(values[index])}</text>
          )}
          {(index === 0 || index === data.length - 1 || data.length <= 8) && (
            <text x={point.x} y={H + 12} textAnchor="middle" fontSize="7.5" fill="#475569">{shortLabel(data[index].label)}</text>
          )}
        </g>
      ))}
    </svg>
  );
}

export default function MiniChart({ chart }) {
  if (!chart?.data?.length) return null;

  return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 6, fontWeight: 600 }}>{chart.title}</div>
      {chart.type === "kpi_card" && <KpiChart chart={chart} />}
      {(chart.type === "bar" || chart.type === "grouped_bar" || chart.type === "stacked_bar") && <BarChart chart={chart} />}
      {(chart.type === "donut" || chart.type === "pie") && <DonutChart chart={chart} />}
      {(chart.type === "line" || chart.type === "area") && <LineChart chart={chart} />}
    </div>
  );
}
