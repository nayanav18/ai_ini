/**
 * PersonaSelector.jsx
 * The 5-persona switcher strip shown at the top of the Dashboard page.
 * Calls onSelect(persona_id) when user clicks a persona.
 *
 * Copy to: frontend/src/components/PersonaSelector.jsx
 */

const PERSONAS = [
  {
    id: "ceo",
    icon: "👔",
    name: "CEO",
    role: "Executive",
    color: "#E60000",
  },
  {
    id: "marketing",
    icon: "📢",
    name: "Marketing",
    role: "Director",
    color: "#EB6100",
  },
  {
    id: "product",
    icon: "📦",
    name: "Product",
    role: "Manager",
    color: "#00B0CA",
  },
  {
    id: "operations",
    icon: "⚙️",
    name: "Operations",
    role: "Manager",
    color: "#009900",
  },
  {
    id: "analyst",
    icon: "🔍",
    name: "Analyst",
    role: "Data",
    color: "#8B5CF6",
  },
];

export default function PersonaSelector({ activePersona, onSelect }) {
  return (
    <div style={{
      background: "#111827",
      borderBottom: "1px solid #1e3a5f",
      padding: "10px 24px",
      display: "flex",
      alignItems: "center",
      gap: 10,
      overflowX: "auto",
    }}>
      {/* Label */}
      <span style={{
        fontSize: 10, fontWeight: 700, color: "#64748b",
        textTransform: "uppercase", letterSpacing: "0.1em",
        whiteSpace: "nowrap", flexShrink: 0,
      }}>
        Your view:
      </span>

      {/* Persona buttons */}
      {PERSONAS.map(p => {
        const isActive = activePersona === p.id;
        return (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 10,
              border: `1px solid ${isActive ? p.color : "#253650"}`,
              background: isActive
                ? `${p.color}18`
                : "#1a2235",
              cursor: "pointer",
              transition: "all 0.2s",
              whiteSpace: "nowrap",
              flexShrink: 0,
              outline: "none",
            }}
            onMouseEnter={e => {
              if (!isActive) {
                e.currentTarget.style.borderColor = `${p.color}66`;
                e.currentTarget.style.background  = `${p.color}0d`;
              }
            }}
            onMouseLeave={e => {
              if (!isActive) {
                e.currentTarget.style.borderColor = "#253650";
                e.currentTarget.style.background  = "#1a2235";
              }
            }}
          >
            <span style={{ fontSize: 18 }}>{p.icon}</span>
            <div style={{ textAlign: "left" }}>
              <div style={{
                fontSize: 12, fontWeight: 700,
                color: isActive ? p.color : "#f0f4f8",
              }}>
                {p.name}
              </div>
              <div style={{ fontSize: 10, color: "#64748b" }}>
                {p.role}
              </div>
            </div>
            {isActive && (
              <span style={{
                width: 6, height: 6, borderRadius: "50%",
                background: p.color, marginLeft: 4, flexShrink: 0,
                boxShadow: `0 0 6px ${p.color}`,
              }} />
            )}
          </button>
        );
      })}
    </div>
  );
}
