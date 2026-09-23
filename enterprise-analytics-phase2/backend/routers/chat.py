"""Chat endpoint: guardrails, analytics pipeline and persistent conversation memory."""
import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from agents.orchestrator import run_pipeline
from models.schemas import ChatRequest
from services.guardrail_service import check as guardrail_check
from services.memory_service import (
    build_context_string,
    create_conversation,
    ensure_conversation,
    load_messages,
    save_message,
    upsert_user,
)

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = structlog.get_logger()


def make_serializable(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(item) for item in obj]
    return obj


@router.post("/chat")
async def chat(request: ChatRequest):
    user_id = request.user_id or f"user_{uuid.uuid4().hex}"
    persona_id = request.persona_id or "analyst"
    dataset_id = request.dataset_id or "ireland"
    query = request.query.strip()
    conv_id = request.conversation_id

    logger.info(
        "Chat request",
        user_id=user_id,
        persona_id=persona_id,
        conversation_id=conv_id,
        query=query[:80],
    )

    try:
        await upsert_user(user_id=user_id, persona_id=persona_id)
    except Exception as exc:
        logger.warning("upsert_user failed", error=str(exc)[:100])

    # Guardrails run before creating/saving a conversation so rejected queries
    # do not create empty history records.
    try:
        guardrail = guardrail_check(query=query)
        if not guardrail.passed:
            if guardrail.action == "clarify":
                return JSONResponse(content={
                    "is_clarification_needed": True,
                    "clarification_question": guardrail.message or "Could you clarify?",
                    "matching_columns": [
                        {"column": option.column, "description": option.description}
                        for option in (guardrail.options or [])
                    ],
                    "original_query": query,
                    "user_id": user_id,
                    "persona_id": persona_id,
                })
            return JSONResponse(content={
                "is_clarification_needed": False,
                "guardrail_message": guardrail.message,
                "action": guardrail.action,
                "query": query,
                "user_id": user_id,
                "persona_id": persona_id,
            })
    except Exception as exc:
        logger.warning("Guardrail error (non-blocking)", error=str(exc)[:100])

    # Keep a frontend-created conversation ID when possible. This prevents the
    # old bug where React generated an ID that did not exist in BigQuery, so
    # message inserts could not update a conversation row.
    if not conv_id:
        conv_id = await create_conversation(
            user_id=user_id,
            persona_id=persona_id,
            dataset_id=dataset_id,
            title=query[:80] + ("..." if len(query) > 80 else ""),
        )
    else:
        conv_id = await ensure_conversation(
            conversation_id=conv_id,
            user_id=user_id,
            persona_id=persona_id,
            dataset_id=dataset_id,
            title=query[:80] + ("..." if len(query) > 80 else ""),
        )

    persisted_messages = []
    try:
        persisted_messages = await load_messages(
            conversation_id=conv_id,
            user_id=user_id,
            limit=20,
        )
    except Exception as exc:
        logger.warning("Could not load persisted history", error=str(exc)[:100])

    history_context = build_context_string(persisted_messages, max_chars=3000)
    request_history = [message.model_dump() for message in request.history]

    # Persisted history is authoritative. Request history is retained only for
    # backward compatibility with older clients that still send it.
    if not persisted_messages and request_history:
        history_for_pipeline = request_history
    else:
        history_for_pipeline = [
            {
                "role": message["role"],
                "content": (
                    message.get("content", {}).get("text", "")
                    if isinstance(message.get("content"), dict)
                    else str(message.get("content", ""))
                ),
            }
            for message in persisted_messages
        ]

    try:
        result = await run_pipeline(
            query=query,
            dataset_id=dataset_id,
            conversation_id=conv_id,
            history=history_for_pipeline,
            history_context=history_context,
        )
    except Exception as exc:
        logger.error("Pipeline failed", error=str(exc)[:180])
        return JSONResponse(status_code=500, content={
            "error": "Analytics pipeline error. Please try again.",
            "detail": str(exc)[:200],
            "user_id": user_id,
            "persona_id": persona_id,
            "conversation_id": conv_id,
        })

    try:
        if hasattr(result, "model_dump"):
            result_dict = result.model_dump()
        elif isinstance(result, dict):
            result_dict = result
        else:
            result_dict = dict(result)
        result_dict = make_serializable(result_dict)
    except Exception as exc:
        logger.error("Serialization failed", error=str(exc)[:100])
        return JSONResponse(status_code=500, content={
            "error": "Response serialization failed.",
            "detail": str(exc)[:100],
            "conversation_id": conv_id,
        })

    # Save both sides of the exchange. The assistant content is the exact
    # structured response returned to the frontend, so reopening a conversation
    # restores the same KPI/chart data rather than regenerating it.
    try:
        await save_message(conv_id, user_id, "user", query, {"text": query})
        await save_message(conv_id, user_id, "assistant", query, result_dict)
    except Exception as exc:
        logger.warning("Message persistence failed", error=str(exc)[:120])

    result_dict["user_id"] = user_id
    result_dict["persona_id"] = persona_id
    result_dict["conversation_id"] = conv_id
    return JSONResponse(content=result_dict)
