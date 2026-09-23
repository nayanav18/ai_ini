"""
dashboard_router.py — Persona-driven auto dashboard endpoint.

Fixes:
  - Runs schema discovery first from BigQuery
  - Converts MetadataAgent output into schema text expected by DashboardAnalystAgent
  - Falls back to static dashboard if agent fails
  - 30-minute cache per persona
  - Works even if story_agent or dashboard_analyst_agent fail
"""
import time
import structlog

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from services.persona_service import get_persona, get_all_persona_ids

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

# In-process cache: key → {data, ts}
_cache: dict = {}
CACHE_TTL = 1800   # 30 minutes


async def invalidate_story_cache(
    user_id: str = "",
    persona_id: str = ""
) -> None:
    """Called when insight saved — forces story regeneration."""
    keys = [
        key for key in _cache
        if persona_id in key or user_id in key
    ]

    for key in keys:
        del _cache[key]

    if keys:
        logger.info(
            "Cache invalidated",
            persona=persona_id,
            count=len(keys)
        )


@router.get("/dashboard/{persona_id}")
async def get_dashboard(
    persona_id: str,
    user_id: str = Query(default="anonymous"),
    dataset_id: str = Query(default="ireland"),
    period: str = Query(default="latest"),
    refresh: bool = Query(default=False),
):
    """
    Auto-generate a persona-specific dashboard.

    Flow:
        MetadataAgent
            ↓
        BigQuery schema discovery
            ↓
        Convert metadata into schema text
            ↓
        DashboardAnalystAgent
            ↓
        Generate SQL
            ↓
        BigQuery queries
            ↓
        Dashboard charts
    """

    # --------------------------------------------------
    # 1. Validate persona
    # --------------------------------------------------
    valid = get_all_persona_ids()

    if persona_id not in valid:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unknown persona '{persona_id}'.",
                "valid_personas": valid,
            }
        )

    cache_key = f"{persona_id}:{dataset_id}:{period}"

    # --------------------------------------------------
    # 2. Serve from cache
    # --------------------------------------------------
    if not refresh and cache_key in _cache:
        cached = _cache[cache_key]

        if time.time() - cached["ts"] < CACHE_TTL:
            logger.info(
                "Dashboard from cache",
                persona=persona_id
            )

            return JSONResponse(
                content={
                    **cached["data"],
                    "from_cache": True
                }
            )

    logger.info(
        "Building dashboard",
        persona=persona_id,
        period=period,
        dataset_id=dataset_id
    )

    t0 = time.monotonic()

    # --------------------------------------------------
    # 3. Get persona configuration
    # --------------------------------------------------
    persona = get_persona(persona_id)

    result = None

    # --------------------------------------------------
    # 4. Run Dashboard Agent
    # --------------------------------------------------
    try:
        from agents.dashboard_analyst_agent import DashboardAnalystAgent
        from agents.metadata_agent import MetadataAgent

        # ----------------------------------------------
        # 4A. Discover actual BigQuery schema
        # ----------------------------------------------
        schema = ""

        try:
            meta = MetadataAgent()

            ctx = await meta.run({
                "dataset_id": dataset_id,
                "query": f"dashboard for {persona_id}",
            })

            # MetadataAgent stores the discovered schema
            # under "metadata", NOT "schema_text".
            metadata = ctx.get("metadata", {})

            tables = metadata.get("tables", {})

            schema_lines = []

            # Build the schema text in the same format
            # used by DataAgent.
            for table_name, info in tables.items():

                # Skip non-business/system tables if present
                if table_name in {
                    "analytics_logs",
                    "sample",
                    "context"
                }:
                    continue

                full_name = info.get("full_name", "")

                if not full_name:
                    continue

                schema_lines.append(
                    f"Table: {full_name}\n"
                    f"  Numeric (metrics): "
                    f"{info.get('numeric_columns', [])}\n"
                    f"  Date columns: "
                    f"{info.get('date_columns', [])}\n"
                    f"  String (dimensions): "
                    f"{info.get('string_columns', [])}"
                )

            schema = "\n\n".join(schema_lines)

            # Logging for verification
            logger.info(
                "Dashboard schema prepared",
                schema_length=len(schema),
                schema_preview=schema[:500],
                tables_found=len(tables)
            )

            # Warn clearly if schema is empty
            if not schema:
                logger.warning(
                    "Dashboard schema is empty",
                    dataset_id=dataset_id,
                    metadata_keys=list(metadata.keys())
                    if metadata else []
                )

        except Exception as e:
            logger.warning(
                "Schema discovery failed",
                error=str(e)[:200]
            )

        # ----------------------------------------------
        # 4B. Build Dashboard
        # ----------------------------------------------
        agent = DashboardAnalystAgent()

        result = await agent.run(
            persona_id=persona_id,
            schema=schema,
            period=period,
        )

    except Exception as e:
        logger.warning(
            "Dashboard agent failed, using fallback",
            error=str(e)[:200]
        )

    # --------------------------------------------------
    # 5. Fall back to static dashboard
    # --------------------------------------------------
    if not result:
        result = _build_fallback_dashboard(
            persona,
            persona_id,
            period
        )

    duration_ms = int(
        (time.monotonic() - t0) * 1000
    )

    result["duration_ms"] = duration_ms
    result["from_cache"] = False
    result["user_id"] = user_id

    # --------------------------------------------------
    # 6. Cache dashboard
    # --------------------------------------------------
    _cache[cache_key] = {
        "data": result,
        "ts": time.time()
    }

    return JSONResponse(content=result)


