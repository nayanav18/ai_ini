import { AGENT_PIPELINE } from "../utils/helpers";

export default function AgentStatusPill({ steps }) {
  const done = Object.values(steps).filter((s) => s === "done").length;
  const running = AGENT_PIPELINE.find((a) => steps[a.id] === "running");
  if (done === AGENT_PIPELINE.length) return null;

  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 8,
      padding: "5px 13px", borderRadius: 999,
      background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)",
      marginBottom: 10,
    }}>
      <div style={{ display: "flex", gap: 3, alignItems: "center" }}>
        {AGENT_PIPELINE.map((a) => (
          <div key={a.id} style={{
            width: steps[a.id] === "done" ? 6 : steps[a.id] === "running" ? 8 : 5,
            height: steps[a.id] === "done" ? 6 : steps[a.id] === "running" ? 8 : 5,
            borderRadius: 999,
            background: steps[a.id] === "done" ? "#22c55e" : steps[a.id] === "running" ? "#f59e0b" : "#1e3a5f",
            transition: "all 0.3s",
            animation: steps[a.id] === "running" ? "pulse 1s ease infinite" : "none",
          }} />
        ))}
      </div>
      <span style={{ fontSize: 11, color: "#60a5fa", fontWeight: 500 }}>
        {running ? `${running.icon} ${running.label} Agent…` : `${done}/${AGENT_PIPELINE.length} agents`}
      </span>
    </div>
  );
}
