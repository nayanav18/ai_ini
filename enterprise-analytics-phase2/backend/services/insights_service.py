"""
insights_service.py — BigQuery persistence for saved insights.

BQ Table: KarthikRudrapati.analytics_insights
"""
import uuid
import json
import structlog
from datetime import datetime
from google.cloud import bigquery
from config import settings

logger = structlog.get_logger()

PROJECT    = settings.GCP_PROJECT_ID
DATASET    = settings.BIGQUERY_DATASET
BQ_INSIGHTS = f"{PROJECT}.{DATASET}.analytics_insights"

CREATE_INSIGHTS_SQL = f"""
CREATE TABLE IF NOT EXISTS `{BQ_INSIGHTS}` (
  insight_id      STRING NOT NULL,
  user_id         STRING NOT NULL,
  persona_id      STRING DEFAULT 'analyst',
  dataset_id      STRING DEFAULT 'ireland',
  title           STRING,
  query           STRING,
  kpis            JSON,
  chart           JSON,
  summary_bullets JSON,
  recommendations JSON,
  tags            ARRAY<STRING>,
  is_pinned       BOOL DEFAULT FALSE,
  confidence      FLOAT64 DEFAULT 0.9,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)"""


def _client():
    return bigquery.Client(project=PROJECT)


async def ensure_table():
    try:
        _client().query(CREATE_INSIGHTS_SQL).result()
    except Exception as e:
        logger.warning("insights table create skipped", error=str(e)[:80])


async def save_insight(
    user_id: str,
    persona_id: str,
    title: str,
    query: str,
    dataset_id: str,
    analytics_response: dict,
    tags: list = None,
) -> str:
    """Persist a saved insight to BigQuery. Returns insight_id."""
    iid = str(uuid.uuid4())
    client = _client()

    kpis           = json.dumps(analytics_response.get("kpis", []))
    chart          = json.dumps(analytics_response.get("chart"))
    bullets        = json.dumps(analytics_response.get("summary_bullets", []))
    recommendations= json.dumps(analytics_response.get("recommendations", []))
    tags_list      = tags or []

    sql = f"""
    INSERT INTO `{BQ_INSIGHTS}`
      (insight_id, user_id, persona_id, dataset_id, title, query,
       kpis, chart, summary_bullets, recommendations,
       tags, is_pinned, confidence, created_at)
    VALUES
      (@iid, @user_id, @persona_id, @dataset_id, @title, @query,
       PARSE_JSON(@kpis), PARSE_JSON(@chart), PARSE_JSON(@bullets),
       PARSE_JSON(@recs), @tags, FALSE, 0.9, CURRENT_TIMESTAMP())
    """
    cfg = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("iid",        "STRING", iid),
        bigquery.ScalarQueryParameter("user_id",    "STRING", user_id),
        bigquery.ScalarQueryParameter("persona_id", "STRING", persona_id),
        bigquery.ScalarQueryParameter("dataset_id", "STRING", dataset_id),
        bigquery.ScalarQueryParameter("title",      "STRING", title[:200]),
        bigquery.ScalarQueryParameter("query",      "STRING", query[:500]),
        bigquery.ScalarQueryParameter("kpis",       "STRING", kpis),
        bigquery.ScalarQueryParameter("chart",      "STRING", chart),
        bigquery.ScalarQueryParameter("bullets",    "STRING", bullets),
        bigquery.ScalarQueryParameter("recs",       "STRING", recommendations),
        bigquery.ArrayQueryParameter("tags",        "STRING", tags_list),
    ])
    try:
        client.query(sql, job_config=cfg).result()
        logger.info("Insight saved", iid=iid, user_id=user_id, title=title[:60])
    except Exception as e:
        logger.error("save_insight failed", error=str(e)[:120])
    return iid


