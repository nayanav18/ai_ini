/**
 * SmartChart.jsx
 * Renders any chart type returned by the analytics API.
 * Supports: line, bar, donut, waterfall, funnel, stacked_bar, heatmap, area, kpi_card
 *
 * Copy to: frontend/src/components/SmartChart.jsx
 */
import { useState } from "react";

// ── Colour palette (Vodafone brand) ───────────────────────────────────────
const VF = {
  red:    "#E60000",
  aqua:   "#00B0CA",
  orange: "#EB6100",
  green:  "#009900",
  gray:   "#666666",
  purple: "#8B5CF6",
  amber:  "#F59E0B",
};

const SERIES_COLORS = [
  VF.red, VF.aqua, VF.orange, VF.green,
  VF.purple, VF.amber, VF.gray, "#EC4899",
];

function formatValue(v) {
  if (v === null || v === undefined) return "0";
  const n = parseFloat(v);
  if (isNaN(n)) return String(v);
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000)    return (n / 1_000).toFixed(1) + "K";
  return n.toFixed(n % 1 === 0 ? 0 : 1);
}

// ── Line / Area Chart ─────────────────────────────────────────────────────
function LineChart({ data, color = VF.red, isArea = false }) {
  if (!data?.length) return <EmptyChart />;
  const values  = data.map(d => parseFloat(d.value) || 0);
  const maxVal  = Math.max(...values, 1);
  const minVal  = Math.min(...values);
  const range   = maxVal - minVal || 1;
  const W = 500, H = 140, PAD = 28;

  const pts = data.map((d, i) => {
    const x = PAD + (i / (data.length - 1 || 1)) * (W - PAD * 2);
    const y = H - PAD - ((parseFloat(d.value) - minVal) / range) * (H - PAD * 2);
    return { x, y, ...d };
  });

  const polyline = pts.map(p => `${p.x},${p.y}`).join(" ");
  const areaPath = `M${pts[0].x},${H - PAD} ` +
    pts.map(p => `L${p.x},${p.y}`).join(" ") +
    ` L${pts[pts.length-1].x},${H - PAD} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", overflow: "visible" }}>
      {/* Grid lines */}
      {[0.25, 0.5, 0.75, 1].map(r => (
        <line key={r} x1={PAD} y1={PAD + (1-r)*(H-PAD*2)}
          x2={W-PAD} y2={PAD + (1-r)*(H-PAD*2)}
          stroke="#1e3a5f" strokeWidth="0.5" strokeDasharray="3,3" />
      ))}
      {/* Area fill */}
      {isArea && (
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.15" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
      )}
      {isArea && <path d={areaPath} fill="url(#areaGrad)" />}
      {/* Line */}
      <polyline points={polyline} fill="none" stroke={color}
        strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {/* Dots */}
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y}
            r={p.is_peak || p.is_min ? 5 : 3.5}
            fill={p.is_peak ? VF.green : p.is_min ? VF.red : color}
            stroke="#111827" strokeWidth="1.5" />
          {(p.is_peak || p.is_min) && (
            <text x={p.x} y={p.y - 8} textAnchor="middle"
              fontSize="9" fill={p.is_peak ? VF.green : VF.red} fontWeight="700">
              {formatValue(p.value)}
            </text>
          )}
        </g>
      ))}
      {/* X labels */}
      {pts.map((p, i) => (
        <text key={i} x={p.x} y={H - 4} textAnchor="middle"
          fontSize="8.5" fill="#64748b">
          {String(p.label).slice(0, 8)}
        </text>
      ))}
    </svg>
  );
}

// ── Bar Chart ─────────────────────────────────────────────────────────────
function BarChart({ data, color = VF.red }) {
  if (!data?.length) return <EmptyChart />;
  const [hovered, setHovered] = useState(null);
  const values = data.map(d => parseFloat(d.value) || 0);
  const maxVal = Math.max(...values, 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6,
                  height: 140, padding: "0 4px" }}>
      {data.slice(0, 10).map((d, i) => {
        const h = Math.max(4, (parseFloat(d.value) / maxVal) * 125);
        const c = SERIES_COLORS[i % SERIES_COLORS.length];
        return (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column",
                                alignItems: "center", gap: 3 }}>
            <span style={{ fontSize: 9, fontWeight: 700, color: c }}>
              {formatValue(d.value)}
            </span>
            <div
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              style={{
                height: h, width: "100%",
                background: `linear-gradient(180deg, ${c}cc, ${c}55)`,
                borderRadius: "3px 3px 0 0",
                opacity: hovered !== null && hovered !== i ? 0.6 : 1,
                transition: "opacity 0.15s",
                cursor: "pointer",
              }} />
            <span style={{ fontSize: 8, color: "#64748b", textAlign: "center",
                           maxWidth: 52, overflow: "hidden", textOverflow: "ellipsis",
                           whiteSpace: "nowrap" }}>
              {d.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Donut / Pie Chart ─────────────────────────────────────────────────────
function DonutChart({ data }) {
  if (!data?.length) return <EmptyChart />;
  const [hovered, setHovered] = useState(null);
  const total = data.reduce((s, d) => s + (parseFloat(d.value) || 0), 0) || 1;
  const items = data.slice(0, 6);

  // Build SVG arcs
  const R = 44, CX = 55, CY = 55;
  let cumAngle = -Math.PI / 2;
  const arcs = items.map((d, i) => {
    const pct   = (parseFloat(d.value) || 0) / total;
    const angle = pct * 2 * Math.PI;
    const x1    = CX + R * Math.cos(cumAngle);
    const y1    = CY + R * Math.sin(cumAngle);
    cumAngle   += angle;
    const x2    = CX + R * Math.cos(cumAngle);
    const y2    = CY + R * Math.sin(cumAngle);
    const large = angle > Math.PI ? 1 : 0;
    return { d: `M${CX},${CY} L${x1},${y1} A${R},${R} 0 ${large},1 ${x2},${y2} Z`,
             color: SERIES_COLORS[i % SERIES_COLORS.length],
             pct: Math.round(pct * 100), label: d.label, value: d.value };
  });

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <svg width={110} height={110} viewBox="0 0 110 110" style={{ flexShrink: 0 }}>
        {arcs.map((arc, i) => (
          <path key={i} d={arc.d} fill={arc.color}
            opacity={hovered !== null && hovered !== i ? 0.5 : 1}
            stroke="#111827" strokeWidth="1"
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
            style={{ cursor: "pointer", transition: "opacity 0.15s" }} />
        ))}
        {/* Centre hole */}
        <circle cx={CX} cy={CY} r={28} fill="#111827" />
        <text x={CX} y={CY - 4} textAnchor="middle" fontSize="11"
          fontWeight="800" fill="white">
          {hovered !== null ? `${arcs[hovered].pct}%` : formatValue(total)}
        </text>
        <text x={CX} y={CY + 10} textAnchor="middle" fontSize="8" fill="#64748b">
          {hovered !== null ? arcs[hovered].label : "total"}
        </text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 7, flex: 1 }}>
        {arcs.map((arc, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 7,
                                cursor: "pointer" }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}>
            <div style={{ width: 9, height: 9, borderRadius: 2,
                          background: arc.color, flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: "#f0f4f8", flex: 1 }}>{arc.label}</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: arc.color }}>
              {arc.pct}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Waterfall Chart ───────────────────────────────────────────────────────
function WaterfallChart({ data }) {
  if (!data?.length) return <EmptyChart />;
  const values = data.map(d => parseFloat(d.value) || 0);
  const maxAbs = Math.max(...values.map(Math.abs), 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 5,
                  height: 130, padding: "0 4px" }}>
      {data.slice(0, 7).map((d, i) => {
        const v   = parseFloat(d.value) || 0;
        const h   = Math.max(4, (Math.abs(v) / maxAbs) * 115);
        const pos = v >= 0;
        // Detect INFLOW/OUTFLOW/NET from label
        const lbl = String(d.label).toUpperCase();
        const color = lbl.includes("INFLOW") || lbl.includes("IN") ? VF.green
          : lbl.includes("OUTFLOW") || lbl.includes("OUT") ? VF.red
          : lbl.includes("NET") ? (pos ? VF.green : VF.red)
          : SERIES_COLORS[i % SERIES_COLORS.length];

        return (
          <div key={i} style={{ flex: 1, display: "flex",
                                flexDirection: "column", alignItems: "center" }}>
            <span style={{ fontSize: 8, fontWeight: 700, color, marginBottom: 2 }}>
              {v > 0 ? "+" : ""}{formatValue(v)}
            </span>
            <div style={{
              height: h, width: "100%", borderRadius: "3px 3px 0 0",
              background: `${color}33`, border: `1px solid ${color}88`,
              cursor: "pointer",
            }} />
            <span style={{ fontSize: 8, color: "#64748b", textAlign: "center",
                           marginTop: 3, whiteSpace: "nowrap" }}>
              {d.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Funnel Chart ──────────────────────────────────────────────────────────
function FunnelChart({ data }) {
  if (!data?.length) return <EmptyChart />;
  const maxVal = Math.max(...data.map(d => parseFloat(d.value) || 0), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5,
                  padding: "4px 0" }}>
      {data.slice(0, 6).map((d, i) => {
        const pct   = ((parseFloat(d.value) || 0) / maxVal) * 100;
        const color = SERIES_COLORS[i % SERIES_COLORS.length];
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 10, color: "#94a3b8", width: 80,
                           textAlign: "right", flexShrink: 0 }}>{d.label}</span>
            <div style={{ flex: 1, display: "flex", alignItems: "center",
                          justifyContent: "center" }}>
              <div style={{
                width: `${pct}%`, height: 28, minWidth: 40,
                background: color, borderRadius: 4,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 10, fontWeight: 700, color: "#fff",
                transition: "all 0.3s",
              }}>
                {formatValue(d.value)}
              </div>
            </div>
            <span style={{ fontSize: 10, fontWeight: 700, width: 40,
                           color, flexShrink: 0 }}>{Math.round(pct)}%</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Stacked Bar ───────────────────────────────────────────────────────────
function StackedBarChart({ data }) {
  if (!data?.length) return <EmptyChart />;

  // Handle both {label, value} and {label, series: {}} formats
  const hasSeries = data[0]?.series;
  if (!hasSeries) return <BarChart data={data} />;

  const seriesKeys = Object.keys(data[0].series);
  const totals     = data.map(d =>
    Object.values(d.series).reduce((s, v) => s + (parseFloat(v) || 0), 0)
  );
  const maxTotal = Math.max(...totals, 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6,
                  height: 140, padding: "0 4px" }}>
      {data.slice(0, 8).map((d, i) => {
        const total = totals[i];
        const barH  = (total / maxTotal) * 125;
        return (
          <div key={i} style={{ flex: 1, display: "flex",
                                flexDirection: "column", alignItems: "center" }}>
            <div style={{ width: "100%", height: barH, display: "flex",
                          flexDirection: "column-reverse", borderRadius: "3px 3px 0 0",
                          overflow: "hidden" }}>
              {seriesKeys.map((key, ki) => {
                const v   = parseFloat(d.series[key]) || 0;
                const pct = (v / total) * 100;
                return (
                  <div key={ki} style={{
                    height: `${pct}%`, background: SERIES_COLORS[ki % SERIES_COLORS.length],
                    transition: "opacity 0.15s",
                  }} />
                );
              })}
            </div>
            <span style={{ fontSize: 8, color: "#64748b", textAlign: "center",
                           marginTop: 4, whiteSpace: "nowrap" }}>{d.label}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── KPI Card (single metric) ──────────────────────────────────────────────
function KpiCardChart({ data }) {
  if (!data?.length) return <EmptyChart />;
  const d = data[0];
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center",
                  justifyContent: "center", height: 120 }}>
      <div style={{ fontSize: 36, fontWeight: 800, color: "#fff",
                    letterSpacing: "-0.03em" }}>
        {Number(d.value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
      </div>
      <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>{d.label}</div>
    </div>
  );
}

// ── Empty / Error state ───────────────────────────────────────────────────
function EmptyChart({ message = "No data — ask a question to populate" }) {
  return (
    <div style={{ height: 120, display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center",
                  border: "1px dashed #1e3a5f", borderRadius: 8,
                  color: "#475569", fontSize: 12 }}>
      <span style={{ fontSize: 24, marginBottom: 8 }}>📊</span>
      {message}
    </div>
  );
}

// ── Main SmartChart component ─────────────────────────────────────────────
export default function SmartChart({ chart }) {
  if (!chart) return <EmptyChart />;

  const { type, title, data = [], selection_reason, error } = chart;

  const renderChart = () => {
    if (error && (!data || data.length === 0)) {
      return <EmptyChart message={error} />;
    }
    switch (type) {
      case "line":        return <LineChart data={data} color={VF.red} />;
      case "area":        return <LineChart data={data} color={VF.aqua} isArea />;
      case "bar":         return <BarChart data={data} />;
      case "donut":
      case "pie":         return <DonutChart data={data} />;
      case "waterfall":   return <WaterfallChart data={data} />;
      case "funnel":      return <FunnelChart data={data} />;
      case "stacked_bar": return <StackedBarChart data={data} />;
      case "kpi_card":    return <KpiCardChart data={data} />;
      default:            return <BarChart data={data} />;
    }
  };

  return (
    <div style={{
      background: "#1a2235", border: "1px solid #1e3a5f",
      borderRadius: 12, padding: 16,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center",
                    justifyContent: "space-between", marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "#fff",
                      display: "flex", alignItems: "center", gap: 7 }}>
          {title}
          {selection_reason && (
            <span style={{ fontSize: 9, fontWeight: 400, color: "#64748b" }}>
              ({selection_reason})
            </span>
          )}
        </div>
        <span style={{ fontSize: 9, color: "#64748b",
                       background: "rgba(255,255,255,0.05)",
                       padding: "2px 8px", borderRadius: 6,
                       border: "1px solid #1e3a5f" }}>
          {type}
        </span>
      </div>

      {/* Chart */}
      {renderChart()}
    </div>
  );
}
