/**
 * Central API client for the FastAPI backend.
 * All calls use the same stable browser user ID so persistent Phase 2
 * conversations and insights survive a page refresh.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }

  if (!response.ok) {
    const message = body?.detail || body?.error || text || `API ${response.status}`;
    throw new Error(message);
  }
  return body;
}

const withUser = (path, userId) => {
  const params = new URLSearchParams({ user_id: userId });
  return `${path}${path.includes("?") ? "&" : "?"}${params.toString()}`;
};

export const api = {
  chat: (body) =>
    request("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listDatasets: () => request("/api/v1/datasets"),

  listConversations: (userId) =>
    request(withUser("/api/v1/conversations", userId)),

  loadConversationMessages: (conversationId, userId) =>
    request(withUser(`/api/v1/conversations/${conversationId}/messages`, userId)),

  createConversation: (userId, { personaId = "analyst", datasetId = "ireland", title = "New Conversation" } = {}) =>
    request(
      `/api/v1/conversations?${new URLSearchParams({
        user_id: userId,
        persona_id: personaId,
        dataset_id: datasetId,
        title,
      })}`,
      { method: "POST" }
    ),

  renameConversation: (conversationId, userId, title) =>
    request(
      `/api/v1/conversations/${conversationId}?${new URLSearchParams({ user_id: userId, title })}`,
      { method: "PATCH" }
    ),

  listInsights: (userId) =>
    request(withUser("/api/v1/insights", userId)),

  saveInsight: (body) =>
    request("/api/v1/insights", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteInsight: (id, userId) =>
    request(withUser(`/api/v1/insights/${id}`, userId), { method: "DELETE" }),
};
