"""
persona_router.py — Persona management endpoints.
Copy to: backend/routers/persona_router.py
"""
from fastapi import APIRouter, Query, Body
from fastapi.responses import JSONResponse
import structlog

from services.persona_service import (
    get_persona,
    get_all_persona_ids,
    load_personas,
)

router = APIRouter(prefix="/api/v1", tags=["persona"])
logger = structlog.get_logger()


@router.get("/personas")
async def list_personas():
    """Return all available personas with their config."""
    personas = load_personas()
    return JSONResponse(content={
        "personas": [
            {
                "id":       p["id"],
                "name":     p["name"],
                "icon":     p["icon"],
                "tagline":  p.get("tagline", ""),
                "focus":    p.get("focus", []),
                "suggested_questions": p.get("suggested_questions", []),
            }
            for p in personas.values()
        ]
    })


@router.get("/persona/{persona_id}/config")
async def get_persona_config(persona_id: str):
    """Get full config for a specific persona."""
    valid = get_all_persona_ids()
    if persona_id not in valid:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown persona. Valid: {valid}"}
        )
    p = get_persona(persona_id)
    return JSONResponse(content=p)


@router.get("/persona/{user_id}")
async def get_user_persona(user_id: str):
    """Get current persona for a user (defaults to analyst)."""
    # Try BQ first
    persona_id = "analyst"
    try:
        from services.memory_service import get_user_persona as _get
        persona_id = await _get(user_id)
    except Exception:
        pass

    persona = get_persona(persona_id)
    return JSONResponse(content={
        "user_id":    user_id,
        "persona_id": persona_id,
        "persona": {
            "id":      persona["id"],
            "name":    persona["name"],
            "icon":    persona["icon"],
            "tagline": persona.get("tagline", ""),
            "suggested_questions": persona.get("suggested_questions", []),
        },
    })


@router.post("/persona/{user_id}")
async def set_user_persona(
    user_id: str,
    body: dict = Body(default={}),
):
    """Update a user's active persona."""
    persona_id = body.get("persona_id", "analyst")
    valid = get_all_persona_ids()
    if persona_id not in valid:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid persona_id. Valid: {valid}"}
        )
    # Save to BQ if available
    try:
        from services.memory_service import upsert_user
        await upsert_user(user_id=user_id, persona_id=persona_id)
    except Exception as e:
        logger.warning("Could not save persona to BQ", error=str(e)[:60])

    persona = get_persona(persona_id)
    return JSONResponse(content={
        "user_id":    user_id,
        "persona_id": persona_id,
        "name":       persona["name"],
        "icon":       persona["icon"],
        "message":    f"Persona updated to {persona['name']}",
    })
