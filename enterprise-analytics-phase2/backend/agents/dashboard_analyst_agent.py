"""
Dashboard Analyst Agent — auto-generates a persona-driven dashboard.

For each persona it:
1. Reads the persona's dashboard_layers config
2. Builds targeted SQL queries for each chart
3. Executes them against BigQuery in parallel
4. Selects the best chart type for each result
5. Generates a Story Agent narrative
6. Returns a complete DashboardResponse
"""
import asyncio
import json
import re
import time
import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from services.persona_service import get_persona, get_dashboard_config
from services.bigquery_service import run_query
from services.chart_selector import select_chart_type
from agents.story_agent import StoryAgent
from config import settings

logger = structlog.get_logger()












# ── SQL generation prompt ──────────────────────────────────────────────────
DASHBOARD_SQL_PROMPT = """You are a strict BigQuery Standard SQL expert building a persona dashboard.

PERSONA: {persona_name}
PERSONA FOCUS: {focus}

CHART NEEDED: {chart_title}
REQUESTED CHART TYPE: {chart_type}
REQUESTED DIMENSION: {dimension}
REQUESTED METRIC: {metric}
DATE PERIOD: {period}

AVAILABLE SCHEMA:
{schema}

STRICT SCHEMA RULES — MUST FOLLOW:

1. Use ONLY exact table names and exact column names that appear in AVAILABLE SCHEMA.

2. NEVER invent, guess, rename, or assume a column.

3. If the requested dimension "{dimension}" does not exist exactly in the schema:
   - choose the closest relevant existing dimension from AVAILABLE SCHEMA.
   - do NOT use "{dimension}" if it does not exist.

4. If the requested metric "{metric}" does not exist exactly in the schema:
   - choose the closest relevant numeric metric from AVAILABLE SCHEMA.
   - do NOT invent a replacement.

5. Never use generic assumed columns such as:
   - title
   - created_at
   - updated_at
   - Channel_Segment
   unless they explicitly exist in AVAILABLE SCHEMA.

6. Use the exact table name shown after "Table:" in AVAILABLE SCHEMA.

7. BigQuery Standard SQL only.

DATE AND TIME RULES:

8. Do not compare TIMESTAMP directly with DATE.

9. If filtering a TIMESTAMP column by a date period, convert it explicitly using:
   DATE(`timestamp_column`)

10. If filtering a DATE column, compare DATE with DATE.

11. Only apply a date filter when an actual date, datetime, or timestamp column exists in AVAILABLE SCHEMA.

CHART RULES:

12. Return data suitable for the requested chart type.

13. For bar, donut, or heatmap charts:
    - use an existing dimension column for grouping
    - aggregate an existing numeric metric
    - GROUP BY the exact selected dimension
    - ORDER BY the aggregated metric DESC
    - LIMIT 12

14. For line or trend charts:
    - use an existing DATE, DATETIME, or TIMESTAMP column
    - aggregate an existing numeric metric
    - order chronologically ASC
    - LIMIT 12

15. For waterfall charts:
    - only use INFLOW and OUTFLOW columns if they actually exist.
    - otherwise use existing relevant numeric columns and return valid comparable data.

16. Do not use SELECT *.

17. Every column referenced in SELECT, WHERE, GROUP BY, ORDER BY, HAVING, or JOIN must exist in AVAILABLE SCHEMA.

18. Before returning SQL, verify internally that every referenced table and column exists in AVAILABLE SCHEMA.

Return ONLY one valid BigQuery Standard SQL query.
No explanation.
No markdown.
No backticks around the entire SQL.
"""












