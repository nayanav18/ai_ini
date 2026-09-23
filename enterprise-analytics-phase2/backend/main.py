"""FastAPI application for the Phase 1 + Phase 2 analytics platform."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from config import settings
from routers.chat import router as chat_router
from routers.datasets import router as datasets_router
from routers.conversations import router as conversations_router
from routers.health import router as health_router
from routers.insights_router import router as insights_router
from routers.persona_router import router as persona_router
from routers.dashboard_router import router as dashboard_router
from routers.widgets_router import router as widgets_router
from services.vertex_client import init_vertex_ai

logger = structlog.get_logger()

app = FastAPI(
    title="Vodafone Ireland Analytics Platform",
    description="AI-powered enterprise analytics — Phase 1 + Phase 2",
    version="2.1.0",
)

# CORS is driven by the environment instead of a non-functional wildcard
# origin such as https://*.cloudshell.dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(datasets_router)
app.include_router(conversations_router)
app.include_router(health_router)
app.include_router(insights_router)
app.include_router(persona_router)
app.include_router(dashboard_router)
app.include_router(widgets_router)


@app.on_event("startup")
async def startup():
    try:
        init_vertex_ai()
    except Exception as exc:
        # Do not prevent health/config inspection from starting when local
        # Google credentials are not available. Analytics requests will still
        # surface the actual provider error.
        logger.warning("Vertex AI initialisation skipped", error=str(exc)[:120])

    try:
        from services.memory_service import ensure_tables_exist
        await ensure_tables_exist()
    except Exception as exc:
        logger.warning("Memory table setup skipped", error=str(exc)[:120])

    try:
        from services.insights_service import ensure_table
        await ensure_table()
    except Exception as exc:
        logger.warning("Insights table setup skipped", error=str(exc)[:120])


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.1.0",
        "phase": 2,
        "features": {
            "guardrails": True,
            "memory": True,
            "persona_dashboard": True,
            "insights": True,
            "widgets": True,
        },
    }
