"""Persistent saved-insight endpoints backed by BigQuery."""
from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from services.insights_service import save_insight, get_insights, patch_insight, delete_insight

router = APIRouter(prefix="/api/v1", tags=["insights"])


@router.post("/insights")
async def create_insight(body: dict = Body(...)):
    analytics_response = body.get("analytics_response") or body.get("analytics") or {}
    if hasattr(analytics_response, "model_dump"):
        analytics_response = analytics_response.model_dump()

    insight_id = await save_insight(
        user_id=body.get("user_id", "anonymous"),
        persona_id=body.get("persona_id", "analyst"),
        title=body.get("title") or body.get("query") or "Untitled Insight",
        query=body.get("query", ""),
        dataset_id=body.get("dataset_id", "ireland"),
        analytics_response=analytics_response,
        tags=body.get("tags", []),
    )
    return JSONResponse(content={"insight_id": insight_id, "status": "saved"})


@router.get("/insights")
async def list_insights(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    search: str = Query(default=""),
    tag: str = Query(default=""),
    pinned_only: bool = Query(default=False),
):
    insights = await get_insights(
        user_id=user_id,
        limit=limit,
        search=search,
        tag_filter=tag,
        pinned_only=pinned_only,
    )
    return JSONResponse(content={
        "insights": insights,
        "total": len(insights),
        "pinned_count": sum(1 for item in insights if item.get("is_pinned")),
    })


@router.patch("/insights/{insight_id}")
async def update_insight(
    insight_id: str,
    user_id: str = Query(..., min_length=1),
    body: dict = Body(default={}),
):
    allowed = {key: body[key] for key in ("tags", "is_pinned", "title") if key in body}
    updated = await patch_insight(insight_id, user_id, **allowed)
    return JSONResponse(content={"updated": updated})


@router.delete("/insights/{insight_id}")
async def remove_insight(
    insight_id: str,
    user_id: str = Query(..., min_length=1),
):
    deleted = await delete_insight(insight_id, user_id)
    return JSONResponse(content={"deleted": deleted})
