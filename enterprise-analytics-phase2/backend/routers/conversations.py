"""Persistent conversation history endpoints."""
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import structlog

from services.memory_service import (
    create_conversation,
    load_conversations,
    load_messages,
    update_conversation_title,
)

router = APIRouter(prefix="/api/v1", tags=["conversations"])
logger = structlog.get_logger()


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _group_name(timestamp):
    if not timestamp:
        return "Older"
    try:
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        delta = (datetime.now(timezone.utc).date() - timestamp.date()).days
        if delta == 0:
            return "Today"
        if delta == 1:
            return "Yesterday"
        if delta <= 7:
            return "This Week"
    except (TypeError, ValueError):
        pass
    return "Older"


def _serialise_conversation(conv: dict) -> dict:
    return {
        "id": conv.get("conversation_id"),
        "user_id": conv.get("user_id"),
        "persona_id": conv.get("persona_id", "analyst"),
        "dataset_id": conv.get("dataset_id", "ireland"),
        "title": conv.get("title") or "New Conversation",
        "message_count": int(conv.get("message_count") or 0),
        "created_at": _iso(conv.get("created_at")),
        "updated_at": _iso(conv.get("updated_at")),
    }


@router.get("/conversations")
async def get_conversations(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    convs = await load_conversations(user_id=user_id, limit=limit)
    groups = defaultdict(list)
    for conv in convs:
        serialised = _serialise_conversation(conv)
        groups[_group_name(serialised["updated_at"])].append(serialised)

    return JSONResponse(content={
        "conversations": [_serialise_conversation(c) for c in convs],
        "groups": dict(groups),
        "total": len(convs),
    })


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    user_id: str = Query(..., min_length=1),
    limit: int = Query(default=100, ge=1, le=200),
):
    messages = await load_messages(
        conversation_id=conversation_id,
        user_id=user_id,
        limit=limit,
    )
    return JSONResponse(content={"messages": messages, "count": len(messages)})


@router.post("/conversations")
async def new_conversation(
    user_id: str = Query(..., min_length=1),
    persona_id: str = Query(default="analyst"),
    dataset_id: str = Query(default="ireland"),
    title: str = Query(default="New Conversation"),
):
    conversation_id = await create_conversation(
        user_id=user_id,
        persona_id=persona_id,
        dataset_id=dataset_id,
        title=title,
    )
    return JSONResponse(content={"conversation_id": conversation_id})


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: str,
    user_id: str = Query(..., min_length=1),
    title: str = Query(..., min_length=1, max_length=120),
):
    updated = await update_conversation_title(conversation_id, user_id, title)
    return JSONResponse(content={"updated": updated})
