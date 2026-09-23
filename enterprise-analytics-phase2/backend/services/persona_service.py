"""
persona_service.py — AI-first persona service.
Tries YAML file first, then hardcoded fallbacks, then generates via Gemini.
All persona content is either from config or AI-generated — never empty.
"""
import yaml
import json
import os
import structlog
from functools import lru_cache

logger = structlog.get_logger()
DEFAULT_PERSONA_ID = "analyst"

_POSSIBLE_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "data", "personas.yaml"),
    os.path.join(os.getcwd(), "data", "personas.yaml"),
    os.path.join(os.getcwd(), "personas.yaml"),
    os.path.expanduser("~/personas.yaml"),
]

# ── Gemini AI persona generation ────────────────────────────────────────────

AI_PERSONA_PROMPT = """You are configuring a Vodafone Ireland analytics dashboard.
Generate a full persona configuration for role: "{persona_id}".

Return ONLY this JSON (no preamble, no markdown):
{{
  "id": "{persona_id}",
  "name": "Role display name",
  "icon": "single emoji",
  "tagline": "One line description of their analytics focus",
  "focus": ["focus_area_1", "focus_area_2", "focus_area_3"],
  "default_kpis": [
    {{"label": "KPI Name", "column_hint": "BQ_column_name", "format": "number|percent|currency_eur|text", "goal": "maximize|minimize|track"}},
    {{"label": "KPI Name", "column_hint": "BQ_column_name", "format": "number", "goal": "maximize"}},
    {{"label": "KPI Name", "column_hint": "BQ_column_name", "format": "number", "goal": "maximize"}},
    {{"label": "KPI Name", "column_hint": "BQ_column_name", "format": "number_signed", "goal": "maximize"}}
  ],
  "story_prompt": "What narrative direction this persona cares about for Vodafone Ireland",
  "question_style": "strategic|tactical|analytical|operational|exploratory",
  "suggested_questions": [
    "Question 1 about Vodafone Ireland subscriber data",
    "Question 2",
    "Question 3",
    "Question 4",
    "Question 5"
  ]
}}

Available BQ columns: Subscriber_Count_CM, INFLOW, OUTFLOW, net_movement, ARPU,
Channel, Price_Plan, Customer_Subscriber_Type_Description_Q, Transaction_Type,
Reporting_Date_Filter, Churn_Rate, market_share"""

AI_PROMPT_INJECTION = """You are configuring a Vodafone Ireland analytics AI prompt.
Generate a persona context injection block for persona_id="{persona_id}", name="{persona_name}".
This text will be injected at the top of an analytics prompt.

Cover: role description, focus areas, preferred KPIs (with BQ column hints),
story direction, question style, and 3 example questions.
Be specific to Vodafone Ireland telecoms context.
Return plain text only — no JSON, no markdown."""