class DashboardAnalystAgent:
    """Builds a complete persona-driven dashboard from BigQuery data."""

    def __init__(self):
        self.model = None

    def _init_model(self):
        if not self.model:
            vertexai.init(
                project=settings.GCP_PROJECT_ID,
                location=settings.GCP_LOCATION
            )
            self.model = GenerativeModel(model_name=settings.VERTEX_AI_MODEL)

    async def generate_sql(self, chart_config: dict, schema: str,
                            persona: dict, period: str) -> str:
        """Generate SQL, using deterministic SQL for known snapshot metrics."""
        metric = chart_config.get("metric", "")
        dimension = chart_config.get("dimension", "")
        if metric == "Subscriber_Count_CM" and "Subscriber_Count_CM" in schema:
            deterministic = _build_subscriber_chart_sql(
                schema=schema, dimension=dimension, period=period, chart_type=chart_config.get("type", "bar")
            )
            if deterministic:
                return deterministic

        self._init_model()
        focus = ", ".join(persona.get("focus", []))
        prompt = DASHBOARD_SQL_PROMPT.format(
            persona_name=persona.get("name", "Analyst"),
            focus=focus,
            chart_title=chart_config.get("title", ""),
            chart_type=chart_config.get("type", "bar"),
            dimension=dimension or "Channel",
            metric=metric or "Subscriber_Count_CM",
            period=period,
            schema=schema,
        )
        try:
            resp = await self.model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(temperature=0.1, max_output_tokens=512),
            )
            return resp.text.strip().replace("```sql", "").replace("```", "").strip()
        except Exception as exc:
            logger.warning("SQL gen failed for chart", title=chart_config.get("title"), error=str(exc))
            return ""

    async def build_chart(self, chart_config: dict, schema: str,
                           persona: dict, period: str) -> dict:
        """Build one chart: generate SQL → execute BQ → select chart type."""
        sql = await self.generate_sql(chart_config, schema, persona, period)
        if not sql:
            return {"title": chart_config["title"], "error": "SQL generation failed",
                    "type": chart_config.get("type", "bar"), "data": []}
        try:
            rows = await run_query(sql)
            # Select best chart type based on query + data
            final_type = select_chart_type(
                query=chart_config.get("title", ""),
                rows=rows,
                requested_type=chart_config.get("type"),
            )
            return {
                "title": chart_config["title"],
                "type": final_type,
                "sql": sql,
                "rows": rows,
                "row_count": len(rows),
                "data": _rows_to_chart_data(rows, final_type),
            }
        except Exception as e:
            logger.warning("BQ chart query failed", title=chart_config.get("title"), error=str(e))
            return {"title": chart_config["title"], "error": str(e),
                    "type": chart_config.get("type", "bar"), "data": []}

    async def build_kpi_scoreboard(self, persona: dict, schema: str,
                                    period: str) -> list:
        """Build KPI scoreboard with schema-aware aggregations."""
        results = []
        for kpi in persona.get("default_kpis", []):
            hint = kpi.get("column_hint", "")
            col = _find_column(schema, hint)
            if not col:
                results.append({
                    "label": kpi.get("label", "KPI"),
                    "value": "N/A",
                    "change": "No data",
                    "trend": "neutral",
                    "format": kpi.get("format", "number"),
                })
                continue

            # Text dimensions need a ranking query, not numeric aggregation.
            if _column_type(schema, col) == "STRING":
                sql = _build_text_kpi_sql(col, kpi.get("label", col), period, schema)
                if not sql:
                    results.append({
                        "label": kpi.get("label", col),
                        "value": "N/A",
                        "change": "No ranking metric available",
                        "trend": "neutral",
                        "format": kpi.get("format", "text"),
                    })
                    continue
                try:
                    rows = await run_query(sql)
                    value = next(iter(rows[0].values())) if rows else None
                    results.append({
                        "label": kpi.get("label", col),
                        "value": str(value) if value is not None else "N/A",
                        "change": "Top result",
                        "trend": "neutral",
                        "format": kpi.get("format", "text"),
                    })
                except Exception as exc:
                    logger.warning("Text KPI query failed", label=kpi.get("label"), error=str(exc)[:120])
                    results.append({"label": kpi.get("label", col), "value": "N/A", "change": "—", "trend": "neutral"})
                continue

            sql = _build_kpi_sql(col, period, schema)
            if not sql:
                results.append({"label": kpi.get("label", col), "value": "N/A", "change": "—", "trend": "neutral"})
                continue

            try:
                rows = await run_query(sql)
                if not rows:
                    raise ValueError("No KPI data returned")
                val = next(iter(rows[0].values()))

                prev_sql = _build_prev_kpi_sql(col, period, schema)
                prev_rows = await run_query(prev_sql) if prev_sql else []
                prev_val = next(iter(prev_rows[0].values())) if prev_rows else None
                change, trend = _calc_variance(val, prev_val)

                item = {
                    "label": kpi.get("label", col),
                    "value": _format_val(val, kpi.get("format", "number")),
                    "change": change,
                    "trend": trend,
                    "format": kpi.get("format", "number"),
                }
                try:
                    item["raw_value"] = float(val)
                except (TypeError, ValueError):
                    pass
                results.append(item)
            except Exception as exc:
                logger.warning("KPI query failed", label=kpi.get("label"), error=str(exc)[:120])
                results.append({"label": kpi.get("label", col), "value": "N/A", "change": "—", "trend": "neutral"})
        return results

    async def run(self, persona_id: str, schema: str,
                  period: str = "latest") -> dict:
        """
        Main entry: builds the full persona dashboard.
        Returns DashboardResponse dict.
        """
        start = time.monotonic()
        persona = get_persona(persona_id)
        dash_config = get_dashboard_config(persona_id)
        layers = dash_config.get("dashboard_layers", [])

        logger.info("Building persona dashboard",
                    persona=persona_id, layers=len(layers))

        # 1. Build KPI scoreboard
        kpis_task = asyncio.create_task(
            self.build_kpi_scoreboard(persona, schema, period)
        )

        # 2. Build all charts in parallel across all layers
        all_chart_tasks = []
        chart_meta = []   # track which layer each chart belongs to
        for layer in layers:
            for chart_cfg in layer.get("charts", []):
                task = asyncio.create_task(
                    self.build_chart(chart_cfg, schema, persona, period)
                )
                all_chart_tasks.append(task)
                chart_meta.append({
                    "layer_id": layer["id"],
                    "layer_label": layer["label"],
                    "layer_icon": layer.get("icon", "📊"),
                })

        # Wait for all in parallel
        kpi_results, *chart_results = await asyncio.gather(
            kpis_task, *all_chart_tasks
        )

        # 3. Organise charts back into layers
        built_layers = {}
        for meta, result in zip(chart_meta, chart_results):
            lid = meta["layer_id"]
            if lid not in built_layers:
                built_layers[lid] = {
                    "id": lid,
                    "label": meta["layer_label"],
                    "icon": meta["layer_icon"],
                    "charts": [],
                }
            built_layers[lid]["charts"].append(result)

        # 4. Generate story narrative
        story = await StoryAgent().generate(
            persona=persona,
            kpis=kpi_results,
            charts=chart_results,
            period=period,
        )

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info("Dashboard built",
                    persona=persona_id,
                    kpis=len(kpi_results),
                    charts=len(chart_results),
                    layers=len(built_layers),
                    duration_ms=duration_ms)

        return {
            "persona_id": persona_id,
            "persona_name": persona.get("name"),
            "persona_icon": persona.get("icon"),
            "tagline": persona.get("tagline"),
            "period": period,
            "kpis": kpi_results,
            "layers": list(built_layers.values()),
            "story": story,
            "suggested_questions": persona.get("suggested_questions", []),
            "generated_at": time.time(),
            "duration_ms": duration_ms,
        }


