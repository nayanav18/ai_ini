"""
Agent Orchestrator — runs full pipeline and returns typed AnalyticsResponse.
Includes summary_bullets and suggested_questions in response.
"""
import time
import uuid
from datetime import datetime, timezone
import structlog
from agents.planner_agent import PlannerAgent
from agents.metadata_agent import MetadataAgent
from agents.data_agent import DataAgent
from agents.analytics_agent import AnalyticsAgent
from services.logging_service import log_analytics_request
from models.schemas import (
   AnalyticsResponse, AgentStep, KPI, RootCause, Recommendation,
   Risk, Chart, ChartDataPoint, MarketAnalysis,
   CompetitorAnalysis, CompetitorItem,
)
logger = structlog.get_logger()
DATASETS = {
   "ireland":  "Vodafone Ireland",
   "mi":       "MI Constellation",
   "germany":  "Germany Constellation",
   "uk":       "UK Constellation",
   "finance":  "Finance Analytics",
   "customer": "Customer Analytics",
}

async def run_pipeline(
   query: str,
   dataset_id: str,
   conversation_id: str | None,
   history: list[dict],
   history_context: str = "",
) -> AnalyticsResponse:
   """Execute all agents sequentially and return typed AnalyticsResponse."""
   conv_id       = conversation_id or str(uuid.uuid4())
   dataset_label = DATASETS.get(dataset_id, dataset_id)
   start_time    = time.monotonic()
   context = {
       "query":           query,
       "dataset_id":      dataset_id,
       "dataset_label":   dataset_label,
       "history":         history,
       "history_context":  history_context,
       "conversation_id": conv_id,
       "_agent_steps":    [],
   }
   pipeline = [PlannerAgent(), MetadataAgent(), DataAgent(), AnalyticsAgent()]
   status        = "success"
   error_message = None
   try:
       for agent in pipeline:
           context = await agent.run(context)
   except Exception as e:
       status        = "error"
       error_message = str(e)
       logger.error("Pipeline failed", error=str(e))
   execution_time_ms = int((time.monotonic() - start_time) * 1000)
   raw          = context.get("analytics_result", {})
   agent_steps  = context.get("_agent_steps", [])
   data_context = context.get("data", {})
   # Log generated SQL to terminal
   if data_context.get("sql"):
       logger.info(
           "GENERATED SQL",
           sql=data_context["sql"],
           row_count=data_context.get("row_count", 0),
       )
   # Log full request to BigQuery (no summary_bullets in log)
   await log_analytics_request(
       user_query=query,
       dataset_id=dataset_id,
       generated_sql=data_context.get("sql", ""),
       bq_rows=data_context.get("rows", []),
       ai_response=raw,
       agent_steps=agent_steps,
       execution_time_ms=execution_time_ms,
       session_id=conv_id,
       status=status,
       error_message=error_message,
   )
   # ── Parse each section safely ────────────────────────────────────────────
   def safe_parse(cls, items):
       result = []
       for item in (items or []):
           try:
               result.append(cls(**item))
           except Exception as e:
               logger.warning(f"Parse error for {cls.__name__}", error=str(e))
       return result
   kpis            = safe_parse(KPI,            raw.get("kpis",            []))
   root_causes     = safe_parse(RootCause,      raw.get("root_causes",     []))
   recommendations = safe_parse(Recommendation, raw.get("recommendations", []))
   risks           = safe_parse(Risk,           raw.get("risks",           []))
   # Chart
   chart = None
   try:
       if raw.get("chart") and raw["chart"].get("data"):
           chart = Chart(
               type=raw["chart"].get("type", "line"),
               title=raw["chart"].get("title", ""),
               data=[ChartDataPoint(**p) for p in raw["chart"]["data"]],
           )
   except Exception as e:
       logger.error("Chart parse error", error=str(e))
   # Market analysis
   market_analysis = None
   try:
       if raw.get("market_analysis"):
           market_analysis = MarketAnalysis(**raw["market_analysis"])
   except Exception as e:
       logger.error("Market analysis parse error", error=str(e))
   # Competitor analysis
   competitor_analysis = None
   try:
       if raw.get("competitor_analysis"):
           ca = raw["competitor_analysis"]
           competitor_analysis = CompetitorAnalysis(
               competitive_landscape=ca.get("competitive_landscape", ""),
               competitors=[CompetitorItem(**c) for c in ca.get("competitors", [])],
               competitive_advantage=ca.get("competitive_advantage", ""),
               competitive_risk=ca.get("competitive_risk", ""),
           )
   except Exception as e:
       logger.error("Competitor analysis parse error", error=str(e))
   # Summary bullets — list of strings
   summary_bullets = raw.get("summary_bullets", [])
   if not isinstance(summary_bullets, list):
       summary_bullets = []
   # Suggested questions — list of strings
   suggested_questions = raw.get("suggested_questions", [])
   if not isinstance(suggested_questions, list):
       suggested_questions = []
   logger.info(
       "Pipeline complete",
       query=query[:60],
       kpis=len(kpis),
       bullets=len(summary_bullets),
       questions=len(suggested_questions),
       duration_ms=execution_time_ms,
   )
   return AnalyticsResponse(
       conversation_id=conv_id,
       what_happened=raw.get("what_happened", "Analysis complete."),
       kpis=kpis,
       business_context=raw.get("business_context", ""),
       why_it_happened=raw.get("why_it_happened", ""),
       root_causes=root_causes,
       market_analysis=market_analysis,
       competitor_analysis=competitor_analysis,
       what_to_do=raw.get("what_to_do", ""),
       recommendations=recommendations,
       risks=risks,
       chart=chart,
       actions=raw.get("actions", ["Generate PowerPoint", "Export PDF", "Save Insight"]),
       agent_steps=agent_steps,
       dataset=dataset_label,
       query=query,
       summary_bullets=summary_bullets,
       suggested_questions=suggested_questions,
       generated_at=datetime.now(timezone.utc),
   )
def _safe_list(val):
   """Ensure value is always a list, never None."""
   if val is None:
       return []
   if isinstance(val, list):
       return val
   return [val]
