import { useState, useCallback, useEffect, useRef } from "react";
import { api } from "../utils/api";
import { DATASETS, AGENT_PIPELINE, getStableUserId, uid } from "../utils/helpers";

const HISTORY_CACHE_KEY = "enterprise_analytics_conversations_cache";

function datasetForId(id) {
  return DATASETS.find((dataset) => dataset.id === id) || DATASETS[0];
}

function normaliseConversation(record) {
  return {
    id: record.id || record.conversation_id,
    title: record.title || "New Conversation",
    messages: record.messages || [],
    ts: record.updated_at || record.created_at || Date.now(),
    dataset: datasetForId(record.dataset_id),
    personaId: record.persona_id || "analyst",
    messageCount: Number(record.message_count || 0),
  };
}

function normalisePersistedMessage(message, dataset) {
  if (message.role === "user") {
    const text = typeof message.content === "string"
      ? message.content
      : message.content?.text || message.query || "";
    return {
      id: message.message_id,
      role: "user",
      content: text,
      ts: message.generated_at || Date.now(),
    };
  }

  const content = typeof message.content === "object" && message.content !== null
    ? message.content
    : message.content?.text || message.query || "";
  const structured = typeof content === "object" && Boolean(content.what_happened);

  return {
    id: message.message_id,
    role: "assistant",
    content,
    isStructured: structured,
    dataset: dataset?.label || DATASETS[0].label,
    ts: message.generated_at || Date.now(),
    query: message.query || "",
    agentSteps: content?.agent_steps || [],
  };
}