# ── Helper functions ──────────────────────────────────────────────────────

def _schema_table(schema: str) -> str:
    for line in schema.split("\n"):
        if line.strip().startswith("Table:"):
            return line.split("Table:", 1)[1].strip()
    return ""


def _parse_schema_columns(schema: str) -> tuple[set[str], set[str], set[str]]:
    numeric, dates, strings = set(), set(), set()
    for line in schema.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Numeric (metrics):"):
            try:
                values = json.loads(stripped.split(":", 1)[1].replace("'", '"'))
                numeric.update(values)
            except Exception:
                numeric.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stripped.split(":", 1)[1]))
        elif stripped.startswith("Date columns:"):
            try:
                values = json.loads(stripped.split(":", 1)[1].replace("'", '"'))
                dates.update(values)
            except Exception:
                dates.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stripped.split(":", 1)[1]))
        elif stripped.startswith("String (dimensions):"):
            try:
                values = json.loads(stripped.split(":", 1)[1].replace("'", '"'))
                strings.update(values)
            except Exception:
                strings.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stripped.split(":", 1)[1]))
    return numeric, dates, strings


def _find_column(schema: str, hint: str) -> str:
    if not hint or not schema:
        return ""
    numeric, dates, strings = _parse_schema_columns(schema)
    all_columns = numeric | dates | strings
    if hint in all_columns:
        return hint
    hint_lower = hint.lower()
    exact_case_insensitive = next((col for col in all_columns if col.lower() == hint_lower), None)
    if exact_case_insensitive:
        return exact_case_insensitive
    return next((col for col in all_columns if hint_lower in col.lower()), "")


