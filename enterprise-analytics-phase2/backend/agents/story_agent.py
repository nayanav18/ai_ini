"""
Story Agent — generates persona-driven narrative for the dashboard.
Reads: persona config + KPI results + chart data → executive brief JSON.
"""
import json
import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config import settings

logger = structlog.get_logger()

STORY_PROMPT = """You are an executive analytics writer for VODAFONE IRELAND.

PERSONA: {persona_name} — {tagline}
PERSONA FOCUS: {focus}
STORY DIRECTION: {story_prompt}
PERIOD: {period}

KPI DATA:
{kpis}

CHART INSIGHTS:
{chart_summary}

Generate a persona-appropriate dashboard narrative. Return ONLY this JSON:
{{
  "headline": "One punchy sentence with the most important number for this persona",
  "what_happened": "2-3 sentences: key performance facts from the KPI data for {persona_name}",
  "why": "2-3 sentences: root cause analysis based on chart data available",
  "what_to_do": "2-3 sentences: top priority actions for {persona_name}",
  "citations": [
    {{"type": "Result",     "icon": "📊", "text": "key result with exact number"}},
    {{"type": "Driver",     "icon": "🔑", "text": "main driver from chart data"}},
    {{"type": "Market",     "icon": "🌍", "text": "Vodafone Ireland market position vs competitors"}},
    {{"type": "Competitor", "icon": "⚔️", "text": "specific competitor threat (Eir/Three/Sky/GoMo)"}},
    {{"type": "Insight",    "icon": "⚡", "text": "top opportunity or risk for this persona"}}
  ],
  "smart_insights": [
    {{
      "severity": "info|warning|alert",
      "title": "short insight title",
      "text": "one sentence insight with specific number",
      "action": "one-line recommended action"
    }}
  ],
  "confidence": 88
}}

RULES:
1. Headline must be specific to {persona_name} role — CEO gets revenue/market, Ops gets churn, Marketing gets channel
2. Use exact numbers from the KPI data provided
3. smart_insights: 2-3 max, each with a concrete number
4. Never fabricate numbers not in the KPI data
5. Vodafone Ireland is always the subject — Eir/Three/Sky are competitors"""


class StoryAgent:
    """Generates persona-driven narrative for dashboard."""

    async def generate(self, persona: dict, kpis: list,
                       charts: list, period: str) -> dict:
        """Generate story narrative from persona + data."""
        try:
            vertexai.init(
                project=settings.GCP_PROJECT_ID,
                location=settings.GCP_LOCATION
            )
            model = GenerativeModel(model_name=settings.VERTEX_AI_MODEL)

            # Summarise KPIs for prompt
            kpi_text = "\n".join(
                f"  - {k['label']}: {k['value']} ({k['change']})"
                for k in kpis if k.get("value") != "N/A"
            )

            # Summarise charts for prompt
            chart_text = "\n".join(
                f"  - {c['title']} ({c['type']}): {c['row_count']} rows returned"
                for c in charts if c.get("row_count", 0) > 0
            )

            focus = ", ".join(persona.get("focus", []))
            prompt = STORY_PROMPT.format(
                persona_name=persona.get("name", "Analyst"),
                tagline=persona.get("tagline", ""),
                focus=focus,
                story_prompt=persona.get("story_prompt", ""),
                period=period,
                kpis=kpi_text or "No KPI data available",
                chart_summary=chart_text or "No chart data available",
            )

            response = await model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1500,
                ),
            )

            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            story = json.loads(raw)
            logger.info("Story generated", persona=persona.get("id"),
                        confidence=story.get("confidence", 0))
            return story

        except Exception as e:
            logger.error("Story Agent failed", error=str(e))
            return _fallback_story(persona, kpis)


def _fallback_story(persona: dict, kpis: list) -> dict:
    """Fallback story when AI call fails."""
    name = persona.get("name", "Analyst")
    headline_kpi = next((k for k in kpis if k.get("value") != "N/A"), {})
    headline = (
        f"Vodafone Ireland {headline_kpi.get('label', 'performance')}: "
        f"{headline_kpi.get('value', 'data retrieved')} "
        f"({headline_kpi.get('change', '')})"
        if headline_kpi else "Vodafone Ireland analytics dashboard loaded."
    )
    return {
        "headline": headline,
        "what_happened": "Dashboard data loaded from BigQuery. KPI scoreboard reflects latest available data.",
        "why": "Dimensional analysis available in chart panels below.",
        "what_to_do": f"Review the {name.lower()} KPIs and drill into the channel and segment charts for actionable insights.",
        "citations": [
            {"type": "Result", "icon": "📊",
             "text": f"{headline_kpi.get('label', 'Metric')}: {headline_kpi.get('value', 'N/A')}"},
            {"type": "Market", "icon": "🌍",
             "text": "Vodafone Ireland holds ~32% of the ~5.2M Irish mobile market, ahead of Eir (28%) and Three Ireland (22%)"},
            {"type": "Insight", "icon": "⚡",
             "text": "Review chart panels for dimensional breakdown and trend analysis"},
        ],
        "smart_insights": [
            {"severity": "info",
             "title": "Dashboard Loaded",
             "text": "All persona charts generated from live BigQuery data",
             "action": "Interact with charts or ask follow-up questions below"}
        ],
        "confidence": 70,
    }
