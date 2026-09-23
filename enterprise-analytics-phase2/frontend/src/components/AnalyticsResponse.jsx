import { useState } from "react";
import MiniChart from "./MiniChart";

function KPICard({ kpi }) {
  const up = kpi.trend === "up", down = kpi.trend === "down";
  return (
    <div style={{ background: "linear-gradient(135deg,#111827,#0f172a)", border: "1px solid #1e3a5f", borderRadius: 12, padding: "14px 18px", flex: 1, minWidth: 130 }}>
      <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>{kpi.label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.02em" }}>{kpi.value}</div>
      <div style={{ fontSize: 11, marginTop: 5, color: up ? "#22c55e" : down ? "#ef4444" : "#94a3b8", fontWeight: 600 }}>
        {up ? "↑" : down ? "↓" : "→"} {kpi.change}
      </div>
    </div>
  );
}

function Badge({ text, color }) {
  const c = {
    blue:   ["rgba(59,130,246,0.12)",  "#60a5fa",  "rgba(59,130,246,0.25)"],
    green:  ["rgba(34,197,94,0.1)",    "#4ade80",  "rgba(34,197,94,0.25)" ],
    amber:  ["rgba(245,158,11,0.12)",  "#fbbf24",  "rgba(245,158,11,0.25)"],
    red:    ["rgba(239,68,68,0.1)",    "#f87171",  "rgba(239,68,68,0.25)" ],
    purple: ["rgba(168,85,247,0.12)",  "#c084fc",  "rgba(168,85,247,0.25)"],
    gray:   ["rgba(100,116,139,0.12)", "#94a3b8",  "rgba(100,116,139,0.2)"],
  }[color] || ["rgba(100,116,139,0.12)", "#94a3b8", "rgba(100,116,139,0.2)"];
  return (
    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 999,
      background: c[0], color: c[1], border: `1px solid ${c[2]}`, whiteSpace: "nowrap" }}>
      {text}
    </span>
  );
}

function Citation({ icon, color, label, text }) {
  const styles = {
    blue:   { bg: "rgba(59,130,246,0.07)",  border: "rgba(59,130,246,0.18)",  lc: "#60a5fa"  },
    amber:  { bg: "rgba(245,158,11,0.07)",  border: "rgba(245,158,11,0.18)",  lc: "#fbbf24"  },
    purple: { bg: "rgba(168,85,247,0.07)",  border: "rgba(168,85,247,0.18)",  lc: "#c084fc"  },
    green:  { bg: "rgba(34,197,94,0.07)",   border: "rgba(34,197,94,0.18)",   lc: "#4ade80"  },
    red:    { bg: "rgba(239,68,68,0.07)",   border: "rgba(239,68,68,0.18)",   lc: "#f87171"  },
    cyan:   { bg: "rgba(6,182,212,0.07)",   border: "rgba(6,182,212,0.18)",   lc: "#22d3ee"  },
  }[color] || { bg: "rgba(59,130,246,0.07)", border: "rgba(59,130,246,0.18)", lc: "#60a5fa" };
  return (
    <div style={{ display: "flex", gap: 8, padding: "6px 10px", background: styles.bg, borderRadius: 7, border: `1px solid ${styles.border}`, alignItems: "flex-start" }}>
      <span style={{ fontSize: 12, flexShrink: 0, marginTop: 1 }}>{icon}</span>
      <div style={{ flex: 1 }}>
        {label && <span style={{ fontSize: 10, fontWeight: 700, color: styles.lc, textTransform: "uppercase", letterSpacing: "0.06em", marginRight: 6 }}>{label}</span>}
        <span style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.55 }}>{text}</span>
      </div>
    </div>
  );
}

const ic = v => v === "High" ? "red" : v === "Medium" ? "amber" : "green";
const tc = t => t === "Strategic" ? "blue" : t === "Tactical" ? "amber" : "red";