def _column_type(schema: str, column: str) -> str:
    numeric, dates, strings = _parse_schema_columns(schema)
    if column in numeric:
        return "NUMERIC"
    if column in dates:
        return "DATE"
    if column in strings:
        return "STRING"
    return ""


def _period_bounds_sql(period: str, date_expr: str) -> str:
    match = re.search(r"\bQ([1-4])\s*(20\d{2})\b", period or "", re.I)
    if match:
        q, year = int(match.group(1)), int(match.group(2))
        start_month = (q - 1) * 3 + 1
        end_year = year + (1 if q == 4 else 0)
        end_month = 1 if q == 4 else start_month + 3
        return f"WHERE {date_expr} >= DATE '{year:04d}-{start_month:02d}-01' AND {date_expr} < DATE '{end_year:04d}-{end_month:02d}-01'"
    if period == "YTD":
        return f"WHERE {date_expr} >= DATE(EXTRACT(YEAR FROM (SELECT MAX({date_expr}) FROM __TABLE_PLACEHOLDER__)) || '-01-01')"
    return ""


def _build_subscriber_chart_sql(schema: str, dimension: str, period: str, chart_type: str) -> str:
    table = _schema_table(schema)
    if not table or "Subscriber_Count_CM" not in _parse_schema_columns(schema)[0]:
        return ""
    numeric, dates, strings = _parse_schema_columns(schema)
    if dimension and dimension not in strings:
        dimension = ""
    date_column = next(iter(dates), "")
    date_expr = f"DATE(`{date_column}`)" if date_column else ""
    full_table = f"`{table}`"

    period_clause = ""
    if date_column and period and period != "latest":
        qmatch = re.search(r"\bQ([1-4])\s*(20\d{2})\b", period, re.I)
        ymatch = re.search(r"\b(20\d{2})\b", period)
        if qmatch:
            q, year = int(qmatch.group(1)), int(qmatch.group(2))
            sm = (q - 1) * 3 + 1
            ey, em = (year + 1, 1) if q == 4 else (year, sm + 3)
            period_clause = f"WHERE {date_expr} >= DATE '{year:04d}-{sm:02d}-01' AND {date_expr} < DATE '{ey:04d}-{em:02d}-01'"
        elif ymatch and period == "YTD":
            period_clause = f"WHERE {date_expr} >= DATE_TRUNC(DATE((SELECT MAX({date_expr}) FROM {full_table})), YEAR)"
    if dimension:
        return (
            f"SELECT `{dimension}` AS label, SUM(`Subscriber_Count_CM`) AS value "
            f"FROM {full_table} {period_clause} "
            f"GROUP BY `{dimension}` ORDER BY value DESC LIMIT 12"
        )

    if date_column and chart_type in {"line", "area"}:
        return (
            f"SELECT FORMAT_DATE('%Y-%m', DATE_TRUNC({date_expr}, MONTH)) AS label, "
            f"MAX(`Subscriber_Count_CM`) AS value FROM {full_table} "
            f"GROUP BY DATE_TRUNC({date_expr}, MONTH) ORDER BY DATE_TRUNC({date_expr}, MONTH) ASC LIMIT 12"
        )

    if date_column:
        latest_filter = f"WHERE {date_expr} = (SELECT MAX({date_expr}) FROM {full_table})"
        return f"SELECT 'Subscriber Count' AS label, MAX(`Subscriber_Count_CM`) AS value FROM {full_table} {latest_filter}"
    return f"SELECT 'Subscriber Count' AS label, MAX(`Subscriber_Count_CM`) AS value FROM {full_table}"