@router.get("/dashboard/personas/list")
async def list_personas():
    """Return all available personas."""

    valid = get_all_persona_ids()

    personas = []

    for pid in valid:

        p = get_persona(pid)

        personas.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "icon": p.get("icon"),
            "tagline": p.get("tagline"),
            "focus": p.get("focus", []),
        })

    return JSONResponse(
        content={
            "personas": personas
        }
    )


@router.delete("/dashboard/cache/{persona_id}")
async def clear_cache(persona_id: str):
    """Manually clear dashboard cache."""

    keys = [
        key for key in _cache
        if key.startswith(persona_id)
    ]

    for key in keys:
        del _cache[key]

    return JSONResponse(
        content={
            "cleared": len(keys)
        }
    )


def _build_fallback_dashboard(
    persona: dict,
    persona_id: str,
    period: str
) -> dict:
    """
    Static fallback dashboard used when BQ agent fails.
    """

    name = persona.get("name", "Analyst")
    icon = persona.get("icon", "🔍")

    # Persona-specific KPIs
    persona_kpis = {

        "ceo": [
            {
                "label": "Total Subscribers",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "ARPU",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Market Share",
                "value": "~32%",
                "change": "Stable",
                "trend": "neutral"
            },
            {
                "label": "Net Movement",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
        ],

        "marketing": [
            {
                "label": "Gross INFLOW",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Top Channel",
                "value": "Affiliate",
                "change": "Leading",
                "trend": "up"
            },
            {
                "label": "Best Plan",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Net New",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
        ],

        "product": [
            {
                "label": "Top Plan Subs",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Postpay Mix",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Plan Churn",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Bundle Adoption",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
        ],

        "operations": [
            {
                "label": "Gross OUTFLOW",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Churn Rate",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Retention Rate",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Net Movement",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
        ],

        "analyst": [
            {
                "label": "Total Records",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Date Range",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Dimensions",
                "value": "Loading...",
                "change": "—",
                "trend": "neutral"
            },
            {
                "label": "Anomalies",
                "value": "0",
                "change": "—",
                "trend": "neutral"
            },
        ],
    }

    kpis = persona_kpis.get(
        persona_id,
        persona_kpis["analyst"]
    )

    return {
        "persona_id": persona_id,
        "persona_name": name,
        "persona_icon": icon,
        "tagline": persona.get("tagline", ""),
        "period": period,

        "kpis": kpis,

        "layers": [
            {
                "id": "overview",
                "label": "Overview",
                "icon": "📊",

                "charts": [
                    {
                        "title": "Subscriber Trend (6 months)",
                        "type": "line",
                        "data": [],
                        "row_count": 0,
                        "auto_selected": True,
                        "selection_reason":
                            "Time series — ask a question to populate",
                        "error":
                            "Run a query to load chart data",
                    },
                    {
                        "title": "Channel Mix",
                        "type": "donut",
                        "data": [],
                        "row_count": 0,
                        "auto_selected": True,
                        "selection_reason":
                            "Share analysis — ask a question to populate",
                        "error":
                            "Run a query to load chart data",
                    },
                ]
            }
        ],

        "story": {
            "headline": (
                f"Welcome to your {name} dashboard — "
                f"ask a question below to populate the charts with live data."
            ),

            "what_happened": (
                "Your persona dashboard is ready. "
                "Ask a question in the chat to generate charts and "
                "insights tailored to your role."
            ),

            "why": (
                "Dashboard data loads dynamically from your "
                "BigQuery analytics tables."
            ),

            "what_to_do": (
                f"Use the recommended questions below to get started "
                f"with your {name.lower()} analysis."
            ),

            "citations": [
                {
                    "type": "Market",
                    "icon": "🌍",
                    "text": (
                        "Vodafone Ireland holds ~32% of the ~5.2M "
                        "Irish mobile market, ahead of Eir (28%) "
                        "and Three Ireland (22%)"
                    ),
                },
            ],

            "smart_insights": [
                {
                    "severity": "info",
                    "title": "Dashboard Ready",
                    "text": (
                        f"Your {name} view is personalised — "
                        f"ask a question to load live data"
                    ),
                    "action": (
                        "Use the recommended questions below "
                        "to get started"
                    ),
                }
            ],

            "confidence": 100,
        },

        "suggested_questions": persona.get(
            "suggested_questions",
            [
                "Show subscriber count for May 2026",
                "What is the INFLOW by channel this month?",
                "Show ARPU trend for the last 6 months",
                "Show INFLOW vs OUTFLOW waterfall for May 2026",
                "Which product plan has the most subscribers?",
            ]
        ),
    }