"""Chat endpoint: intent routing, guardrails, analytics pipeline and conversation memory."""

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from agents.intent_router import intent_router
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
        return {
            key: make_serializable(value)
            for key, value in obj.items()
        }

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

    # ---------------------------------------------------------
    # 1. BUILD HISTORY CONTEXT
    # ---------------------------------------------------------

    request_history = [
        message.model_dump()
        for message in request.history
    ]

    # ---------------------------------------------------------
    # 2. INTENT + CONTEXT ROUTER
    # ---------------------------------------------------------

    try:
        route_result = intent_router.route(
            message=query,
            history=request_history,
        )

        intent = route_result.intent

        logger.info(
            "Intent routed",
            intent=intent,
            confidence=route_result.confidence,
            reason=route_result.reason,
        )

    except Exception as exc:
        logger.warning(
            "Intent routing failed; defaulting to analysis",
            error=str(exc)[:150],
        )

        intent = "analysis"

    # ---------------------------------------------------------
    # 3. ORDINARY CONVERSATION
    #
    # IMPORTANT:
    # Conversation should NOT go through the analytics
    # pipeline or BigQuery.
    #
    # For now we return a lightweight conversational response.
    # The dedicated conversational AI response will be connected
    # in the next architecture step.
    # ---------------------------------------------------------

    if intent == "conversation":
        response_text = _conversation_response(query)

        return JSONResponse(
            content={
                "intent": "conversation",
                "conversation_response": response_text,
                "what_happened": response_text,
                "user_id": user_id,
                "persona_id": persona_id,
                "conversation_id": conv_id,
            }
        )

    # ---------------------------------------------------------
    # 4. USER / CONVERSATION SETUP
    # ---------------------------------------------------------

    try:
        await upsert_user(
            user_id=user_id,
            persona_id=persona_id,
        )
    except Exception as exc:
        logger.warning(
            "upsert_user failed",
            error=str(exc)[:100],
        )

    # ---------------------------------------------------------
    # 5. GUARDRAILS
    #
    # Only analytics-related intents reach this stage.
    # ---------------------------------------------------------

    try:
        guardrail = guardrail_check(query=query)

        if not guardrail.passed:

            if guardrail.action == "clarify":
                return JSONResponse(
                    content={
                        "intent": intent,
                        "is_clarification_needed": True,
                        "clarification_question": (
                            guardrail.message
                            or "Could you clarify?"
                        ),
                        "matching_columns": [
                            {
                                "column": option.column,
                                "description": option.description,
                            }
                            for option in (guardrail.options or [])
                        ],
                        "original_query": query,
                        "user_id": user_id,
                        "persona_id": persona_id,
                        "conversation_id": conv_id,
                    }
                )

            return JSONResponse(
                content={
                    "intent": intent,
                    "is_clarification_needed": False,
                    "guardrail_message": guardrail.message,
                    "action": guardrail.action,
                    "query": query,
                    "user_id": user_id,
                    "persona_id": persona_id,
                    "conversation_id": conv_id,
                }
            )

    except Exception as exc:
        logger.warning(
            "Guardrail error (non-blocking)",
            error=str(exc)[:100],
        )

    # ---------------------------------------------------------
    # 6. CREATE / RESTORE CONVERSATION
    # ---------------------------------------------------------

    if not conv_id:
        conv_id = await create_conversation(
            user_id=user_id,
            persona_id=persona_id,
            dataset_id=dataset_id,
            title=query[:80]
            + ("..." if len(query) > 80 else ""),
        )
    else:
        conv_id = await ensure_conversation(
            conversation_id=conv_id,
            user_id=user_id,
            persona_id=persona_id,
            dataset_id=dataset_id,
            title=query[:80]
            + ("..." if len(query) > 80 else ""),
        )

    # ---------------------------------------------------------
    # 7. LOAD PERSISTED CONVERSATION HISTORY
    # ---------------------------------------------------------

    persisted_messages = []

    try:
        persisted_messages = await load_messages(
            conversation_id=conv_id,
            user_id=user_id,
            limit=20,
        )
    except Exception as exc:
        logger.warning(
            "Could not load persisted history",
            error=str(exc)[:100],
        )

    history_context = build_context_string(
        persisted_messages,
        max_chars=3000,
    )

    # Persisted history is authoritative.
    if not persisted_messages and request_history:
        history_for_pipeline = request_history

    else:
        history_for_pipeline = [
            {
                "role": message["role"],
                "content": (
                    message.get("content", {}).get("text", "")
                    if isinstance(
                        message.get("content"),
                        dict,
                    )
                    else str(
                        message.get("content", "")
                    )
                ),
            }
            for message in persisted_messages
        ]

    # ---------------------------------------------------------
    # 8. ANALYTICS / COMPARISON / VISUALIZATION / DASHBOARD
    #
    # The current orchestrator still performs the analytics
    # pipeline. We pass the detected intent through the context
    # using the query prefix so the existing pipeline can continue
    # working without changing its function signature yet.
    # ---------------------------------------------------------

    try:
        routed_query = query

        if intent == "comparison":
            routed_query = (
                f"[INTENT: comparison]\n{query}"
            )

        elif intent == "visualization":
            routed_query = (
                f"[INTENT: visualization]\n{query}"
            )

        elif intent == "dashboard":
            routed_query = (
                f"[INTENT: dashboard]\n{query}"
            )

        result = await run_pipeline(
            query=routed_query,
            dataset_id=dataset_id,
            conversation_id=conv_id,
            history=history_for_pipeline,
            history_context=history_context,
        )

    except Exception as exc:
        logger.error(
            "Pipeline failed",
            error=str(exc)[:180],
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Analytics pipeline error. Please try again.",
                "detail": str(exc)[:200],
                "user_id": user_id,
                "persona_id": persona_id,
                "conversation_id": conv_id,
                "intent": intent,
            },
        )

    # ---------------------------------------------------------
    # 9. SERIALIZE RESULT
    # ---------------------------------------------------------

    try:
        if hasattr(result, "model_dump"):
            result_dict = result.model_dump()

        elif isinstance(result, dict):
            result_dict = result

        else:
            result_dict = dict(result)

        result_dict = make_serializable(result_dict)

    except Exception as exc:
        logger.error(
            "Serialization failed",
            error=str(exc)[:100],
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Response serialization failed.",
                "detail": str(exc)[:100],
                "conversation_id": conv_id,
            },
        )

    # ---------------------------------------------------------
    # 10. ADD ROUTING INFORMATION
    # ---------------------------------------------------------

    result_dict["intent"] = intent
    result_dict["user_id"] = user_id
    result_dict["persona_id"] = persona_id
    result_dict["conversation_id"] = conv_id

    # ---------------------------------------------------------
    # 11. SAVE CONVERSATION
    # ---------------------------------------------------------

    try:
        await save_message(
            conv_id,
            user_id,
            "user",
            query,
            {"text": query},
        )

        await save_message(
            conv_id,
            user_id,
            "assistant",
            query,
            result_dict,
        )

    except Exception as exc:
        logger.warning(
            "Message persistence failed",
            error=str(exc)[:120],
        )

    return JSONResponse(content=result_dict)