def _build_text_kpi_sql(col: str, label: str, period: str, schema: str) -> str:
    table = _schema_table(schema)
    if not table or _column_type(schema, col) != "STRING":
        return ""
    numeric, dates, strings = _parse_schema_columns(schema)
    full_table = f"`{table}`"
    date_column = next(iter(dates), "")
    date_expr = f"DATE(`{date_column}`)" if date_column else ""
    where = ""
    if date_column and period and period != "latest":
        qmatch = re.search(r"\bQ([1-4])\s*(20\d{2})\b", period or "", re.I)
        ymatch = re.search(r"\b(20\d{2})\b", period or "")
        if qmatch:
            q, year = int(qmatch.group(1)), int(qmatch.group(2))
            sm = (q - 1) * 3 + 1
            ey, em = (year + 1, 1) if q == 4 else (year, sm + 3)
            where = f"WHERE {date_expr} >= DATE '{year:04d}-{sm:02d}-01' AND {date_expr} < DATE '{ey:04d}-{em:02d}-01'"
        elif ymatch and period != "YTD":
            year = int(ymatch.group(1))
            where = f"WHERE {date_expr} >= DATE '{year:04d}-01-01' AND {date_expr} < DATE '{year + 1:04d}-01-01'"
        elif period == "YTD":
            where = f"WHERE {date_expr} >= DATE_TRUNC(DATE((SELECT MAX({date_expr}) FROM {full_table})), YEAR)"
    elif date_column and period == "latest":
        where = f"WHERE {date_expr} = (SELECT MAX({date_expr}) FROM {full_table})"

    label_lower = (label or "").lower()
    if "channel" in label_lower and "INFLOW" in numeric and "Channel" in strings and col == "Channel":
        return f"SELECT `{col}` AS value FROM {full_table} {where} GROUP BY `{col}` ORDER BY SUM(`INFLOW`) DESC LIMIT 1"
    if "plan" in label_lower and "Price_Plan" in strings and col == "Price_Plan":
        metric = "Subscriber_Count_CM" if "Subscriber_Count_CM" in numeric else ("INFLOW" if "INFLOW" in numeric else None)
        if metric:
            aggregation = "MAX" if metric == "Subscriber_Count_CM" else "SUM"
            return f"SELECT `{col}` AS value FROM {full_table} {where} GROUP BY `{col}` ORDER BY {aggregation}(`{metric}`) DESC LIMIT 1"
    return f"SELECT `{col}` AS value FROM {full_table} {where} GROUP BY `{col}` ORDER BY COUNT(*) DESC LIMIT 1"


def _build_kpi_sql(col: str, period: str, schema: str) -> str:
    table = _schema_table(schema)
    if not table or _column_type(schema, col) == "STRING":
        return ""
    full_table = f"`{table}`"
    numeric, dates, _ = _parse_schema_columns(schema)
    date_column = next(iter(dates), "")
    date_expr = f"DATE(`{date_column}`)" if date_column else ""

    # Snapshot metrics must not be summed across denormalised rows.
    aggregation = "MAX" if col == "Subscriber_Count_CM" or col.endswith("_CM") else "SUM"
    where = ""
    if date_column:
        if period == "latest":
            where = f"WHERE {date_expr} = (SELECT MAX({date_expr}) FROM {full_table})"
        else:
            qmatch = re.search(r"\bQ([1-4])\s*(20\d{2})\b", period or "", re.I)
            ymatch = re.search(r"\b(20\d{2})\b", period or "")
            if qmatch:
                q, year = int(qmatch.group(1)), int(qmatch.group(2))
                sm = (q - 1) * 3 + 1
                ey, em = (year + 1, 1) if q == 4 else (year, sm + 3)
                where = f"WHERE {date_expr} >= DATE '{year:04d}-{sm:02d}-01' AND {date_expr} < DATE '{ey:04d}-{em:02d}-01'"
            elif period == "YTD":
                where = f"WHERE {date_expr} >= DATE_TRUNC(DATE((SELECT MAX({date_expr}) FROM {full_table})), YEAR)"
            elif ymatch:
                year = int(ymatch.group(1))
                where = f"WHERE {date_expr} >= DATE '{year:04d}-01-01' AND {date_expr} < DATE '{year + 1:04d}-01-01'"
    return f"SELECT {aggregation}(`{col}`) AS value FROM {full_table} {where}"


