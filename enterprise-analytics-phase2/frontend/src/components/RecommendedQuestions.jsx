/**
 * RecommendedQuestions.jsx
 * Clickable suggested questions at the bottom of the dashboard.
 * Clicking a question fires it to the chat.
 *
 * Copy to: frontend/src/components/RecommendedQuestions.jsx
 */

const QUESTION_ICONS = ["📊", "📈", "💧", "🔍", "📦", "⚔️", "📉", "💰", "🎯", "📡"];

export default function RecommendedQuestions({ questions = [], onAsk, persona }) {
  if (!questions.length) return null;

  return (
    <div style={{ marginTop: 16 }}>
      {/* Header */}
      <div style={{
        fontSize: 10, fontWeight: 700, color: "#64748b",
        textTransform: "uppercase", letterSpacing: "0.1em",
        marginBottom: 10,
        display: "flex", alignItems: "center", gap: 10,
      }}>
        💬 {persona ? `${persona} Recommended Analysis` : "Recommended Analysis"}
        <div style={{ flex: 1, height: 1, background: "#1e3a5f" }} />
      </div>

      {/* Question cards */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        gap: 8,
      }}>
        {questions.slice(0, 6).map((q, i) => (
          <div
            key={i}
            onClick={() => onAsk && onAsk(q)}
            style={{
              background: "#1a2235",
              border: "1px solid #1e3a5f",
              borderRadius: 9,
              padding: 12,
              cursor: "pointer",
              transition: "all 0.15s",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = "rgba(230,0,0,0.4)";
              e.currentTarget.style.background = "rgba(230,0,0,0.04)";
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = "#1e3a5f";
              e.currentTarget.style.background = "#1a2235";
              e.currentTarget.style.transform = "translateY(0)";
            }}
          >
            <div style={{ fontSize: 15, marginBottom: 5 }}>
              {QUESTION_ICONS[i % QUESTION_ICONS.length]}
            </div>
            <div style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.4 }}>
              {q}
            </div>
            <div style={{ fontSize: 10, color: "#E60000", marginTop: 6,
                          fontWeight: 600 }}>
              → Ask this
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
