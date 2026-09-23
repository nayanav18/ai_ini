import { useRef, useEffect, useState } from "react";
import AgentStatusPill from "./AgentStatusPill";
import AnalyticsResponse from "./AnalyticsResponse";
import { SUGGESTED_QUERIES } from "../utils/helpers";

export default function ChatView({ messages, loading, agentSteps, activeConv, selectedDataset, onSend, onNewChat, onSaveInsight, prefillQuery, historyLoading }) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  useEffect(() => {
    if (prefillQuery) setInput(prefillQuery);
  }, [prefillQuery]);

  const handleSend = () => {
    if (!input.trim() || loading) return;
    onSend(input);
    setInput("");
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Top bar */}
      <div style={{ padding: "11px 24px", borderBottom: "1px solid #0d1f35", display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(6,13,26,0.95)", backdropFilter: "blur(8px)" }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#64748b" }}>
          {activeConv ? activeConv.title : "Enterprise Command Center"}
        </div>
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#60a5fa" }}>
            <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span>
            Agents working…
          </div>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
        {historyLoading && messages.length === 0 && (
          <div style={{ textAlign: "center", color: "#475569", fontSize: 12, paddingTop: 18 }}>
            Restoring your conversation history…
          </div>
        )}
        {messages.length === 0 && (
          <div style={{ textAlign: "center", paddingTop: 60 }}>
            <div style={{ fontSize: 38, marginBottom: 14 }}>⬡</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.03em", margin: "0 0 8px" }}>
              Enterprise Command Center
            </h2>
            <p style={{ color: "#475569", fontSize: 13, maxWidth: 400, margin: "0 auto 28px" }}>
              Ask any business question about <span style={{ color: "#60a5fa" }}>{selectedDataset.label}</span>.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 520, margin: "0 auto" }}>
              {SUGGESTED_QUERIES.map((q, i) => (
                <button key={i} onClick={() => onSend(q)} style={{ padding: "7px 15px", background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 999, color: "#64748b", fontSize: 12, cursor: "pointer", fontWeight: 500 }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor="#3b82f6"; e.currentTarget.style.color="#60a5fa"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor="#1e3a5f"; e.currentTarget.style.color="#64748b"; }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: 20 }}>
            {msg.role === "user" ? (
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <div style={{ maxWidth: "68%", padding: "10px 16px", background: "linear-gradient(135deg,#1d4ed8,#1e40af)", borderRadius: "16px 16px 4px 16px", color: "#fff", fontSize: 13, lineHeight: 1.55 }}>
                  {msg.content}
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", gap: 11 }}>
                <div style={{ width: 26, height: 26, borderRadius: 7, flexShrink: 0, background: "linear-gradient(135deg,#1d4ed8,#7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, marginTop: 2 }}>⬡</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {i === messages.length - 1 && loading && <AgentStatusPill steps={agentSteps} />}
                  {msg.isStructured ? (
                  <AnalyticsResponse
                    data={msg.content}
                    onSaveInsight={() => onSaveInsight(msg)}
                    onSuggestedQuery={(q) => {onSend(q);}}
                  />
                  ) : (
                    <div style={{ background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 12, padding: "12px 16px", color: "#cbd5e1", fontSize: 13, lineHeight: 1.6 }}>
                      {typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content)}
                    </div>
                  )}
                  {msg.isStructured && (
                    <button onClick={() => onSaveInsight(msg)} style={{ marginTop: 8, padding: "4px 12px", borderRadius: 999, border: "1px solid #1e3a5f", background: "transparent", color: "#475569", fontSize: 11, cursor: "pointer" }}
                      onMouseEnter={e => { e.currentTarget.style.color="#22c55e"; e.currentTarget.style.borderColor="#22c55e"; }}
                      onMouseLeave={e => { e.currentTarget.style.color="#475569"; e.currentTarget.style.borderColor="#1e3a5f"; }}>
                      ✦ Save Insight
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && messages[messages.length - 1]?.role === "user" && (
          <div style={{ display: "flex", gap: 11, marginBottom: 20 }}>
            <div style={{ width: 26, height: 26, borderRadius: 7, background: "linear-gradient(135deg,#1d4ed8,#7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12 }}>⬡</div>
            <div>
              <AgentStatusPill steps={agentSteps} />
              <div style={{ padding: "10px 16px", background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 12, display: "inline-flex", gap: 5, alignItems: "center" }}>
                {[0, 150, 300].map(d => (
                  <div key={d} style={{ width: 6, height: 6, borderRadius: 999, background: "#3b82f6", animation: `pulse 1.2s ${d}ms ease infinite` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{ padding: "14px 24px 18px", borderTop: "1px solid #0d1f35", background: "#060d1a" }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center", background: "#0f172a", border: "1px solid #1e3a5f", borderRadius: 14, padding: "10px 14px" }}>
          <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder={`Ask Vodafone Ireland Analytics…`}
            disabled={loading}
            style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#f1f5f9", fontSize: 13 }}
          />
          <button onClick={handleSend} disabled={loading || !input.trim()} style={{
            width: 32, height: 32, borderRadius: 8, border: "none", flexShrink: 0,
            background: loading || !input.trim() ? "#1e293b" : "linear-gradient(135deg,#1d4ed8,#7c3aed)",
            color: loading || !input.trim() ? "#374151" : "#fff",
            cursor: loading || !input.trim() ? "not-allowed" : "pointer",
            fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center",
          }}>→</button>
        </div>
      </div>
    </div>
  );
}