def _build_prev_kpi_sql(col: str, period: str, schema: str) -> str:
    table = _schema_table(schema)
    if not table or _column_type(schema, col) == "STRING":
        return ""
    full_table = f"`{table}`"
    _, dates, _ = _parse_schema_columns(schema)
    date_column = next(iter(dates), "")
    if not date_column:
        return ""
    date_expr = f"DATE(`{date_column}`)"
    aggregation = "MAX" if col == "Subscriber_Count_CM" or col.endswith("_CM") else "SUM"

    qmatch = re.search(r"\bQ([1-4])\s*(20\d{2})\b", period or "", re.I)
    ymatch = re.search(r"\b(20\d{2})\b", period or "")
    if qmatch:
        q, year = int(qmatch.group(1)), int(qmatch.group(2))
        prev_q = 4 if q == 1 else q - 1
        prev_year = year - 1 if q == 1 else year
        sm = (prev_q - 1) * 3 + 1
        em = 1 if prev_q == 4 else sm + 3
        ey = prev_year + 1 if prev_q == 4 else prev_year
        where = f"WHERE {date_expr} >= DATE '{prev_year:04d}-{sm:02d}-01' AND {date_expr} < DATE '{ey:04d}-{em:02d}-01'"
    elif period == "YTD":
        where = f"WHERE {date_expr} >= DATE_TRUNC(DATE_SUB(DATE((SELECT MAX({date_expr}) FROM {full_table})), INTERVAL 1 YEAR), YEAR) AND {date_expr} < DATE_TRUNC(DATE((SELECT MAX({date_expr}) FROM {full_table})), YEAR)"
    elif ymatch:
        year = int(ymatch.group(1)) - 1
        where = f"WHERE {date_expr} >= DATE '{year:04d}-01-01' AND {date_expr} < DATE '{year + 1:04d}-01-01'"
    else:
        where = f"WHERE {date_expr} = (SELECT MAX({date_expr}) FROM {full_table} WHERE {date_expr} < (SELECT MAX({date_expr}) FROM {full_table}))"
    return f"SELECT {aggregation}(`{col}`) AS value FROM {full_table} {where}"


def _extract_table(schema: str) -> str:
    return _schema_table(schema)


def _calc_variance(current, previous) -> tuple:
    """Calculate variance string and trend direction."""
    try:
        c = float(current or 0)
        p = float(previous or 0)
        if p == 0:
            return "N/A", "neutral"
        diff = c - p
        pct = (diff / p) * 100
        sign = "+" if diff >= 0 else ""
        trend = "up" if diff > 0 else ("down" if diff < 0 else "neutral")
        return f"{sign}{diff:,.0f} / {sign}{pct:.1f}%", trend
    except Exception:
        return "N/A", "neutral"


def _format_val(val, fmt: str) -> str:
    """Format a value for display based on format type."""
    try:
        v = float(val)
        if fmt == "number":
            return f"{v:,.0f}"
        elif fmt == "currency_eur":
            return f"€{v:,.2f}"
        elif fmt == "percent":
            return f"{v:.1f}%"
        elif fmt == "number_signed":
            return f"+{v:,.0f}" if v >= 0 else f"{v:,.0f}"
        return str(val)
    except Exception:
        return str(val)


def _rows_to_chart_data(rows: list, chart_type: str) -> list:
    """Convert rows using named label/value fields when available."""
    if not rows:
        return []
    data = []
    for row in rows[:12]:
        keys = list(row.keys())
        label_key = next((k for k in keys if k.lower() in {"label", "dimension", "period", "month", "date"}), None)
        numeric_keys = [k for k, v in row.items() if isinstance(v, (int, float))]
        value_key = "value" if "value" in row else (numeric_keys[0] if numeric_keys else None)
        if label_key and value_key:
            data.append({"label": str(row[label_key]), "value": _safe_float(row[value_key])})
        elif len(keys) >= 2:
            data.append({"label": str(row[keys[0]]), "value": _safe_float(row[keys[1]])})
        elif keys:
            data.append({"label": str(keys[0]), "value": _safe_float(row[keys[0]])})
    return data


def _safe_float(value) -> float:
    try:
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value).replace(",", "").replace("€", "").replace("%", "").strip())
    except (ValueError, TypeError, AttributeError):
        return 0.0
