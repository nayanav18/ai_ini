"""
Planner Agent — understands user intent and creates an execution plan.
"""
from agents.base_agent import BaseAgent
from services.vertex_client import generate_analytics

PLANNER_PROMPT = """You are the Planner Agent for an enterprise analytics platform.
Analyse the user query and return ONLY this JSON:
{
  "intent": "kpi|trend|comparison|root_cause|recommendation|report",
  "metric": "primary metric name",
  "dimensions": ["list", "of", "dimensions"],
  "time_period": "e.g. May 2026 or last quarter",
  "filters": {"key": "value"},
  "requires_agents": ["data","rootcause","recommendation"],
  "sql_hint": "optional hint about the query structure"
}"""


class PlannerAgent(BaseAgent):
    agent_id = "planner"
    label = "Planner"

    async def _execute(self, context: dict) -> dict:
        plan_raw = await generate_analytics(
            system_prompt=PLANNER_PROMPT,
            history=[],
            user_query=context["query"],
        )
        context["plan"] = plan_raw
        return context
