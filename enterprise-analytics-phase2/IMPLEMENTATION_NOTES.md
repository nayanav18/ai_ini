# Phase 2 Implementation Notes

This package is the updated Phase 2 application. The existing architecture was preserved: React/Vite frontend, FastAPI backend, BigQuery persistence, Vertex AI/Gemini, persona dashboards, agents, and Builder.

## Changes implemented

### Analytics consistency
- Subscriber-count requests now use a deterministic BigQuery snapshot path when `Subscriber_Count_CM` exists.
- Subscriber totals use `MAX(Subscriber_Count_CM)` for a period/latest snapshot instead of summing repeated denormalised snapshot values.
- Explicit month and quarter periods are actually applied to subscriber queries.
- Subscriber chart data comes from the same canonical result as the subscriber KPI.
- A simple subscriber-count request renders as a KPI-style chart instead of an unrelated dimensional bar chart.
- Subscriber trend uses monthly `MAX(Subscriber_Count_CM)` rather than summing snapshot values.
- Dashboard subscriber KPIs use the same snapshot semantics.
- Chart row conversion prefers explicit `label`/`value` fields instead of relying on arbitrary BigQuery column order.
- Text persona KPIs such as Top Channel / Best Plan are ranked instead of being incorrectly passed to `SUM()`.

### Conversation history
- Added a stable browser user ID stored in localStorage.
- Frontend loads persisted conversations from the FastAPI conversation API on startup.
- Frontend loads persisted messages when a conversation is opened or restored after refresh.
- Backend ensures frontend-created conversation IDs exist in BigQuery before saving messages.
- Backend conversation/message reads are scoped by user ID.
- User and assistant messages are persisted as the exact exchange returned by the API.
- Persisted history is used as the analytics context when available.
- Local conversation cache is retained as a fallback during a temporary backend outage.

### API / integration cleanup
- Removed the duplicate in-memory Insights router from active registration.
- Fixed the conversation title endpoint/import.
- Added conversation rename support.
- Fixed the frontend Insights request payload to use `analytics_response`.
- Normalised frontend Insights responses to the UI model.
- Added user ID to conversation and insight requests.
- CORS now uses the configured `ALLOWED_ORIGINS` setting rather than an ineffective wildcard hostname.

### UI improvements
- Saved mini charts now correctly render KPI, bar, donut, line and area chart types.
- KPI-style charts show the exact number rather than an abbreviated K/M value, avoiding apparent mismatches with KPI cards.
- Conversation restoration has a visible loading state.
- Dashboard-originated questions are sent without creating an extra orphan "New Chat".

## Validation performed

- Python syntax compilation completed successfully for all backend Python files.
- Plain JavaScript syntax checks completed successfully for frontend utility files.
- Deterministic subscriber SQL helpers were exercised with representative DATE/schema inputs.
- Full frontend Vite build could not be run in this environment because the uploaded `node_modules` was incomplete and external npm package installation is unavailable here. The source and package-lock are included so dependencies can be installed in the normal development environment.

## Running locally

### Backend

From `backend/`:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

The Vite development server proxies `/api` to `http://localhost:8000`.

## Configuration

The existing environment files are preserved. Do not commit real credentials or secrets to source control. If a secret has previously been exposed outside the intended environment, rotate it.

## Important data assumption

The subscriber consistency fix deliberately treats `Subscriber_Count_CM` as a snapshot/current-state metric when that exact field exists. This avoids multiplying a repeated snapshot across rows. If the BigQuery schema has a different business definition for that field, the aggregation should be adjusted to that documented definition rather than blindly changing it back to `SUM()`.
