/*
import { timeAgo } from "../utils/helpers";
import MiniChart from "./MiniChart";
export default function InsightsView({ insights, onDelete,onAddToBuilder }) {
  if (insights.length === 0) return (
    <div style={{ textAlign: "center", paddingTop: 80, color: "#475569" }}>
      <div style={{ fontSize: 36, marginBottom: 12 }}>💡</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: "#64748b" }}>No saved insights yet</div>
      <div style={{ fontSize: 13, marginTop: 6 }}>Click "Save Insight" on any analytics response to store it here.</div>
    </div>
  );

  return (
    <div style={{ padding: 24, overflowY: "auto", height: "100%" }}>
      <div style={{ fontSize: 11, color: "#3b82f6", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 20 }}>
        Saved Insights ({insights.length})
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {insights.map((ins) => (
          <div key={ins.id} style={{ background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 12, padding: "16px 18px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>{ins.query}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 10, color: "#475569", whiteSpace: "nowrap" }}>{timeAgo(ins.ts)}</span>
                {onDelete && (
                  <button onClick={() => onDelete(ins.id)} style={{ fontSize: 11, color: "#374151", background: "transparent", border: "none", cursor: "pointer", padding: "2px 6px" }}
                    onMouseEnter={e => e.currentTarget.style.color = "#ef4444"}
                    onMouseLeave={e => e.currentTarget.style.color = "#374151"}>✕</button>
                )}
              </div>
            </div>
            <div style={{ fontSize: 12, color: "#64748b", lineHeight: 1.5, marginBottom: 10 }}>
              {ins.data?.what_happened}
            </div>
            {ins.data?.chart && (
  <div
    style={{
      marginBottom: 12,
      background: "#0a1220",
      border: "1px solid #1e3a5f",
      borderRadius: 10,
      padding: "12px",
    }}
  >
    <MiniChart chart={ins.data.chart} />
  </div>
)}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 999, background: "rgba(59,130,246,0.1)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.15)" }}>
                {ins.dataset}
              </span>
              {ins.data?.kpis?.slice(0, 3).map((k, j) => (
                <span key={j} style={{ fontSize: 10, padding: "2px 8px", borderRadius: 999, background: "rgba(34,197,94,0.08)", color: "#4ade80", border: "1px solid rgba(34,197,94,0.15)" }}>
                  {k.label}: {k.value}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
*/
import { timeAgo } from "../utils/helpers";
import MiniChart from "./MiniChart";

export default function InsightsView({
  insights,
  onDelete,
  onAddToBuilder,
}) {
  if (insights.length === 0) {
    return (
      <div style={{ textAlign: "center", paddingTop: 80, color: "#475569" }}>
        <div style={{ fontSize: 36, marginBottom: 12 }}>💡</div>
        <div
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: "#64748b",
          }}
        >
          No saved insights yet
        </div>
        <div style={{ fontSize: 13, marginTop: 6 }}>
          Click "Save Insight" on any analytics response to store it here.
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, overflowY: "auto", height: "100%" }}>
      <div
        style={{
          fontSize: 11,
          color: "#3b82f6",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: 20,
        }}
      >
        Saved Insights ({insights.length})
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {insights.map((ins) => (
          <div
            key={ins.id}
            style={{
              background: "#0f172a",
              border: "1px solid #1e3a5f",
              borderRadius: 12,
              padding: "16px 18px",
            }}
          >
            {/* Header */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 8,
              }}
            >
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#e2e8f0",
                }}
              >
                {ins.query}
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span
                  style={{
                    fontSize: 10,
                    color: "#475569",
                    whiteSpace: "nowrap",
                  }}
                >
                  {timeAgo(ins.ts)}
                </span>

                {onDelete && (
                  <button
                    onClick={() => onDelete(ins.id)}
                    style={{
                      fontSize: 11,
                      color: "#374151",
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      padding: "2px 6px",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = "#ef4444";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = "#374151";
                    }}
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>

            {/* Summary */}
            <div
              style={{
                fontSize: 12,
                color: "#64748b",
                lineHeight: 1.5,
                marginBottom: 10,
              }}
            >
              {ins.data?.what_happened}
            </div>

            {/* Chart */}
            {ins.data?.chart && (
              <div
                style={{
                  marginBottom: 12,
                  background: "#0a1220",
                  border: "1px solid #1e3a5f",
                  borderRadius: 10,
                  padding: "12px",
                }}
              >
                <MiniChart chart={ins.data.chart} />
              </div>
            )}

            {/* Tags */}
            <div
              style={{
                display: "flex",
                gap: 6,
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 8px",
                  borderRadius: 999,
                  background: "rgba(59,130,246,0.1)",
                  color: "#60a5fa",
                  border: "1px solid rgba(59,130,246,0.15)",
                }}
              >
                {ins.dataset}
              </span>

              {ins.data?.kpis?.slice(0, 3).map((k, j) => (
                <span
                  key={j}
                  style={{
                    fontSize: 10,
                    padding: "2px 8px",
                    borderRadius: 999,
                    background: "rgba(34,197,94,0.08)",
                    color: "#4ade80",
                    border: "1px solid rgba(34,197,94,0.15)",
                  }}
                >
                  {k.label}: {k.value}
                </span>
              ))}
            </div>

            {/* Add To Builder Button */}
            {ins.data?.chart && (
              <button
                onClick={() => onAddToBuilder(ins)}
                style={{
                  marginTop: 12,
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid #3b82f6",
                  background: "rgba(59,130,246,0.08)",
                  color: "#60a5fa",
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                ➕ Add To Builder
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}