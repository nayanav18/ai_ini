/**
 * DashboardPage.jsx — Main persona dashboard page.
 * Fetches data from GET /api/v1/dashboard/{persona_id}
 * Shows: PersonaSelector → StoryBanner → KPIScoreboard → Charts → Questions
 *
 * Copy to: frontend/src/pages/DashboardPage.jsx
 * (or wherever your other page components live)
 *
 * Props from your router: none needed — manages own state
 * Optional prop: onAskQuestion(query) — fires query to chat
 */
import { useState, useEffect, useCallback } from "react";
import PersonaSelector    from "../components/PersonaSelector";
import StoryBanner        from "../components/StoryBanner";
import KPIScoreboard      from "../components/KPIScoreboard";
import SmartChart         from "../components/SmartChart";
import RecommendedQuestions from "../components/RecommendedQuestions";

// ── Config ────────────────────────────────────────────────────────────────
const API_BASE = "/api/v1";
const DEFAULT_PERSONA = "analyst";

// Layer tab colours per persona
const PERSONA_COLORS = {
  ceo:        "#E60000",
  marketing:  "#EB6100",
  product:    "#00B0CA",
  operations: "#009900",
  analyst:    "#8B5CF6",
};

export default function DashboardPage({ onAskQuestion }) {
  const [personaId,   setPersonaId]   = useState(DEFAULT_PERSONA);
  const [dashboard,   setDashboard]   = useState(null);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState(null);
  const [activeLayer, setActiveLayer] = useState(0);
  const [period,      setPeriod]      = useState("latest");
  const [lastRefresh, setLastRefresh] = useState(null);

  // ── Fetch dashboard data ─────────────────────────────────────────────
  const fetchDashboard = useCallback(async (pid, per, refresh = false) => {
    setLoading(true);
    setError(null);
    setActiveLayer(0);

    try {
      const params = new URLSearchParams({
        period:per,
        dataset_id: "ireland",
        refresh: refresh ? "true" : "false",
      });
      const res = await fetch(
        `${API_BASE}/dashboard/${pid}?${params}`,
        { headers: { "Content-Type": "application/json" } }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const data = await res.json();

console.log("========== DASHBOARD RESPONSE ==========");
console.log(data);
console.log("Layers:", data?.layers);
console.log("KPIs:", data?.kpis);
console.log("Charts:", data?.layers?.[0]?.charts);

setDashboard(data);
setLastRefresh(new Date());
    } catch (e) {
      setError(e.message);
      setDashboard(null);
    } finally {
      setLoading(false);
    }
  }, [period]);

  // Fetch on persona / period change
  useEffect(() => {
    fetchDashboard(personaId, period, false);
  }, [personaId, period]);

  // ── Handlers ─────────────────────────────────────────────────────────
  const handlePersonaChange = (pid) => {
    setPersonaId(pid);
    setDashboard(null);
  };

  const handleRefresh = () => {
    fetchDashboard(personaId, period, true);
  };

  const handleAskQuestion = (q) => {
    if (onAskQuestion) {
      onAskQuestion(q);
    } else {
      // Fallback: navigate to chat with query pre-filled
      const event = new CustomEvent("dashboard:ask", { detail: { query: q } });
      window.dispatchEvent(event);
    }
  };

  // ── Derived state ─────────────────────────────────────────────────────
  const layers = dashboard?.layers || [];
  const activeLayerData = layers[activeLayer] || null;
  const charts = activeLayerData?.charts || [];
  const accentColor = PERSONA_COLORS[personaId] || "#E60000";

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <div style={{
      background: "#06090f",
      minHeight: "100vh",
      color: "#f0f4f8",
      fontFamily: "Inter, system-ui, sans-serif",
    }}>

      {/* ── Persona Selector ── */}
      <PersonaSelector
        activePersona={personaId}
        onSelect={handlePersonaChange}
      />

      {/* ── Story Banner ── */}
      <StoryBanner
        story={dashboard?.story}
        personaName={dashboard?.persona_name || "Loading..."}
        loading={loading}
      />

      {/* ── Layer tabs + controls ── */}
      <div style={{
        background: "#111827",
        borderBottom: "1px solid #1e3a5f",
        padding: "0 24px",
        display: "flex",
        alignItems: "center",
        overflowX: "auto",
      }}>
        {/* Layer tabs */}
        {layers.map((layer, i) => (
          <button
            key={layer.id}
            onClick={() => setActiveLayer(i)}
            style={{
              padding: "10px 16px",
              fontSize: 11, fontWeight: 600,
              color: activeLayer === i ? accentColor : "#64748b",
              borderBottom: `2px solid ${activeLayer === i ? accentColor : "transparent"}`,
              background: "transparent",
              border: "none",
              borderBottom: `2px solid ${activeLayer === i ? accentColor : "transparent"}`,
              cursor: "pointer",
              whiteSpace: "nowrap",
              outline: "none",
              transition: "all 0.15s",
              display: "flex",
              alignItems: "center",
              gap: 5,
            }}
          >
            <span>{layer.icon}</span>
            <span>{layer.label}</span>
          </button>
        ))}

        {/* Right side controls */}
        <div style={{ marginLeft: "auto", display: "flex", gap: 7,
                      padding: "8px 0", flexShrink: 0 }}>
          {["latest", "Q2 2026", "YTD"].map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                padding: "4px 11px", borderRadius: 999,
                fontSize: 10, fontWeight: 600, cursor: "pointer",
                border: `1px solid ${period === p ? accentColor : "#253650"}`,
                background: period === p ? `${accentColor}18` : "transparent",
                color: period === p ? accentColor : "#64748b",
                outline: "none", transition: "all 0.15s",
              }}
            >
              {p}
            </button>
          ))}

          <button
            onClick={handleRefresh}
            disabled={loading}
            style={{
              padding: "4px 12px", borderRadius: 999,
              fontSize: 10, fontWeight: 600, cursor: loading ? "wait" : "pointer",
              border: "1px solid #253650",
              background: "transparent",
              color: loading ? "#475569" : "#64748b",
              outline: "none", transition: "all 0.15s",
            }}
          >
            {loading ? "⟳ Loading..." : "↺ Refresh"}
          </button>

          {lastRefresh && (
            <span style={{ fontSize: 10, color: "#475569",
                           display: "flex", alignItems: "center" }}>
              {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* ── Main content ── */}
      <div style={{ maxWidth: 1360, margin: "0 auto", padding: "20px 24px" }}>

        {/* Error state */}
        {error && (
          <div style={{
            background: "rgba(230,0,0,0.08)", border: "1px solid rgba(230,0,0,0.3)",
            borderRadius: 10, padding: "14px 16px", marginBottom: 16,
            color: "#f87171", fontSize: 13,
          }}>
            ⚠ {error} —{" "}
            <span
              onClick={handleRefresh}
              style={{ textDecoration: "underline", cursor: "pointer" }}
            >
              try again
            </span>
          </div>
        )}

        {/* KPI Scoreboard */}
        <KPIScoreboard
          kpis={dashboard?.kpis}
          loading={loading}
        />

        {/* Charts grid */}
        {loading ? (
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 12, marginBottom: 14,
          }}>
            {[1, 2, 3, 4].map(i => (
              <div key={i} style={{
                background: "#1a2235", border: "1px solid #1e3a5f",
                borderRadius: 12, padding: 16, height: 200,
                display: "flex", flexDirection: "column", gap: 12,
              }}>
                <div style={{ width: "60%", height: 12, background: "#1e3a5f",
                              borderRadius: 4, animation: "pulse 1.5s infinite" }} />
                <div style={{ flex: 1, background: "#111827", borderRadius: 8 }} />
              </div>
            ))}
          </div>
        ) : charts.length > 0 ? (
          <div style={{
            display: "grid",
            gridTemplateColumns: charts.length === 1
              ? "1fr"
              : charts.length === 2
              ? "1fr 1fr"
              : "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 12, marginBottom: 14,
          }}>
            {charts.map((chart, i) => (
              <SmartChart key={i} chart={chart} />
            ))}
          </div>
        ) : !loading && !error && (
          <div style={{
            background: "#1a2235", border: "1px dashed #1e3a5f",
            borderRadius: 12, padding: 40, marginBottom: 14,
            textAlign: "center", color: "#475569",
          }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📊</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#64748b",
                          marginBottom: 6 }}>
              No chart data yet
            </div>
            <div style={{ fontSize: 12, color: "#475569" }}>
              Ask a question below to populate your dashboard with live data
            </div>
          </div>
        )}

        {/* Recommended Questions */}
        <RecommendedQuestions
          questions={dashboard?.suggested_questions || []}
          onAsk={handleAskQuestion}
          persona={dashboard?.persona_name}
        />

        {/* Cache indicator */}
        {dashboard?.from_cache && (
          <div style={{ textAlign: "center", marginTop: 12,
                        fontSize: 10, color: "#475569" }}>
            ⚡ Served from cache · Generated in {dashboard.duration_ms}ms ·
            <span
              onClick={handleRefresh}
              style={{ color: "#64748b", cursor: "pointer",
                       textDecoration: "underline", marginLeft: 4 }}
            >
              refresh
            </span>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.5} }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 3px; }
      `}</style>
    </div>
  );
}
