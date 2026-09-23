"""Data Agent: generates and executes the data queries required by analytics."""
import json
import re

import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from agents.base_agent import BaseAgent
from config import settings
from services.bigquery_service import run_query

logger = structlog.get_logger()

SQL_GEN_PROMPT = """You are a BigQuery Standard SQL expert for an enterprise analytics platform.

Generate MULTIPLE SQL queries to answer the user question. Return ONLY a JSON object with exactly:
{
  "current_period": "SQL for the primary requested metric and period",
  "previous_period": "SQL for the comparable previous period",
  "by_dimensions": "SQL for the requested dimensional breakdown, or a safe empty result if no breakdown was requested",
  "trend": "SQL for a monthly/periodic trend when a date column exists"
}

Rules:
- Use only exact table and column names from the supplied schema.
- Use fully qualified BigQuery table names with backticks.
- Never invent columns, aliases used as source columns, or dimensions.
- If a metric is a snapshot/current-state metric (for example Subscriber_Count_CM), do NOT SUM it for a total. Use an appropriate snapshot aggregation such as MAX for the requested period.
- Use SUM for additive transaction measures such as INFLOW/OUTFLOW when the schema supports it.
- For dimensional breakdowns, group by the requested existing dimension and aggregate the metric consistently.
- Only add a date filter when a date column exists.
- For a specific month, filter that month. For a quarter/year, filter the requested range.
- For trend output, aggregate by month and order chronologically.
- Do not use SELECT *.
- Keep current/previous queries to one aggregate row when possible.
- LIMIT 50 for dimensions and LIMIT 24 for trend.
- Return executable SQL only inside the JSON values.

SCHEMA:
{schema}

USER QUESTION:
{query}
"""


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _schema_text(metadata: dict) -> str:
    lines = []
    for table_name, info in metadata.get("tables", {}).items():
        lines.append(
            f"Table: {info['full_name']}\n"
            f"  Numeric (metrics): {info.get('numeric_columns', [])}\n"
            f"  Date columns: {info.get('date_columns', [])}\n"
            f"  String (dimensions): {info.get('string_columns', [])}"
        )
    return "\n\n".join(lines)


def _find_table_with_column(metadata: dict, column: str) -> dict | None:
    for info in metadata.get("tables", {}).values():
        if column in info.get("numeric_columns", []) or column in info.get("columns", []):
            return info
    return None


def _find_exact_column(metadata: dict, column: str) -> tuple[dict | None, str | None]:
    for info in metadata.get("tables", {}).values():
        for candidate in info.get("columns", []):
            name = candidate.get("name") if isinstance(candidate, dict) else str(candidate)
            if name == column:
                return info, candidate.get("type") if isinstance(candidate, dict) else None
    return None, None


def _date_bounds(query: str) -> tuple[str | None, str | None]:
    """Return ISO start/end dates for explicit month, quarter, or year requests."""
    q = _normalise_text(query)
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    m = re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(20\d{2})\b", q)
    if m:
        year, month = int(m.group(2)), months[m.group(1)]
        if month == 12:
            end = f"{year + 1:04d}-01-01"
        else:
            end = f"{year:04d}-{month + 1:02d}-01"
        return f"{year:04d}-{month:02d}-01", end

    q_match = re.search(r"\bq([1-4])\s*(20\d{2})\b", q)
    if q_match:
        quarter, year = int(q_match.group(1)), int(q_match.group(2))
        start_month = (quarter - 1) * 3 + 1
        end_year = year + (1 if quarter == 4 else 0)
        end_month = 1 if quarter == 4 else start_month + 3
        return f"{year:04d}-{start_month:02d}-01", f"{end_year:04d}-{end_month:02d}-01"

    y_match = re.search(r"\b(20\d{2})\b", q)
    if y_match:
        year = int(y_match.group(1))
        return f"{year:04d}-01-01", f"{year + 1:04d}-01-01"
    return None, None


def _date_expr(column: str, field_type: str | None) -> str:
    if field_type == "DATE":
        return f"`{column}`"
    return f"DATE(`{column}`)"