function readCachedConversations() {
  try {
    const raw = localStorage.getItem(HISTORY_CACHE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeCachedConversations(conversations) {
  try {
    localStorage.setItem(HISTORY_CACHE_KEY, JSON.stringify(conversations.slice(0, 50)));
  } catch {
    // The backend remains the source of truth when browser storage is unavailable.
  }
}

export function useChat({ selectedDataset }) {
  const userIdRef = useRef(null);
  if (!userIdRef.current) userIdRef.current = getStableUserId();

  const [conversations, setConversations] = useState(readCachedConversations);
  const [activeConvId, setActiveConvId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [agentSteps, setAgentSteps] = useState({});
  const loadedMessageIds = useRef(new Set());

  const activeConv = conversations.find((conversation) => conversation.id === activeConvId) || null;
  const messages = activeConv?.messages || [];

  useEffect(() => {
    writeCachedConversations(conversations);
  }, [conversations]);

  const refreshConversations = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const response = await api.listConversations(userIdRef.current);
      const serverConversations = (response?.conversations || []).map(normaliseConversation);

      // Do not erase a useful local cache when the backend is temporarily
      // unavailable and responds with an empty list.
      if (serverConversations.length > 0 || readCachedConversations().length === 0) {
        setConversations(serverConversations);
      }

      setActiveConvId((current) => {
        if (current && serverConversations.some((item) => item.id === current)) return current;
        return serverConversations[0]?.id || readCachedConversations()[0]?.id || null;
      });
    } catch (error) {
      console.warn("Conversation history could not be loaded:", error);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  const loadMessages = useCallback(async (conversationId) => {
    if (!conversationId || loadedMessageIds.current.has(conversationId)) return;
    try {
      const response = await api.loadConversationMessages(conversationId, userIdRef.current);
      const serverMessages = response?.messages || [];
      const conversation = conversations.find((item) => item.id === conversationId);
      const dataset = conversation?.dataset || selectedDataset;
      const hydrated = serverMessages.map((message) => normalisePersistedMessage(message, dataset));

      setConversations((prev) => prev.map((item) => {
        if (item.id !== conversationId) return item;
        return { ...item, messages: hydrated, messageCount: hydrated.length, ts: item.ts || Date.now() };
      }));
      loadedMessageIds.current.add(conversationId);
    } catch (error) {
      console.warn("Conversation messages could not be loaded:", error);
    }
  }, [conversations, selectedDataset]);

  useEffect(() => {
    if (activeConvId) loadMessages(activeConvId);
  }, [activeConvId, loadMessages]);

  const animatePipeline = useCallback(async () => {
    const steps = {};
    for (const agent of AGENT_PIPELINE) {
      steps[agent.id] = "running";
      setAgentSteps({ ...steps });
      await new Promise((resolve) => setTimeout(resolve, 350 + Math.random() * 250));
      steps[agent.id] = "done";
      setAgentSteps({ ...steps });
    }
  }, []);

  const newChat = useCallback(() => {
    const id = uid();
    const conversation = {
      id,
      title: "New Chat",
      messages: [],
      ts: Date.now(),
      dataset: selectedDataset,
      personaId: "analyst",
      messageCount: 0,
    };
    setConversations((prev) => [conversation, ...prev.filter((item) => item.id !== id)]);
    setActiveConvId(id);
    setAgentSteps({});
    return id;
  }, [selectedDataset]);

  const openConv = useCallback((id) => {
    setActiveConvId(id);
    setAgentSteps({});
    loadMessages(id);
  }, [loadMessages]);

  const sendMessage = useCallback(
    async (query, overrideConvId) => {
      const trimmedQuery = query.trim();
      if (!trimmedQuery || loading) return;

      let convId = overrideConvId || activeConvId;
      const existingConversation = conversations.find((item) => item.id === convId);

      if (!convId) {
        convId = uid();
        setConversations((prev) => [
          {
            id: convId,
            title: trimmedQuery.slice(0, 42),
            messages: [],
            ts: Date.now(),
            dataset: selectedDataset,
            personaId: "analyst",
            messageCount: 0,
          },
          ...prev,
        ]);
        setActiveConvId(convId);
      } else if (!existingConversation) {
        setConversations((prev) => [
          {
            id: convId,
            title: trimmedQuery.slice(0, 42),
            messages: [],
            ts: Date.now(),
            dataset: selectedDataset,
            personaId: "analyst",
            messageCount: 0,
          },
          ...prev,
        ]);
      }

      const previousMessages = existingConversation?.messages || [];
      const history = previousMessages.map((message) => ({
        role: message.role,
        content: typeof message.content === "string"
          ? message.content
          : message.content?.what_happened || message.content?.text || JSON.stringify(message.content),
      }));

      const userMessage = {
        id: uid(),
        role: "user",
        content: trimmedQuery,
        ts: Date.now(),
      };

      setConversations((prev) => prev.map((conversation) => conversation.id === convId
        ? {
            ...conversation,
            title: conversation.title === "New Chat" ? trimmedQuery.slice(0, 42) : conversation.title,
            messages: [...conversation.messages, userMessage],
            ts: new Date().toISOString(),
            dataset: selectedDataset,
          }
        : conversation
      ));

      setLoading(true);
      setAgentSteps({});

      const [_, result] = await Promise.all([
        animatePipeline(),
        api.chat({
          query: trimmedQuery,
          dataset_id: selectedDataset.id,
          conversation_id: convId,
          user_id: userIdRef.current,
          persona_id: existingConversation?.personaId || "analyst",
          history,
        }).catch((error) => ({ error: error.message })),
      ]);

      setAgentSteps({});
      setLoading(false);

      const serverConversationId = result?.conversation_id || convId;
      const isStructured = !result?.error && Boolean(result?.what_happened);
      const assistantMessage = {
        id: uid(),
        role: "assistant",
        content: isStructured ? result : result?.error || "An error occurred.",
        isStructured,
        dataset: selectedDataset.label,
        ts: Date.now(),
        query: trimmedQuery,
        agentSteps: result?.agent_steps || [],
      };

      setConversations((prev) => {
        let found = false;
        const next = prev.map((conversation) => {
          if (conversation.id !== convId && conversation.id !== serverConversationId) return conversation;
          found = true;
          return {
            ...conversation,
            id: serverConversationId,
            title: conversation.title === "New Chat" ? trimmedQuery.slice(0, 42) : conversation.title,
            messages: [...conversation.messages, assistantMessage],
            ts: new Date().toISOString(),
            messageCount: (conversation.messageCount || 0) + 2,
          };
        });
        if (!found) {
          next.unshift({
            id: serverConversationId,
            title: trimmedQuery.slice(0, 42),
            messages: [userMessage, assistantMessage],
            ts: new Date().toISOString(),
            dataset: selectedDataset,
            personaId: "analyst",
            messageCount: 2,
          });
        }
        return next;
      });
      setActiveConvId(serverConversationId);
      loadedMessageIds.current.add(serverConversationId);
    },
    [loading, activeConvId, conversations, selectedDataset, animatePipeline]
  );

  return {
    userId: userIdRef.current,
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
    refreshConversations,
  };
}