def _generate_persona_sync(persona_id: str) -> dict:
    """Synchronous Gemini call to generate a persona config."""
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig
        from config import settings

        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        model = GenerativeModel(model_name=settings.VERTEX_AI_MODEL)

        response = model.generate_content(
            AI_PERSONA_PROMPT.format(persona_id=persona_id),
            generation_config=GenerationConfig(temperature=0.3, max_output_tokens=800),
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        persona = json.loads(raw)
        if isinstance(persona, dict) and persona.get("id"):
            logger.info("AI-generated persona", persona_id=persona_id)
            return persona
    except Exception as e:
        logger.error("AI persona generation failed", persona_id=persona_id, error=str(e))
    return {}


# ── Persona loading ──────────────────────────────────────────────────────────

def _find_personas_file():
    for path in _POSSIBLE_PATHS:
        resolved = os.path.normpath(path)
        if os.path.exists(resolved):
            return resolved
    return None


@lru_cache(maxsize=1)
def load_personas() -> dict:
    path = _find_personas_file()
    if path:
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            personas = {p["id"]: p for p in data.get("personas", [])}
            if personas:
                logger.info("Personas loaded from YAML", count=len(personas))
                return personas
        except Exception as e:
            logger.error("YAML parse failed", error=str(e))

    logger.warning("No YAML found — using built-in personas")
    return _builtin_personas()


def get_persona(persona_id: str) -> dict:
    """Get persona — tries YAML, then built-in, then AI-generates."""
    persona_id = persona_id or DEFAULT_PERSONA_ID
    personas = load_personas() or {}

    # 1. Try requested persona
    p = personas.get(persona_id)
    if p and isinstance(p, dict):
        return p

    # 2. Try AI generation
    logger.warning("Persona not in config, generating via AI", persona_id=persona_id)
    p = _generate_persona_sync(persona_id)
    if p:
        return p

    # 3. Try default analyst
    p = personas.get(DEFAULT_PERSONA_ID)
    if p and isinstance(p, dict):
        logger.warning("Using default analyst persona", requested=persona_id)
        return p

    # 4. Absolute fallback
    return _analyst_persona()


def get_all_persona_ids() -> list:
    return list(load_personas().keys())


def get_dashboard_config(persona_id: str) -> dict:
    p = get_persona(persona_id)
    return {
        "persona_id":          p.get("id", persona_id),
        "persona_name":        p.get("name", "Analyst"),
        "persona_icon":        p.get("icon", "🔍"),
        "tagline":             p.get("tagline", ""),
        "default_kpis":        p.get("default_kpis", []),
        "dashboard_layers":    p.get("dashboard_layers", []),
        "story_prompt":        p.get("story_prompt", ""),
        "suggested_questions": p.get("suggested_questions", []),
        "question_style":      p.get("question_style", "analytical"),
    }


def get_persona_prompt_injection(persona_id: str) -> str:
    """
    Returns a persona context string for Gemini prompt injection.
    Tries structured persona data first, then AI-generates the injection text.
    Never returns None or empty string.
    """
    persona_id = persona_id or DEFAULT_PERSONA_ID

    try:
        p = get_persona(persona_id)

        focus = "\n".join(f"  - {f}" for f in (p.get("focus") or []) if f)
        kpis  = "\n".join(
            f"  - {k['label']}: column hint '{k.get('column_hint', '')}'"
            for k in (p.get("default_kpis") or [])
            if isinstance(k, dict) and k.get("label")
        )
        qs = "\n".join(f"  - {q}" for q in (p.get("suggested_questions") or []) if q)

        result = f"""USER PERSONA: {p.get('name', 'Analyst')} ({p.get('id', persona_id)})
Role: {p.get('tagline', '')}
FOCUS AREAS:
{focus}
PREFERRED KPIs:
{kpis}
STORY DIRECTION: {p.get('story_prompt', '')}
QUESTION STYLE: {p.get('question_style', 'analytical')}
EXAMPLE QUESTIONS:
{qs}
Tailor ALL analysis, KPIs, charts and questions to this persona's role."""

        if result.strip():
            return result.strip()

    except Exception as e:
        logger.warning("Structured persona injection failed", error=str(e))

    # AI-generate the injection text directly
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig
        from config import settings

        vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        model = GenerativeModel(model_name=settings.VERTEX_AI_MODEL)
        response = model.generate_content(
            AI_PROMPT_INJECTION.format(
                persona_id=persona_id,
                persona_name=persona_id.replace("_", " ").title()
            ),
            generation_config=GenerationConfig(temperature=0.3, max_output_tokens=400),
        )
        text = response.text.strip()
        if text:
            logger.info("AI-generated persona prompt injection", persona_id=persona_id)
            return text
    except Exception as e:
        logger.error("AI prompt injection failed", error=str(e))

    return f"USER PERSONA: {persona_id.replace('_', ' ').title()}\nRole: Vodafone Ireland analytics user.\nFocus on subscriber metrics, trends and business insights."


def reload_personas() -> dict:
    load_personas.cache_clear()
    return load_personas()


# ── Built-in personas (used only if YAML missing) ───────────────────────────

def _builtin_personas() -> dict:
    return {p["id"]: p for p in [
        _analyst_persona(), _ceo_persona(),
        _marketing_persona(), _product_persona(), _ops_persona()
    ]}


def _analyst_persona() -> dict:
    return {
        "id": "analyst", "name": "Data Analyst", "icon": "🔍",
        "tagline": "Full analytics — all metrics, trends and dimensional analysis",
        "focus": ["all_metrics", "trends", "dimensional_breakdown"],
        "default_kpis": [
            {"label": "Total Subscribers", "column_hint": "Subscriber_Count_CM", "format": "number",        "goal": "maximize"},
            {"label": "Gross INFLOW",       "column_hint": "INFLOW",              "format": "number",        "goal": "maximize"},
            {"label": "Gross OUTFLOW",      "column_hint": "OUTFLOW",             "format": "number",        "goal": "minimize"},
            {"label": "Net Movement",       "column_hint": "net_movement",        "format": "number_signed", "goal": "maximize"},
        ],
        "story_prompt": "Provide comprehensive analytics across all available metrics and dimensions.",
        "question_style": "exploratory",
        "suggested_questions": [
            "Show subscriber count trend for the last 6 months — line chart",
            "Which channel drove the most INFLOW this month?",
            "Show heatmap of subscribers by channel and customer segment",
            "What is the churn rate by subscriber type for May 2026?",
            "Show INFLOW vs OUTFLOW waterfall for the current period",
        ],
    }


def _ceo_persona() -> dict:
    return {
        "id": "ceo", "name": "CEO / Executive", "icon": "👔",
        "tagline": "Revenue, market leadership and strategic position",
        "focus": ["total_subscribers", "revenue", "market_share", "arpu", "competitive_position"],
        "default_kpis": [
            {"label": "Total Subscribers", "column_hint": "Subscriber_Count_CM", "format": "number",        "goal": "maximize"},
            {"label": "ARPU",              "column_hint": "ARPU",                "format": "currency_eur",  "goal": "maximize"},
            {"label": "Market Share",      "column_hint": "market_share",        "format": "percent",       "goal": "maximize"},
            {"label": "Net Movement",      "column_hint": "net_movement",        "format": "number_signed", "goal": "maximize"},
        ],
        "story_prompt": "Focus on market share vs Eir and Three Ireland, subscriber growth, revenue and ARPU trends.",
        "question_style": "strategic",
        "suggested_questions": [
            "Show Vodafone Ireland subscriber trend for 2026 — line chart",
            "What drove revenue growth or decline in May 2026?",
            "How does Vodafone Ireland ARPU compare to the Ireland market?",
            "What is our market share trajectory for Q2 2026?",
            "Show INFLOW vs OUTFLOW waterfall for May 2026",
        ],
    }


def _marketing_persona() -> dict:
    return {
        "id": "marketing", "name": "Marketing Director", "icon": "📢",
        "tagline": "Acquisition, channel ROI and campaign performance",
        "focus": ["inflow_transactions", "channel_performance", "plan_performance", "segment_growth"],
        "default_kpis": [
            {"label": "Gross INFLOW",       "column_hint": "INFLOW",       "format": "number",        "goal": "maximize"},
            {"label": "Top Channel",        "column_hint": "Channel",      "format": "text",          "goal": "track"},
            {"label": "Best Plan",          "column_hint": "Price_Plan",   "format": "text",          "goal": "track"},
            {"label": "Net New Subscribers","column_hint": "net_movement", "format": "number_signed", "goal": "maximize"},
        ],
        "story_prompt": "Focus on acquisition: which channels drive INFLOW, which plans perform best, what to amplify.",
        "question_style": "tactical",
        "suggested_questions": [
            "Which channel drove the most INFLOW in May 2026 — bar chart?",
            "What is the top performing product plan by subscriber count?",
            "Show channel INFLOW trend over 6 months",
            "Which customer segment is growing fastest by channel?",
            "Show INFLOW vs OUTFLOW by channel — waterfall chart",
        ],
    }


def _product_persona() -> dict:
    return {
        "id": "product", "name": "Product Manager", "icon": "📦",
        "tagline": "Plan performance, ARPU and bundle adoption",
        "focus": ["plan_performance", "arpu_by_plan", "bundle_adoption", "product_mix"],
        "default_kpis": [
            {"label": "Top Plan Subscribers","column_hint": "Price_Plan",   "format": "number",        "goal": "maximize"},
            {"label": "Plan INFLOW",         "column_hint": "INFLOW",       "format": "number",        "goal": "maximize"},
            {"label": "Plan OUTFLOW",        "column_hint": "OUTFLOW",      "format": "number",        "goal": "minimize"},
            {"label": "Net Movement",        "column_hint": "net_movement", "format": "number_signed", "goal": "maximize"},
        ],
        "story_prompt": "Focus on product mix: which plans grow and decline, postpay vs prepay balance, plan-level churn signals.",
        "question_style": "analytical",
        "suggested_questions": [
            "Which product plans have the highest subscriber count — bar chart?",
            "What is the postpay vs prepay split for May 2026?",
            "Show INFLOW and OUTFLOW by product plan — waterfall",
            "Which plans have the highest churn in May 2026?",
            "Show top 5 plans by INFLOW growth over 6 months",
        ],
    }


def _ops_persona() -> dict:
    return {
        "id": "operations", "name": "Operations Manager", "icon": "⚙️",
        "tagline": "Churn management, retention and service quality",
        "focus": ["churn_rate", "outflow_reasons", "retention_rate", "at_risk_segments"],
        "default_kpis": [
            {"label": "Gross OUTFLOW",  "column_hint": "OUTFLOW",     "format": "number",        "goal": "minimize"},
            {"label": "Churn Rate",     "column_hint": "Churn_Rate",  "format": "percent",       "goal": "minimize"},
            {"label": "Retention Rate", "column_hint": "retention",   "format": "percent",       "goal": "maximize"},
            {"label": "Net Movement",   "column_hint": "net_movement","format": "number_signed", "goal": "maximize"},
        ],
        "story_prompt": "Focus on churn: which segments have highest OUTFLOW, churn trend, and urgent retention actions.",
        "question_style": "operational",
        "suggested_questions": [
            "Show OUTFLOW trend by month for the last 6 months — line chart",
            "Which customer segment has the highest churn in May 2026?",
            "What product plans have the most OUTFLOW — bar chart?",
            "Show INFLOW vs OUTFLOW balance by channel — waterfall",
            "Which plans are losing subscribers fastest?",
        ],
    }