def _month_shift(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + month - 1 + delta
    return idx // 12, idx % 12 + 1


def _previous_bounds(query: str) -> tuple[str | None, str | None]:
    start, end = _date_bounds(query)
    if not start or not end:
        return None, None
    y, m = map(int, start[:7].split("-"))
    if end.endswith("01-01") and int(end[:4]) == y + 1:
        return f"{y - 1:04d}-01-01", f"{y:04d}-01-01"
    # explicit month / quarter: previous period has the same duration
    ey, em = map(int, end[:7].split("-"))
    months = (ey - y) * 12 + (em - m)
    py, pm = _month_shift(y, m, -months)
    pey, pem = _month_shift(ey, em, -months)
    return f"{py:04d}-{pm:02d}-01", f"{pey:04d}-{pem:02d}-01"


def _period_clause(date_column: str | None, field_type: str | None, start: str | None, end: str | None) -> str:
    if not date_column or not start or not end:
        return ""
    expr = _date_expr(date_column, field_type)
    return f"WHERE {expr} >= DATE '{start}' AND {expr} < DATE '{end}'"


def _subscriber_queries(query: str, metadata: dict) -> dict | None:
    """Build deterministic subscriber-count queries when the exact snapshot field exists."""
    table = _find_table_with_column(metadata, "Subscriber_Count_CM")
    if not table:
        return None

    date_column = table.get("date_column")
    field_type = None
    for col in table.get("columns", []):
        if col.get("name") == date_column:
            field_type = col.get("type")
            break

    full_table = f"`{table['full_name']}`"
    q = _normalise_text(query)
    start, end = _date_bounds(query)
    prev_start, prev_end = _previous_bounds(query)

    # A total subscriber question is a snapshot. MAX prevents the same snapshot
    # being multiplied by dimensional rows in a denormalised table.
    current_where = _period_clause(date_column, field_type, start, end)
    if not current_where and date_column:
        date_expr = _date_expr(date_column, field_type)
        current_where = f"WHERE {date_expr} = (SELECT MAX({date_expr}) FROM {full_table})"

    previous_where = _period_clause(date_column, field_type, prev_start, prev_end)
    if not previous_where and date_column:
        date_expr = _date_expr(date_column, field_type)
        previous_where = (
            f"WHERE {date_expr} = (SELECT MAX({date_expr}) FROM {full_table} "
            f"WHERE {date_expr} < (SELECT MAX({date_expr}) FROM {full_table}))"
        )

    current_sql = f"SELECT MAX(`Subscriber_Count_CM`) AS value FROM {full_table} {current_where}"
    previous_sql = f"SELECT MAX(`Subscriber_Count_CM`) AS value FROM {full_table} {previous_where}"

    asks_breakdown = bool(re.search(r"\b(by|per|breakdown|group|grouped|mix|channel|segment|plan|type)\b", q))
    dimensions = table.get("string_columns", [])
    preferred_dimension = next(
        (d for d in dimensions if d.lower() in q and d != "Subscriber_Count_CM"),
        None,
    )
    if not preferred_dimension:
        dimension_aliases = {
            "channel": "Channel",
            "segment": "Customer_Subscriber_Type_Description_Q",
            "plan": "Price_Plan",
            "customer type": "Customer_Subscriber_Type_Description_Q",
            "subscriber type": "subscriber_type",
        }
        for word, col in dimension_aliases.items():
            if word in q and col in dimensions:
                preferred_dimension = col
                break

    if asks_breakdown and preferred_dimension:
        breakdown_where = _period_clause(date_column, field_type, start, end)
        dimensions_sql = (
            f"SELECT `{preferred_dimension}` AS label, SUM(`Subscriber_Count_CM`) AS value "
            f"FROM {full_table} {breakdown_where} "
            f"GROUP BY `{preferred_dimension}` ORDER BY value DESC LIMIT 12"
        )
    else:
        dimensions_sql = current_sql

    if date_column:
        date_expr = _date_expr(date_column, field_type)
        trend_sql = (
            f"SELECT FORMAT_DATE('%Y-%m', DATE_TRUNC({date_expr}, MONTH)) AS label, "
            f"MAX(`Subscriber_Count_CM`) AS value "
            f"FROM {full_table} "
            f"GROUP BY DATE_TRUNC({date_expr}, MONTH) "
            f"ORDER BY DATE_TRUNC({date_expr}, MONTH) ASC LIMIT 24"
        )
    else:
        trend_sql = current_sql

    return {
        "current_period": current_sql,
        "previous_period": previous_sql,
        "by_dimensions": dimensions_sql,
        "trend": trend_sql,
        "metric_type": "snapshot",
        "chart_rows_key": "by_dimensions" if asks_breakdown and preferred_dimension else "current_period",
    }


class DataAgent(BaseAgent):
    agent_id = "data"
    label = "Data"

    async def _execute(self, context: dict) -> dict:
        query = context.get("query", "")
        metadata = context.get("metadata", {})
        tables = metadata.get("tables", {})
        if not tables:
            context["data"] = {"source": "bigquery", "results": {}, "error": "No BigQuery tables were discovered."}
            return context

        schema_text = _schema_text(metadata)
        context["schema_text"] = schema_text

        # Deterministic path for the known subscriber snapshot metric. This is
        # deliberately ahead of Gemini so the same metric cannot be aggregated
        # differently for the KPI and chart.
        subscriber_plan = _subscriber_queries(query, metadata)
        if subscriber_plan:
            sql_queries = {
                k: v for k, v in subscriber_plan.items()
                if k in {"current_period", "previous_period", "by_dimensions", "trend"}
            }
            context["metric_semantics"] = "snapshot"
            context["chart_rows_key"] = subscriber_plan["chart_rows_key"]
        else:
            sql_queries = {}
            try:
                vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
                model = GenerativeModel(model_name=settings.VERTEX_AI_MODEL)
                response = await model.generate_content_async(
                    SQL_GEN_PROMPT.format(schema=schema_text, query=query),
                    generation_config=GenerationConfig(temperature=0.1, max_output_tokens=2048),
                )
                raw = response.text.strip().replace("```json", "").replace("```", "").strip()
                sql_queries = json.loads(raw)
                if not isinstance(sql_queries, dict):
                    raise ValueError("SQL generator returned a non-object response")
            except Exception as exc:
                logger.error("SQL generation failed", error=str(exc)[:160])
                context["data"] = {"source": "bigquery", "results": {}, "error": str(exc)}
                return context

        results = {}
        for key in ("current_period", "previous_period", "by_dimensions", "trend"):
            sql = sql_queries.get(key)
            if not isinstance(sql, str) or not sql.strip():
                continue
            sql = sql.strip().replace("```sql", "").replace("```", "").strip()
            try:
                rows = await run_query(sql)
                results[key] = {"rows": rows, "sql": sql, "row_count": len(rows)}
            except Exception as exc:
                logger.error("BigQuery query failed", query_type=key, error=str(exc)[:160])
                results[key] = {"rows": [], "sql": sql, "row_count": 0, "error": str(exc)}

        chart_key = context.get("chart_rows_key", "by_dimensions")
        chart_rows = results.get(chart_key, {}).get("rows", [])
        if not chart_rows:
            chart_key = "trend" if results.get("trend", {}).get("rows") else "current_period"
            chart_rows = results.get(chart_key, {}).get("rows", [])

        context["current_data"] = results.get("current_period", {}).get("rows", [])
        context["previous_data"] = results.get("previous_period", {}).get("rows", [])
        context["dimensions_data"] = results.get("by_dimensions", {}).get("rows", [])
        context["trend_data"] = results.get("trend", {}).get("rows", [])
        context["chart_data"] = chart_rows
        context["data"] = {
            "source": "bigquery",
            "results": results,
            "sql_queries": sql_queries,
            "rows": context["current_data"],
            "sql": sql_queries.get("current_period", ""),
            "row_count": len(context["current_data"]),
            "chart_rows_key": chart_key,
        }
        logger.info(
            "Data agent complete",
            current_rows=len(context["current_data"]),
            dimension_rows=len(context["dimensions_data"]),
            trend_rows=len(context["trend_data"]),
            chart_source=chart_key,
        )
        return context