async def get_insights(
    user_id: str,
    limit: int = 50,
    search: str = "",
    tag_filter: str = "",
    pinned_only: bool = False,
) -> list:
    """Load insights for a user with optional search / tag / pin filters."""
    client = _client()
    where = ["user_id = @user_id"]
    params = [bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]

    if pinned_only:
        where.append("is_pinned = TRUE")
    if tag_filter:
        where.append("@tag IN UNNEST(tags)")
        params.append(bigquery.ScalarQueryParameter("tag", "STRING", tag_filter))
    if search:
        where.append("(LOWER(title) LIKE @kw OR LOWER(query) LIKE @kw)")
        params.append(bigquery.ScalarQueryParameter("kw", "STRING", f"%{search.lower()}%"))

    params.append(bigquery.ScalarQueryParameter("lim", "INT64", limit))
    where_clause = " AND ".join(where)

    sql = f"""
    SELECT
      insight_id, user_id, persona_id, dataset_id, title, query,
      TO_JSON_STRING(kpis) AS kpis_json,
      TO_JSON_STRING(chart) AS chart_json,
      TO_JSON_STRING(summary_bullets) AS bullets_json,
      TO_JSON_STRING(recommendations) AS recs_json,
      tags, is_pinned, confidence, created_at
    FROM `{BQ_INSIGHTS}`
    WHERE {where_clause}
    ORDER BY is_pinned DESC, created_at DESC
    LIMIT @lim
    """
    try:
        rows = list(client.query(sql, job_config=bigquery.QueryJobConfig(
            query_parameters=params)).result())
        results = []
        for r in rows:
            results.append({
                "insight_id":      r["insight_id"],
                "user_id":         r["user_id"],
                "persona_id":      r["persona_id"],
                "dataset_id":      r["dataset_id"],
                "title":           r["title"],
                "query":           r["query"],
                "kpis":            json.loads(r["kpis_json"] or "[]"),
                "chart":           json.loads(r["chart_json"] or "null"),
                "summary_bullets": json.loads(r["bullets_json"] or "[]"),
                "recommendations": json.loads(r["recs_json"] or "[]"),
                "tags":            list(r["tags"] or []),
                "is_pinned":       bool(r["is_pinned"]),
                "confidence":      float(r["confidence"] or 0.9),
                "created_at":      str(r["created_at"]),
            })
        return results
    except Exception as e:
        logger.warning("get_insights failed", error=str(e)[:100])
        return []


async def patch_insight(insight_id: str, user_id: str, **kwargs) -> bool:
    """Update tags, is_pinned, or title on an insight."""
    client = _client()
    sets, params = [], [
        bigquery.ScalarQueryParameter("iid",     "STRING", insight_id),
        bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
    ]
    if "is_pinned" in kwargs:
        sets.append("is_pinned = @pinned")
        params.append(bigquery.ScalarQueryParameter("pinned", "BOOL", kwargs["is_pinned"]))
    if "tags" in kwargs:
        sets.append("tags = @tags")
        params.append(bigquery.ArrayQueryParameter("tags", "STRING", kwargs["tags"]))
    if "title" in kwargs:
        sets.append("title = @title")
        params.append(bigquery.ScalarQueryParameter("title", "STRING", kwargs["title"][:200]))
    if not sets:
        return False
    sql = f"""
    UPDATE `{BQ_INSIGHTS}`
    SET {', '.join(sets)}
    WHERE insight_id = @iid AND user_id = @user_id
    """
    try:
        client.query(sql, job_config=bigquery.QueryJobConfig(
            query_parameters=params)).result()
        return True
    except Exception as e:
        logger.warning("patch_insight failed", error=str(e)[:80])
        return False


async def delete_insight(insight_id: str, user_id: str) -> bool:
    """Hard-delete an insight."""
    client = _client()
    sql = f"""
    DELETE FROM `{BQ_INSIGHTS}`
    WHERE insight_id = @iid AND user_id = @user_id
    """
    cfg = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("iid",     "STRING", insight_id),
        bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
    ])
    try:
        client.query(sql, job_config=cfg).result()
        logger.info("Insight deleted", iid=insight_id)
        return True
    except Exception as e:
        logger.warning("delete_insight failed", error=str(e)[:80])
        return False
