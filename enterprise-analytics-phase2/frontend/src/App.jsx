import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatView from "./components/ChatView";
import InsightsView from "./components/InsightsView";
import DashboardPage from "./pages/DashboardPage";
import BuilderPage from "./components/BuilderPage";
import { useChat } from "./hooks/useChat";
import { DATASETS, getStableUserId, uid } from "./utils/helpers";
import { api } from "./utils/api";

const INSIGHTS_CACHE_KEY = "enterprise_saved_insights";
const BUILDER_CACHE_KEY = "enterprise_builder_items";

function readCache(key, fallback = []) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export default function App() {
  const [activeNav, setActiveNav] = useState("chat");
  const [selectedDataset, setSelectedDataset] = useState(DATASETS[0]);
  const [savedInsights, setSavedInsights] = useState(() => readCache(INSIGHTS_CACHE_KEY));
  const [analyticsItems, setAnalyticsItems] = useState(() => readCache(BUILDER_CACHE_KEY));
  const [prefillQuery, setPrefillQuery] = useState("");
  const userId = getStableUserId();

  const {
    conversations,
    activeConv,
    activeConvId,
    messages,
    loading,
    historyLoading,
    agentSteps,
    newChat,
    openConv,
    sendMessage,
  } = useChat({ selectedDataset });

  useEffect(() => {
    try {
      localStorage.setItem(INSIGHTS_CACHE_KEY, JSON.stringify(savedInsights));
    } catch {
      // Backend persistence remains authoritative.
    }
  }, [savedInsights]);

  useEffect(() => {
    try {
      localStorage.setItem(BUILDER_CACHE_KEY, JSON.stringify(analyticsItems));
    } catch {
      // Builder persistence is a convenience cache.
    }
  }, [analyticsItems]);

  useEffect(() => {
    let cancelled = false;
    async function loadInsights() {
      try {
        const response = await api.listInsights(userId);
        const items = (response?.insights || []).map((item) => ({
          id: item.id || item.insight_id,
          query: item.query || item.title || "Untitled",
          dataset: item.dataset || item.dataset_id || selectedDataset.label,
          data: item.data || {
            what_happened: item.what_happened || "",
            kpis: item.kpis || [],
            chart: item.chart || null,
            summary_bullets: item.summary_bullets || [],
            recommendations: item.recommendations || [],
          },
          ts: item.created_at || Date.now(),
        }));
        if (!cancelled && (items.length > 0 || readCache(INSIGHTS_CACHE_KEY).length === 0)) {
          setSavedInsights(items);
        }
      } catch (error) {
        console.warn("Saved insights could not be loaded:", error);
      }
    }
    loadInsights();
    return () => { cancelled = true; };
  }, [userId, selectedDataset.label]);

  const handleSaveInsight = async (msg) => {
    const insightData = msg.analytics || msg.content;
    if (!insightData || typeof insightData !== "object") return;

    const optimisticId = uid();
    const optimistic = {
      id: optimisticId,
      query: msg.query || insightData.query || "Untitled",
      dataset: msg.dataset || selectedDataset.label,
      data: insightData,
      ts: Date.now(),
    };
    setSavedInsights((prev) => [optimistic, ...prev]);

    try {
      const response = await api.saveInsight({
        user_id: userId,
        persona_id: "analyst",
        title: optimistic.query,
        conversation_id: activeConvId || "",
        query: optimistic.query,
        dataset_id: selectedDataset.id,
        analytics_response: insightData,
        tags: [],
      });

      if (response?.insight_id) {
        setSavedInsights((prev) => prev.map((item) => (
          item.id === optimisticId ? { ...item, id: response.insight_id } : item
        )));
      }
    } catch (error) {
      // Keep the optimistic item as a local fallback so a temporary BQ outage
      // does not make the user's saved insight disappear.
      console.warn("Insight backend save failed; kept local fallback:", error);
    }
  };

  const handleDeleteInsight = async (id) => {
    const previous = savedInsights;
    setSavedInsights((items) => items.filter((item) => item.id !== id));
    try {
      await api.deleteInsight(id, userId);
    } catch (error) {
      setSavedInsights(previous);
      console.warn("Insight deletion failed:", error);
    }
  };

  const handleAddToBuilder = (insight) => {
    if (!insight.data?.chart) return;
    setAnalyticsItems((prev) => [
      ...prev,
      {
        id: uid(),
        title: insight.query,
        chart: insight.data.chart,
        x: 50,
        y: 50,
        width: 500,
        height: 350,
      },
    ]);
    setActiveNav("builder");
  };

  const handleSend = (query) => {
    sendMessage(query);
  };

  const handleDashboardAsk = (query) => {
    setPrefillQuery(query);
    setActiveNav("chat");
    sendMessage(query);
    window.setTimeout(() => setPrefillQuery(""), 100);
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#060d1a" }}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: 0.4 } }
        * { box-sizing: border-box; }
        input::placeholder { color: #374151; }
        button { transition: all 0.15s; }
      `}</style>

      <Sidebar
        activeNav={activeNav}
        setActiveNav={(nav) => {
          setActiveNav(nav);
          if (nav === "chat" && !activeConvId && conversations.length > 0) {
            openConv(conversations[0].id);
          }
        }}
        selectedDataset={selectedDataset}
        setSelectedDataset={setSelectedDataset}
        conversations={conversations}
        activeConvId={activeConvId}
        openConv={openConv}
        newChat={newChat}
        savedInsightsCount={savedInsights.length}
        historyLoading={historyLoading}
      />

      <main style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {(activeNav === "chat" || activeNav === "history") && (
          <ChatView
            messages={messages}
            loading={loading}
            agentSteps={agentSteps}
            activeConv={activeConv}
            selectedDataset={selectedDataset}
            onSend={handleSend}
            onNewChat={newChat}
            onSaveInsight={handleSaveInsight}
            prefillQuery={prefillQuery}
            historyLoading={historyLoading}
          />
        )}

        {activeNav === "insights" && (
          <div style={{ flex: 1, overflowY: "auto" }}>
            <InsightsView
              insights={savedInsights}
              onDelete={handleDeleteInsight}
              onAddToBuilder={handleAddToBuilder}
            />
          </div>
        )}

        {activeNav === "builder" && (
          <div style={{ flex: 1, overflowY: "auto" }}>
            <BuilderPage analyticsItems={analyticsItems} setAnalyticsItems={setAnalyticsItems} />
          </div>
        )}

        {activeNav === "dashboards" && (
          <div style={{ flex: 1, overflowY: "auto" }}>
            <DashboardPage onAskQuestion={handleDashboardAsk} />
          </div>
        )}
      </main>
    </div>
  );
}
