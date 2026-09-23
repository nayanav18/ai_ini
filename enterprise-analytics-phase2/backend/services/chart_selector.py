"""
chart_selector.py — Auto-selects best chart type + converts BQ rows to chart data.
Copy to: backend/services/chart_selector.py
"""
import re
from typing import Optional, List


# ── Keyword → chart type mapping ──────────────────────────────────────────
KEYWORD_MAP = {
    "donut": [
        "share", "mix", "split", "composition", "percentage",
        "breakdown", "proportion", "distribution", "market share",
    ],
    "waterfall": [
        "inflow", "outflow", "bridge", "net movement",
        "net change", "waterfall", "gain and loss", "movement",
    ],
    "funnel": [
        "funnel", "conversion", "acquisition funnel",
        "journey", "stages", "pipeline", "drop-off",
    ],
    "stacked_bar": [
        "stacked", "cumulative", "composition over time",
        "mix change", "over time by", "breakdown over",
    ],
    "grouped_bar": [
        "compare", "comparison", "versus", " vs ", "side by side",
        "benchmark",
    ],
    "heatmap": [
        "heatmap", "heat map", "matrix", "cross",
        "by channel and", "by segment and", "two dimensions",
    ],
    "scatter": [
        "scatter", "anomaly", "outlier", "correlation",
        "relationship between", "anomaly detection",
    ],
    "area": [
        "area chart", "cumulative growth", "stacked area",
    ],
    "line": [
        "trend", "over time", "monthly", "weekly", "daily",
        "growth trajectory", "6 months", "12 months", "history",
        "evolution", "trajectory", "time series", "month by month",
    ],
    "bar": [
        "top", "highest", "lowest", "ranking", "ranked",
        "by channel", "by segment", "by plan", "breakdown",
        "which channel", "which plan", "which segment",
        "bar chart", "bar graph",
    ],
}

# ── Descriptions ──────────────────────────────────────────────────────────
CHART_DESCRIPTIONS = {
    "line":        "Line chart — auto-selected: time series data",
    "bar":         "Bar chart — auto-selected: category comparison",
    "donut":       "Donut chart — auto-selected: share/mix/proportion",
    "pie":         "Pie chart — auto-selected: part-to-whole",
    "waterfall":   "Waterfall — auto-selected: INFLOW/OUTFLOW bridge",
    "funnel":      "Funnel — auto-selected: conversion/stages",
    "stacked_bar": "Stacked bar — auto-selected: composition over time",
    "grouped_bar": "Grouped bar — auto-selected: multi-series comparison",
    "heatmap":     "Heatmap — auto-selected: cross-dimensional matrix",
    "scatter":     "Scatter — auto-selected: anomaly/correlation",
    "area":        "Area chart — auto-selected: cumulative trend",
    "kpi_card":    "KPI card — single metric summary",
}


# ── Data shape helpers ────────────────────────────────────────────────────

def _has_date_column(rows: list) -> bool:
    if not rows:
        return False
    date_kw = {"date", "month", "period", "week", "year", "time", "day"}
    return any(
        any(dk in k.lower() for dk in date_kw)
        for k in rows[0].keys()
    )


def _category_count(rows: list) -> int:
    return len(rows)


def _has_inflow_outflow(rows: list) -> bool:
    if not rows:
        return False
    combined = " ".join(
        f"{k} {v}" for row in rows[:5] for k, v in row.items()
    ).lower()
    return "inflow" in combined or "outflow" in combined


def _has_multiple_numeric_series(rows: list) -> bool:
    if not rows:
        return False
    num_cols = [k for k, v in rows[0].items() if isinstance(v, (int, float))]
    return len(num_cols) >= 2


def _has_two_categorical_dimensions(rows: list) -> bool:
    if not rows or len(rows) < 4:
        return False
    str_cols = [k for k, v in rows[0].items()
                if isinstance(v, str) and "date" not in k.lower()]
    num_cols = [k for k, v in rows[0].items() if isinstance(v, (int, float))]
    return len(str_cols) >= 2 and len(num_cols) >= 1


