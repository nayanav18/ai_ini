/**
 * ClarificationDialog.jsx
 * Shows when guardrail detects an ambiguous query (e.g. "profitability").
 * Renders column option cards — user clicks one to refine their query.
 *
 * Copy to: frontend/src/components/ClarificationDialog.jsx
 *
 * Usage in ChatView.jsx:
 *   if (response.is_clarification_needed) {
 *     return <ClarificationDialog response={response} onSelect={handleClarify} />
 *   }
 */

export default function ClarificationDialog({ response, onSelect }) {
  if (!response?.is_clarification_needed) return null;

  const {
    clarification_question,
    matching_columns = [],
    original_query,
  } = response;

  return (
    <div style={{
      background: "#1a2235",
      border: "1px solid rgba(0,176,202,0.3)",
      borderRadius: 14,
      padding: 18,
      maxWidth: 520,
    }}>
      {/* Bot icon + question */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10,
                    marginBottom: 14 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 10, flexShrink: 0,
          background: "rgba(0,176,202,0.12)", border: "1px solid rgba(0,176,202,0.3)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16,
        }}>🤔</div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#22d3ee",
                        textTransform: "uppercase", letterSpacing: "0.08em",
                        marginBottom: 4 }}>
            Clarification needed
          </div>
          <div style={{ fontSize: 13, color: "#f0f4f8", lineHeight: 1.5 }}>
            {clarification_question}
          </div>
        </div>
      </div>

      {/* Column options */}
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {matching_columns.map((col, i) => (
          <button
            key={i}
            onClick={() => {
              // Build a refined query replacing the ambiguous term
              const refined = `${original_query} (using ${col.column})`;
              onSelect && onSelect(refined, col.column);
            }}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "11px 14px",
              borderRadius: 9,
              border: "1px solid #253650",
              background: "#111827",
              cursor: "pointer",
              transition: "all 0.15s",
              textAlign: "left",
              outline: "none",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = "rgba(230,0,0,0.4)";
              e.currentTarget.style.background = "rgba(230,0,0,0.06)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = "#253650";
              e.currentTarget.style.background = "#111827";
            }}
          >
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#f0f4f8",
                            fontFamily: "monospace", marginBottom: 2 }}>
                {col.column}
              </div>
              <div style={{ fontSize: 11, color: "#64748b" }}>
                {col.description}
              </div>
            </div>
            <span style={{ color: "#E60000", fontSize: 14, flexShrink: 0,
                           marginLeft: 10 }}>→</span>
          </button>
        ))}
      </div>

      {/* Original query label */}
      {original_query && (
        <div style={{ marginTop: 10, fontSize: 10, color: "#475569" }}>
          Original query: "{original_query}"
        </div>
      )}
    </div>
  );
}