export default function AnalyticsResponse({ data, onSaveInsight, onSuggestedQuery }) {
  const [showDetails, setShowDetails] = useState(false);

  const bullets     = data.summary_bullets     || [];
  const actions     = data.recommendations     || [];
  const risks       = data.risks               || [];
  const suggested   = data.suggested_questions || [];
  const causes      = data.root_causes         || [];
  const market      = data.market_analysis     || {};
  const competitive = data.competitor_analysis || {};
  const competitors = competitive.competitors  || [];

  // Limit chart to last 6 months
  const chart6m = data.chart ? {
    ...data.chart,
    data: (data.chart.data || []).slice(-6)
  } : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

      {/* ── Row 1: KPIs + 6-month Chart ── */}
      <div style={{ display: "flex", gap: 10, alignItems: "stretch" }}>
        {data.kpis?.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0, width: 175 }}>
            {data.kpis.map((k, i) => <KPICard key={i} kpi={k} />)}
          </div>
        )}
        {chart6m && (
          <div style={{ flex: 1, background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 12, padding: "12px 16px", minWidth: 0 }}>
            <MiniChart chart={chart6m} />
          </div>
        )}
      </div>

      {/* ── Executive Summary ── */}
      <div style={{ background: "#0a1220", border: "1px solid #1e3a5f", borderRadius: 12, padding: "14px 18px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 9 }}>
          <div style={{ fontSize: 10, color: "#3b82f6", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>📋 Executive Summary</div>
          <button onClick={() => setShowDetails(!showDetails)}
            style={{ fontSize: 10, color: "#475569", background: "transparent", border: "1px solid #1e3a5f", borderRadius: 6, padding: "2px 10px", cursor: "pointer" }}>
            {showDetails ? "Less ▲" : "Full Analysis ▼"}
          </button>
        </div>

        {/* What happened */}
        <p style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600, lineHeight: 1.65, margin: "0 0 10px" }}>
          {data.what_happened}
        </p>

        {/* ── Always visible: 5 citation bullets ── */}
        {bullets.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {bullets.map((b, i) => {
              const icons  = ["📊","🔑","🌍","⚔️","⚡"];
              const colors = ["blue","purple","cyan","amber","green"];
              const labels = ["Result","Driver","Market","Competitor","Insight"];
              return <Citation key={i} icon={icons[i]||"•"} color={colors[i]||"blue"} label={labels[i]} text={b.replace(/^[•·]\s*/,"")} />;
            })}
          </div>
        ) : (
          /* Fallback if no bullets — show inline citations from raw fields */
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {data.business_context && (
              <Citation icon="📊" color="blue" label="Result" text={data.business_context} />
            )}
            {causes[0] && (
              <Citation icon="🔑" color="purple" label="Driver" text={`${causes[0].driver} — ${causes[0].detail}`} />
            )}
            {market.market_position && (
              <Citation icon="🌍" color="cyan" label="Market" text={market.market_position} />
            )}
            {competitors[0] && (
              <Citation icon="⚔️" color="amber" label="Competitor" text={`${competitors[0].name}: ${competitors[0].insight} [${competitors[0].threat_level} threat]`} />
            )}
            {competitive.competitive_risk && (
              <Citation icon="⚡" color="green" label="Insight" text={competitive.competitive_risk} />
            )}
          </div>
        )}

        {/* ── Expandable full analysis ── */}
        {showDetails && (
          <div style={{ marginTop: 12, borderTop: "1px solid #1e3a5f", paddingTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>

            {/* Root cause reasoning */}
            {(causes.length > 0 || data.why_it_happened) && (
              <div>
                <div style={{ fontSize: 10, color: "#a855f7", fontWeight: 700, textTransform: "uppercase", marginBottom: 6 }}>🔬 Root Cause Analysis</div>
                {data.why_it_happened && (
                  <p style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.6, margin: "0 0 8px" }}>{data.why_it_happened}</p>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {causes.map((rc, i) => (
                    <Citation key={i} icon="→" color="purple" label={rc.driver}
                      text={`${rc.detail} [${rc.impact} impact · ${rc.confidence}% confidence · ${rc.category}]`} />
                  ))}
                </div>
              </div>
            )}

            {/* Market analysis citations */}
            {market.market_position && (
              <div>
                <div style={{ fontSize: 10, color: "#06b6d4", fontWeight: 700, textTransform: "uppercase", marginBottom: 6 }}>🌍 Market Analysis</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <Citation icon="📍" color="cyan" label="Position" text={market.market_position} />
                  {market.market_trends?.map((t, i) => (
                    <Citation key={i} icon="→" color="cyan" label={`Trend ${i+1}`} text={t} />
                  ))}
                  {market.growth_outlook && (
                    <Citation icon="📈" color="cyan" label="Outlook" text={market.growth_outlook} />
                  )}
                </div>
              </div>
            )}

            {/* Competitor analysis citations */}
            {competitive.competitive_landscape && (
              <div>
                <div style={{ fontSize: 10, color: "#f59e0b", fontWeight: 700, textTransform: "uppercase", marginBottom: 6 }}>⚔️ Competitor Analysis</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <Citation icon="🗺️" color="amber" label="Landscape" text={competitive.competitive_landscape} />
                  {competitors.map((c, i) => (
                    <Citation key={i} icon="🏢" color="amber" label={c.name}
                      text={`${c.position} — ${c.insight} [${c.threat_level} threat]`} />
                  ))}
                  {competitive.competitive_advantage && (
                    <Citation icon="✅" color="green" label="Our Advantage" text={competitive.competitive_advantage} />
                  )}
                  {competitive.competitive_risk && (
                    <Citation icon="⚠️" color="red" label="Key Risk" text={competitive.competitive_risk} />
                  )}
                </div>
              </div>
            )}

            {/* Strategic direction */}
            {data.what_to_do && (
              <Citation icon="🎯" color="green" label="Strategic Direction" text={data.what_to_do} />
            )}
          </div>
        )}
      </div>

      {/* ── Actions + Risks side by side ── */}
      {(actions.length > 0 || risks.length > 0) && (
        <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 10 }}>
          {actions.length > 0 && (
            <div style={{ background: "#0a1220", border: "1px solid #1e3a5f", borderRadius: 12, padding: "11px 14px" }}>
              <div style={{ fontSize: 10, color: "#22c55e", fontWeight: 700, textTransform: "uppercase", marginBottom: 8 }}>💡 Action Plan</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {actions.map((r, i) => (
                  <div key={i} style={{ padding: "8px 10px", background: "rgba(34,197,94,0.04)", borderRadius: 8, border: "1px solid rgba(34,197,94,0.1)" }}>
                    <div style={{ display: "flex", gap: 5, marginBottom: 4, flexWrap: "wrap", alignItems: "center" }}>
                      <Badge text={r.priority||"P2"} color={r.priority==="P1"?"red":"amber"} />
                      <Badge text={r.type} color={tc(r.type)} />
                      {r.timeline && <span style={{ fontSize: 9, color: "#374151" }}>⏱ {r.timeline}</span>}
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0", marginBottom: 3 }}>{r.action}</div>
                    <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.5 }}>{r.detail}</div>
                    {r.expected_impact && (
                      <div style={{ fontSize: 10, color: "#4ade80", marginTop: 4 }}>Expected: {r.expected_impact}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {risks.length > 0 && (
            <div style={{ background: "#0a1220", border: "1px solid #1e3a5f", borderRadius: 12, padding: "11px 14px" }}>
              <div style={{ fontSize: 10, color: "#ef4444", fontWeight: 700, textTransform: "uppercase", marginBottom: 8 }}>⚠️ Risks</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {risks.map((r, i) => (
                  <div key={i} style={{ padding: "8px 10px", background: "rgba(239,68,68,0.04)", borderRadius: 8, border: "1px solid rgba(239,68,68,0.1)" }}>
                    <div style={{ display: "flex", gap: 5, marginBottom: 3 }}>
                      <Badge text={r.severity} color={ic(r.severity)} />
                      <div style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0", lineHeight: 1.35 }}>{r.risk}</div>
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.45, borderLeft: "2px solid rgba(239,68,68,0.2)", paddingLeft: 7 }}>
                      {r.mitigation}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Suggested Questions ── */}
      {suggested.length > 0 && (
        <div style={{ background: "#0a1220", border: "1px solid #1e3a5f", borderRadius: 10, padding: "10px 14px" }}>
          <div style={{ fontSize: 10, color: "#60a5fa", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
            💬 Ask Next
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {suggested.map((q, i) => (
              <button key={i} onClick={() => onSuggestedQuery && onSuggestedQuery(q)}
                style={{ padding: "5px 12px", borderRadius: 999, border: "1px solid #1e3a5f",
                  background: "rgba(59,130,246,0.06)", color: "#64748b", fontSize: 11,
                  cursor: "pointer", fontWeight: 500, lineHeight: 1.4 }}
                onMouseEnter={e => { e.currentTarget.style.borderColor="#3b82f6"; e.currentTarget.style.color="#93c5fd"; e.currentTarget.style.background="rgba(59,130,246,0.12)"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor="#1e3a5f"; e.currentTarget.style.color="#64748b"; e.currentTarget.style.background="rgba(59,130,246,0.06)"; }}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Action Buttons ── */}
      {data.actions?.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {data.actions.map((a, i) => (
            <button key={i}
              onClick={() => a==="Save Insight"&&onSaveInsight ? onSaveInsight() : alert(`Action: ${a}`)}
              style={{ padding: "5px 12px", borderRadius: 999, border: "1px solid #1e3a5f", background: "#0a1628", color: "#64748b", fontSize: 11, cursor: "pointer", fontWeight: 500 }}
              onMouseEnter={e => { e.currentTarget.style.borderColor="#3b82f6"; e.currentTarget.style.color="#60a5fa"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor="#1e3a5f"; e.currentTarget.style.color="#64748b"; }}>
              {a}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
