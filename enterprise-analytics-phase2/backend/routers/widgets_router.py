"""
widgets_router.py — Dashboard widget layout endpoints.

BQ Table: KarthikRudrapati.analytics_dashboard_layouts
"""
import uuid
import json
from fastapi import APIRouter, Query, Body
from fastapi.responses import JSONResponse
from google.cloud import bigquery
import structlog

from config import settings

router = APIRouter(prefix="/api/v1", tags=["widgets"])
logger = structlog.get_logger()

PROJECT    = settings.GCP_PROJECT_ID
DATASET    = settings.BIGQUERY_DATASET
BQ_LAYOUTS = f"{PROJECT}.{DATASET}.analytics_dashboard_layouts"

CREATE_LAYOUTS_SQL = f"""
CREATE TABLE IF NOT EXISTS `{BQ_LAYOUTS}` (
  layout_id   STRING NOT NULL,
  user_id     STRING NOT NULL,
  persona_id  STRING NOT NULL,
  widgets     JSON,
  story_cache JSON,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)"""

def _client():
    return bigquery.Client(project=PROJECT)

def _ensure_table():
    try:
        _client().query(CREATE_LAYOUTS_SQL).result()
    except Exception:
        pass


@router.get("/widgets/{user_id}/{persona_id}")
async def get_layout(user_id: str, persona_id: str):
    """Load saved widget layout for user+persona."""
    _ensure_table()
    sql = f"""
    SELECT layout_id, TO_JSON_STRING(widgets) AS widgets_json, updated_at
    FROM `{BQ_LAYOUTS}`
    WHERE user_id = @uid AND persona_id = @pid
    ORDER BY updated_at DESC LIMIT 1
    """
    cfg = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("uid", "STRING", user_id),
        bigquery.ScalarQueryParameter("pid", "STRING", persona_id),
    ])
    try:
        rows = list(_client().query(sql, job_config=cfg).result())
        if rows:
            widgets = json.loads(rows[0]["widgets_json"] or "[]")
            return JSONResponse(content={
                "layout_id": rows[0]["layout_id"],
                "widgets":   widgets,
                "updated_at": str(rows[0]["updated_at"]),
            })
    except Exception as e:
        logger.warning("get_layout failed", error=str(e)[:80])
    return JSONResponse(content={"layout_id": None, "widgets": []})


@router.put("/widgets/{user_id}/{persona_id}")
async def save_layout(
    user_id: str,
    persona_id: str,
    body: dict = Body(...),
):
    """Save (upsert) widget layout. Called after drag-drop."""
    _ensure_table()
    widgets = body.get("widgets", [])
    layout_id = body.get("layout_id") or str(uuid.uuid4())
    widgets_json = json.dumps(widgets)

    sql = f"""
    MERGE `{BQ_LAYOUTS}` T
    USING (SELECT @uid AS user_id, @pid AS persona_id) S
    ON T.user_id = S.user_id AND T.persona_id = S.persona_id
    WHEN MATCHED THEN
      UPDATE SET widgets = PARSE_JSON(@wj), updated_at = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
      INSERT (layout_id, user_id, persona_id, widgets, updated_at)
      VALUES (@lid, S.user_id, S.persona_id, PARSE_JSON(@wj), CURRENT_TIMESTAMP())
    """
    cfg = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("uid", "STRING", user_id),
        bigquery.ScalarQueryParameter("pid", "STRING", persona_id),
        bigquery.ScalarQueryParameter("lid", "STRING", layout_id),
        bigquery.ScalarQueryParameter("wj",  "STRING", widgets_json),
    ])
    try:
        _client().query(sql, job_config=cfg).result()
        return JSONResponse(content={"layout_id": layout_id, "saved": True})
    except Exception as e:
        logger.error("save_layout failed", error=str(e)[:100])
        return JSONResponse(status_code=500, content={"error": str(e)[:100]})


@router.post("/widgets/{user_id}/{persona_id}/add")
async def add_widget(
    user_id: str,
    persona_id: str,
    body: dict = Body(...),
):
    """Add one widget to the layout (pin from Insights tab)."""
    widget_id = str(uuid.uuid4())
    new_widget = {
        "widget_id":  widget_id,
        "insight_id": body.get("insight_id", ""),
        "type":       body.get("widget_type", "kpi_card"),
        "title":      body.get("title", "Insight"),
        "size":       body.get("size", "medium"),
        "data":       body.get("data", {}),
        "position":   body.get("position", 0),
    }
    # Load existing, append, save
    _ensure_table()
    result = await get_layout(user_id, persona_id)
    existing = json.loads(result.body).get("widgets", [])
    existing.append(new_widget)
    await save_layout(user_id, persona_id, {"widgets": existing})
    return JSONResponse(content={"widget_id": widget_id, "added": True})


@router.delete("/widgets/{user_id}/{persona_id}/{widget_id}")
async def remove_widget(user_id: str, persona_id: str, widget_id: str):
    """Remove one widget from the layout."""
    result = await get_layout(user_id, persona_id)
    existing = json.loads(result.body).get("widgets", [])
    filtered = [w for w in existing if w.get("widget_id") != widget_id]
    await save_layout(user_id, persona_id, {"widgets": filtered})
    return JSONResponse(content={"removed": True, "remaining": len(filtered)})
