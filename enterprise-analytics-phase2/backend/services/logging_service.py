"""
BigQuery Logging Service
Stores every user query, generated SQL, BQ results and AI response
for auditability and validation.
"""
import json
import uuid
import time
import structlog
from datetime import datetime, timezone
from google.cloud import bigquery
from config import settings
logger = structlog.get_logger()
LOG_TABLE = f"{settings.GCP_PROJECT_ID}.KarthikRudrapati.analytics_logs"
_client = None

def get_bq_client():
   global _client
   if _client is None:
       _client = bigquery.Client(project=settings.GCP_PROJECT_ID)
   return _client

async def log_analytics_request(
   user_query: str,
   dataset_id: str,
   generated_sql: str,
   bq_rows: list,
   ai_response: dict,
   agent_steps: list,
   execution_time_ms: int,
   session_id: str,
   status: str = "success",
   error_message: str = None,
):
   """Log every request to BigQuery for validation and audit."""
   try:
       client = get_bq_client()
       log_id = str(uuid.uuid4())
       row = {
           "log_id": log_id,
           "timestamp": datetime.now(timezone.utc).isoformat(),
           "user_session": session_id,
           "dataset_id": dataset_id,
           "user_query": user_query,
           "generated_sql": generated_sql or "",
           "sql_row_count": len(bq_rows) if bq_rows else 0,
           "bq_data": json.dumps(bq_rows[:10] if bq_rows else []),  # store first 10 rows
           "ai_response": json.dumps(ai_response) if ai_response else "{}",
           "what_happened": ai_response.get("what_happened", "") if ai_response else "",
           "kpis": json.dumps(ai_response.get("kpis", [])) if ai_response else "[]",
           "agent_steps": json.dumps([s.model_dump() if hasattr(s, 'model_dump') else str(s) for s in agent_steps]),
           "execution_time_ms": execution_time_ms,
           "status": status,
           "error_message": error_message or "",
       }
       errors = client.insert_rows_json(LOG_TABLE, [row])
       if errors:
           logger.error("BQ logging error", errors=errors)
       else:
           logger.info("Request logged to BQ", log_id=log_id, query=user_query[:60])
       return log_id
   except Exception as e:
       logger.error("Logging service failed", error=str(e))
       return None
