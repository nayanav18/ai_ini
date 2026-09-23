import { useState } from "react";
import { DATASETS, timeAgo } from "../utils/helpers";

const NAV = [
  { id: "chat",       icon: "💬", label: "Chat" },
  { id: "history",    icon: "🕐", label: "History" },
  { id: "insights",   icon: "💡", label: "Insights" },
  { id: "builder",    icon: "📈", label: "Builder" },
  { id: "dashboards", icon: "📊", label: "Dashboards" },
];

export default function Sidebar({
  activeNav, setActiveNav,
  selectedDataset, setSelectedDataset,
  conversations, activeConvId, openConv, newChat,
  savedInsightsCount, historyLoading,
}) {
  const [showDatasetMenu, setShowDatasetMenu] = useState(false);

  return (
    <div style={{
      width: "240px", flexShrink: 0, background: "#07111f",
      borderRight: "1px solid #0d1f35", display: "flex", flexDirection: "column",
      height: "100vh", position: "sticky", top: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: "16px 16px 12px", borderBottom: "1px solid #0d1f35" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: "linear-gradient(135deg,#1d4ed8,#7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>⬡</div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.02em" }}>Analytics AI</div>
            <div style={{ fontSize: 9, color: "#3b82f6", fontWeight: 600, letterSpacing: "0.08em" }}>ENTERPRISE · VERTEX AI</div>
          </div>
        </div>
      </div>

      {/* New Chat */}
      <div style={{ padding: "12px 12px 6px" }}>
        <button onClick={newChat} style={{
          width: "100%", padding: 9, borderRadius: 9,
          background: "linear-gradient(135deg,#1d4ed8,#7c3aed)", border: "none",
          color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer",
          display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
        }}>
          <span style={{ fontSize: 16 }}>+</span> New Chat
        </button>
      </div>

      {/* Nav */}
      <div style={{ padding: "4px 8px" }}>
        {NAV.map((item) => (
          <button key={item.id} onClick={() => setActiveNav(item.id)} style={{
            width: "100%", display: "flex", alignItems: "center", gap: 10,
            padding: "9px 10px", borderRadius: 8, border: "none",
            background: activeNav === item.id ? "rgba(59,130,246,0.12)" : "transparent",
            color: activeNav === item.id ? "#60a5fa" : "#64748b",
            fontSize: 13, fontWeight: activeNav === item.id ? 600 : 500,
            cursor: "pointer", marginBottom: 2, textAlign: "left",
            borderLeft: activeNav === item.id ? "2px solid #3b82f6" : "2px solid transparent",
          }}>
            <span style={{ fontSize: 15 }}>{item.icon}</span>
            {item.label}
            {item.id === "insights" && savedInsightsCount > 0 && (
              <span style={{ marginLeft: "auto", fontSize: 10, background: "rgba(59,130,246,0.18)", color: "#60a5fa", borderRadius: 999, padding: "1px 6px" }}>
                {savedInsightsCount}
              </span>
            )}
            {item.id === "history" && historyLoading ? (
              <span style={{ marginLeft: "auto", fontSize: 10, color: "#64748b" }}>Loading…</span>
            ) : item.id === "history" && conversations.length > 0 && (
              <span style={{ marginLeft: "auto", fontSize: 10, background: "rgba(100,116,139,0.18)", color: "#64748b", borderRadius: 999, padding: "1px 6px" }}>
                {conversations.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Recent conversations */}
      {conversations.length > 0 && (
        <div style={{ flex: 1, overflowY: "auto", padding: "6px 8px 0" }}>
          <div style={{ fontSize: 10, color: "#374151", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", padding: "4px 10px 6px" }}>
            {activeNav === "history" ? "All Conversations" : "Recent"}
          </div>
          {conversations.map((conv) => (
            <button key={conv.id} onClick={() => { openConv(conv.id); setActiveNav("chat"); }} style={{
              width: "100%", padding: "8px 10px", borderRadius: 8, border: "none",
              background: conv.id === activeConvId ? "rgba(59,130,246,0.1)" : "transparent",
              color: conv.id === activeConvId ? "#93c5fd" : "#64748b",
              fontSize: 12, cursor: "pointer", textAlign: "left",
              display: "flex", flexDirection: "column", gap: 2, marginBottom: 2,
              borderLeft: conv.id === activeConvId ? "2px solid #3b82f6" : "2px solid transparent",
            }}>
              <span style={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{conv.title}</span>
              <span style={{ fontSize: 10, color: "#374151" }}>{conv.dataset?.label} · {timeAgo(conv.ts)}</span>
            </button>
          ))}
        </div>
      )}

      {/* Dataset Selector */}
      <div style={{ padding: 12, borderTop: "1px solid #0d1f35", position: "relative" }}>
        <div style={{ fontSize: 9, color: "#374151", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>Dataset</div>
        <button onClick={() => setShowDatasetMenu(!showDatasetMenu)} style={{
          width: "100%", display: "flex", alignItems: "center", gap: 8,
          padding: "8px 10px", background: "#0f172a", border: "1px solid #1e3a5f",
          borderRadius: 8, cursor: "pointer", color: "#e2e8f0", fontSize: 12, fontWeight: 500,
        }}>
          <span>{selectedDataset.flag}</span>
          <span style={{ flex: 1, textAlign: "left", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{selectedDataset.label}</span>
          <span style={{ color: "#374151", fontSize: 9 }}>▾</span>
        </button>
        {showDatasetMenu && (
          <div style={{
            position: "absolute", bottom: "calc(100% - 12px)", left: 12, right: 12,
            background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 10,
            boxShadow: "0 -8px 24px rgba(0,0,0,0.5)", zIndex: 200, overflow: "hidden",
          }}>
            {DATASETS.map((ds) => (
              <button key={ds.id} onClick={() => { setSelectedDataset(ds); setShowDatasetMenu(false); }} style={{
                display: "flex", alignItems: "center", gap: 8, width: "100%",
                padding: "9px 14px", background: ds.id === selectedDataset.id ? "rgba(59,130,246,0.1)" : "transparent",
                border: "none", color: ds.id === selectedDataset.id ? "#60a5fa" : "#94a3b8",
                fontSize: 12, cursor: "pointer", textAlign: "left",
              }}>
                <span>{ds.flag}</span><span>{ds.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
