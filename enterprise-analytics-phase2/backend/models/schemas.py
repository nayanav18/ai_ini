"""
schemas.py — Complete Pydantic models for Phase 1 + Phase 2.
Copy to: backend/models/schemas.py
REPLACES the existing file completely.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Any
from datetime import datetime


# ── Chat ──────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    dataset_id: str
    conversation_id: Optional[str] = None
    history: List[ChatMessage] = []
    # Phase 2 additions (optional — won't break Phase 1 calls)
    user_id: Optional[str] = None
    persona_id: Optional[str] = "analyst"


# ── KPI ───────────────────────────────────────────────────────────────────

class KPI(BaseModel):
    label: str = ""
    value: str = ""
    change: str = "N/A"
    trend: Literal["up", "down", "neutral"] = "neutral"

    @field_validator("value", "change", "label", mode="before")
    @classmethod
    def coerce_to_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator("trend", mode="before")
    @classmethod
    def validate_trend(cls, v: Any) -> str:
        v = str(v).lower()
        return v if v in ("up", "down", "neutral") else "neutral"


# ── Root Cause ────────────────────────────────────────────────────────────

class RootCause(BaseModel):
    driver: str = ""
    impact: Literal["High", "Medium", "Low"] = "Medium"
    confidence: int = Field(default=70, ge=0, le=100)
    detail: str = ""
    category: Optional[str] = "Internal"

    @field_validator("impact", mode="before")
    @classmethod
    def validate_impact(cls, v: Any) -> str:
        v = str(v).capitalize()
        return v if v in ("High", "Medium", "Low") else "Medium"


# ── Recommendation ────────────────────────────────────────────────────────

class Recommendation(BaseModel):
    action: str = ""
    type: Literal["Strategic", "Tactical", "Immediate"] = "Tactical"
    detail: str = ""
    priority: Optional[str] = "P2"
    timeline: Optional[str] = ""
    expected_impact: Optional[str] = ""

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: Any) -> str:
        v = str(v).capitalize()
        return v if v in ("Strategic", "Tactical", "Immediate") else "Tactical"


# ── Risk ──────────────────────────────────────────────────────────────────

class Risk(BaseModel):
    risk: str = ""
    severity: Literal["High", "Medium", "Low"] = "Medium"
    mitigation: str = ""

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v: Any) -> str:
        v = str(v).capitalize()
        return v if v in ("High", "Medium", "Low") else "Medium"


# ── Chart ─────────────────────────────────────────────────────────────────

class ChartDataPoint(BaseModel):
    label: str = ""
    value: float = 0.0

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value(cls, v: Any) -> float:
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    @field_validator("label", mode="before")
    @classmethod
    def coerce_label(cls, v: Any) -> str:
        return str(v) if v is not None else ""


class Chart(BaseModel):
    type: Literal["line", "bar", "funnel", "waterfall", "donut", "pie",
                  "stacked_bar", "grouped_bar", "heatmap", "scatter", "area", "kpi_card"] = "line"
    title: str = ""
    data: List[ChartDataPoint] = []


# ── Market & Competitor ───────────────────────────────────────────────────

class MarketAnalysis(BaseModel):
    market_position: str = ""
    market_trends: List[str] = []
    market_size: Optional[str] = ""
    growth_outlook: str = ""


class CompetitorItem(BaseModel):
    name: str = ""
    position: str = ""
    threat_level: Literal["High", "Medium", "Low"] = "Medium"
    insight: str = ""

    @field_validator("threat_level", mode="before")
    @classmethod
    def validate_threat(cls, v: Any) -> str:
        v = str(v).capitalize()
        return v if v in ("High", "Medium", "Low") else "Medium"


class CompetitorAnalysis(BaseModel):
    competitive_landscape: str = ""
    competitors: List[CompetitorItem] = []
    competitive_advantage: str = ""
    competitive_risk: str = ""


# ── Agent Step ────────────────────────────────────────────────────────────

class AgentStep(BaseModel):
    agent_id: str = ""
    label: str = ""
    status: Literal["pending", "running", "done", "error"] = "done"
    duration_ms: Optional[int] = None


# ── Main Analytics Response ───────────────────────────────────────────────

class AnalyticsResponse(BaseModel):
    conversation_id: str = ""
    what_happened: str = ""
    kpis: List[KPI] = []
    business_context: Optional[str] = ""
    why_it_happened: str = ""
    root_causes: List[RootCause] = []
    market_analysis: Optional[MarketAnalysis] = None
    competitor_analysis: Optional[CompetitorAnalysis] = None
    what_to_do: str = ""
    recommendations: List[Recommendation] = []
    risks: List[Risk] = []
    chart: Optional[Chart] = None
    actions: List[str] = []
    agent_steps: List[AgentStep] = []
    dataset: str = ""
    query: str = ""
    generated_at: Optional[datetime] = None
    summary_bullets: Optional[List[str]] = []
    suggested_questions: Optional[List[str]] = []


# ── Insights (Phase 1) ────────────────────────────────────────────────────

class SaveInsightRequest(BaseModel):
    conversation_id: str = ""
    query: str = ""
    analytics: Optional[dict] = {}
    dataset_id: str = "ireland"
    # Phase 2 extras
    user_id: Optional[str] = None
    persona_id: Optional[str] = "analyst"
    title: Optional[str] = ""
    tags: Optional[List[str]] = []


class InsightSummary(BaseModel):
    id: str = ""
    query: str = ""
    dataset: str = ""
    what_happened: str = ""
    kpis: List[KPI] = []
    created_at: Optional[datetime] = None


# ── Datasets ──────────────────────────────────────────────────────────────

class DatasetInfo(BaseModel):
    id: str
    label: str
    flag: str = ""
    description: str = ""
    bigquery_table: Optional[str] = None
    available: bool = True


# ── Phase 2: Clarification (Guardrails) ──────────────────────────────────

class ColumnOption(BaseModel):
    column: str = ""
    description: str = ""


class ClarificationResponse(BaseModel):
    is_clarification_needed: bool = True
    clarification_question: str = ""
    matching_columns: List[ColumnOption] = []
    original_query: str = ""
    suggested_reformulations: List[str] = []