# ── Main selector ─────────────────────────────────────────────────────────

def select_chart_type(
    query: str,
    rows: list,
    requested_type: Optional[str] = None,
) -> str:
    """
    Select the best chart type for a given query + BQ result.

    Priority:
      1. Keyword matching on query/title
      2. Data shape heuristics
      3. Requested type from config
      4. Safe default: bar
    """
    q = query.lower()

    # ── Priority 1: Keywords ───────────────────────────────────────────
    for chart_type, keywords in KEYWORD_MAP.items():
        if any(kw in q for kw in keywords):
            # Corrections
            if chart_type == "donut" and _category_count(rows) > 6:
                return "bar"
            if chart_type == "line" and not _has_date_column(rows):
                return "bar"
            return chart_type

    # ── Priority 2: Data shape ─────────────────────────────────────────
    if _has_inflow_outflow(rows):
        return "waterfall"

    if _has_date_column(rows) and _category_count(rows) >= 4:
        return "line"

    if _has_two_categorical_dimensions(rows):
        return "heatmap"

    if _has_multiple_numeric_series(rows) and not _has_date_column(rows):
        return "grouped_bar"

    if not _has_date_column(rows) and 2 <= _category_count(rows) <= 5:
        return "donut"

    if _category_count(rows) > 5:
        return "bar"

    if _category_count(rows) == 1:
        return "kpi_card"

    # ── Priority 3: Requested type ─────────────────────────────────────
    VALID = {
        "line", "bar", "donut", "pie", "waterfall", "funnel",
        "stacked_bar", "grouped_bar", "heatmap", "scatter", "area"
    }
    if requested_type and requested_type in VALID:
        return requested_type

    return "bar"


def get_chart_description(chart_type: str) -> str:
    """Return human-readable reason for chart type selection."""
    return CHART_DESCRIPTIONS.get(chart_type, f"{chart_type} chart")


def rows_to_chart_data(rows: list, chart_type: str) -> List[dict]:
    """
    Convert BQ rows to standard chart data format.

    Standard output:  [{"label": "...", "value": 123.0}, ...]
    Multi-series:     [{"label": "...", "series": {"col1": 1.0, "col2": 2.0}}, ...]
    Peak/min markers: added for line and area charts
    """
    if not rows:
        return []

    data = []
    for row in rows[:15]:          # cap at 15 data points
        vals = list(row.values())
        keys = list(row.keys())

        if len(vals) == 0:
            continue
        elif len(vals) == 1:
            data.append({
                "label": str(keys[0]),
                "value": _safe_float(vals[0]),
            })
        elif len(vals) == 2:
            data.append({
                "label": str(vals[0]),
                "value": _safe_float(vals[1]),
            })
        elif len(vals) >= 3 and chart_type in ("stacked_bar", "grouped_bar"):
            # Multi-series: first col = label, rest = series values
            entry = {"label": str(vals[0]), "series": {}}
            for k, v in zip(keys[1:], vals[1:]):
                entry["series"][k] = _safe_float(v)
            data.append(entry)
        else:
            # Default: first col = label, last numeric = value
            label = str(vals[0])
            value = _safe_float(vals[-1])
            data.append({"label": label, "value": value})

    # ── Mark peak and min for line/area charts ─────────────────────────
    if chart_type in ("line", "area") and data:
        values = [d.get("value", 0) for d in data if "value" in d]
        if values:
            max_v = max(values)
            min_v = min(values)
            for d in data:
                v = d.get("value", 0)
                d["is_peak"] = (v == max_v)
                d["is_min"]  = (v == min_v)

    return data


def _safe_float(v) -> float:
    """Safely convert any value to float."""
    try:
        if isinstance(v, (int, float)):
            return float(v)
        return float(str(v).replace(",", "").replace("€", "").replace("%", "").strip())
    except (ValueError, TypeError, AttributeError):
        return 0.0
