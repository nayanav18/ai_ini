/**
 * StoryBanner.jsx
 * The AI narrative banner at the top of the dashboard.
 * Shows headline, what/why/todo tabs, citations and smart insights.
 *
 * Copy to: frontend/src/components/StoryBanner.jsx
 */
import { useState } from "react";

const SEVERITY_STYLES = {
  info:    { bg: "rgba(0,176,202,0.08)",  border: "rgba(0,176,202,0.3)",  color: "#22d3ee",  icon: "💡" },
  warning: { bg: "rgba(235,97,0,0.08)",   border: "rgba(235,97,0,0.3)",   color: "#fb923c",  icon: "⚠️" },
  alert:   { bg: "rgba(230,0,0,0.08)",    border: "rgba(230,0,0,0.3)",    color: "#f87171",  icon: "🚨" },
};

const CIT_STYLES = {
  Result:     { bg: "rgba(59,130,246,0.06)",   border: "rgba(59,130,246,0.22)",  label: "rgba(59,130,246,0.15)",  lcolor: "#60a5fa" },
  Driver:     { bg: "rgba(139,92,246,0.06)",   border: "rgba(139,92,246,0.22)",  label: "rgba(139,92,246,0.15)",  lcolor: "#a78bfa" },
  Market:     { bg: "rgba(0,176,202,0.06)",    border: "rgba(0,176,202,0.22)",   label: "rgba(0,176,202,0.15)",   lcolor: "#22d3ee" },
  Competitor: { bg: "rgba(245,158,11,0.06)",   border: "rgba(245,158,11,0.22)",  label: "rgba(245,158,11,0.15)",  lcolor: "#fbbf24" },
  Insight:    { bg: "rgba(230,0,0,0.06)",      border: "rgba(230,0,0,0.22)",     label: "rgba(230,0,0,0.15)",     lcolor: "#f87171" },
};

export default function StoryBanner({ story, personaName, loading }) {
  const [activeTab, setActiveTab] = useState("what");

  if (loading) {
    return (
      <div style={{ background: "linear-gradient(135deg, rgba(230,0,0,0.1), rgba(13,20,32,0.98))",
                    borderBottom: "1px solid #1e3a5f", padding: "16px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 44, height: 44, borderRadius: 11,
                        background: "rgba(230,0,0,0.1)", border: "1px solid rgba(230,0,0,0.2)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 20, flexShrink: 0 }}>📖</div>
          <div>
            <div style={{ width: 420, height: 14, background: "#1e3a5f",
                          borderRadius: 4, marginBottom: 8, animation: "pulse 1.5s infinite" }} />
            <div style={{ width: 280, height: 10, background: "#1e2d40",
                          borderRadius: 4, animation: "pulse 1.5s infinite" }} />
          </div>
        </div>
        <style>{`@keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.5} }`}</style>
      </div>
    );
  }

  if (!story) return null;

  const tabs = [
    { id: "what", label: "What Happened",  content: story.what_happened },
    { id: "why",  label: "Why It Happened", content: story.why },
    { id: "todo", label: "What To Do",     content: story.what_to_do },
  ];

  return (
    <div style={{
      background: "linear-gradient(135deg, rgba(230,0,0,0.12), rgba(13,20,32,0.98) 45%, rgba(59,130,246,0.05))",
      borderBottom: "1px solid #1e3a5f",
      padding: "16px 24px",
    }}>
      {/* Top row: icon + headline + confidence */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14,
                    marginBottom: 14 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 11, flexShrink: 0,
          background: "rgba(230,0,0,0.1)", border: "1px solid rgba(230,0,0,0.25)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20,
        }}>📖</div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#fff",
                        lineHeight: 1.45, marginBottom: 3 }}>
            {story.headline}
          </div>
          <div style={{ fontSize: 11, color: "#64748b" }}>
            {personaName} Story · AI Generated · Confidence: {story.confidence || 85}%
          </div>
        </div>

        {/* Smart insight badges */}
        <div style={{ display: "flex", gap: 7, flexShrink: 0, flexWrap: "wrap",
                      alignItems: "flex-start" }}>
          {(story.smart_insights || []).slice(0, 3).map((ins, i) => {
            const s = SEVERITY_STYLES[ins.severity] || SEVERITY_STYLES.info;
            return (
              <span key={i} style={{
                padding: "3px 11px", borderRadius: 999,
                fontSize: 10, fontWeight: 700,
                background: s.bg, border: `1px solid ${s.border}`, color: s.color,
              }}>
                {s.icon} {ins.title}
              </span>
            );
          })}
        </div>
      </div>

      {/* Story tabs */}
      <div style={{ display: "flex", gap: 5, marginBottom: 12 }}>
        {tabs.map(tab => (
          <button key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1, padding: "7px 10px", borderRadius: 8,
              border: `1px solid ${activeTab === tab.id ? "rgba(230,0,0,0.35)" : "#1e3a5f"}`,
              background: activeTab === tab.id ? "rgba(230,0,0,0.1)" : "transparent",
              color: activeTab === tab.id ? "#E60000" : "#64748b",
              fontSize: 11, fontWeight: 600, cursor: "pointer",
              transition: "all 0.15s", outline: "none",
            }}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active tab content */}
      <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.7,
                    marginBottom: 14 }}>
        {tabs.find(t => t.id === activeTab)?.content}
      </div>

      {/* Citations */}
      {(story.citations || []).length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 5,
                      marginBottom: 12 }}>
          {story.citations.slice(0, 4).map((cit, i) => {
            const s = CIT_STYLES[cit.type] || CIT_STYLES.Result;
            return (
              <div key={i} style={{
                display: "flex", gap: 8, padding: "7px 10px",
                borderRadius: 7, border: `1px solid ${s.border}`,
                background: s.bg, alignItems: "flex-start",
              }}>
                <span style={{
                  fontSize: 8, fontWeight: 800, padding: "2px 7px",
                  borderRadius: 999, border: `1px solid ${s.border}`,
                  background: s.label, color: s.lcolor,
                  whiteSpace: "nowrap", flexShrink: 0, marginTop: 1,
                }}>
                  {cit.icon} {cit.type}
                </span>
                <span style={{ fontSize: 11, color: "#94a3b8",
                               lineHeight: 1.45 }}>{cit.text}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Smart insights detail */}
      {(story.smart_insights || []).length > 0 && (
        <div style={{ display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                      gap: 8 }}>
          {story.smart_insights.map((ins, i) => {
            const s = SEVERITY_STYLES[ins.severity] || SEVERITY_STYLES.info;
            return (
              <div key={i} style={{
                background: s.bg, border: `1px solid ${s.border}`,
                borderRadius: 9, padding: "9px 12px",
                display: "flex", alignItems: "flex-start", gap: 8,
              }}>
                <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>
                  {s.icon}
                </span>
                <div>
                  <div style={{ fontSize: 8, fontWeight: 800, textTransform: "uppercase",
                                letterSpacing: "0.1em", padding: "1px 7px",
                                borderRadius: 999, border: `1px solid ${s.border}`,
                                background: s.bg, color: s.color,
                                display: "inline-block", marginBottom: 4 }}>
                    {ins.title}
                  </div>
                  <div style={{ fontSize: 11, color: "#94a3b8",
                                lineHeight: 1.55 }}>{ins.text}</div>
                  {ins.action && (
                    <div style={{ fontSize: 10, color: s.color,
                                  marginTop: 4, fontWeight: 600 }}>
                      → {ins.action}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