def _conversation_response(query: str) -> str:
    """Temporary deterministic conversational responses."""

    text = query.strip().lower()

    if text in {
        "hi",
        "hello",
        "hey",
        "hiya",
        "hii",
        "hiii",
    }:
        return (
            "Hello! 👋 I'm your Enterprise Analytics AI assistant. "
            "How can I help you today?"
        )

    if text in {
        "how are you",
        "how are you?",
        "how are you doing",
        "how are you doing?",
    }:
        return (
            "I'm doing well! I'm ready to help you explore your "
            "business data or answer questions."
        )

    if text in {
        "thanks",
        "thank you",
        "thank you so much",
    }:
        return "You're welcome! 😊"

    if text in {
        "bye",
        "goodbye",
    }:
        return "Goodbye! Feel free to come back whenever you need me."

    if text in {
        "what can you do",
        "what can you do?",
    }:
        return (
            "I can help you have a conversation about your data, "
            "analyze metrics, compare periods or segments, create "
            "visualizations, and work with dashboards."
        )

    if text in {
        "who are you",
        "who are you?",
    }:
        return (
            "I'm your Enterprise Analytics AI assistant. "
            "I can help you understand and analyze your business data."
        )

    if text == "help":
        return (
            "You can ask me questions about your business data, "
            "request an analysis, compare values, or ask for a "
            "visualization."
        )

    return (
        "Sure. Tell me what you'd like to know, and I'll help."
    )