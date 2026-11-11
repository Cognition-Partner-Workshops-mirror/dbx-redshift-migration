"""Generate the leadership Lakeview dashboard, with explicit snapshot filter scope."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
PREFIX = "demo_redshift.customer_360."
CURRENCY = {"type": "number-currency", "currencyCode": "USD", "abbreviation": "compact",
            "decimalPlaces": {"type": "max", "places": 2}}
NUMBER = {"type": "number", "decimalPlaces": {"type": "max", "places": 0}}
PERCENT = {"type": "number-percent", "decimalPlaces": {"type": "exact", "places": 1}}
FILTERS = ("fiscal_quarter", "sales_channel", "region")
datasets = []


def dataset(name, sql, filters=()):
    item = {"name": name, "displayName": name.replace("_", " ").title(),
            "queryLines": [sql + "\n"]}
    if filters:
        item["parameters"] = [
            {"keyword": f, "displayName": f.replace("_", " ").title(), "dataType": "STRING",
             "defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": "All"}]}}}
            for f in filters
        ]
    datasets.append(item)


def where(filters):
    return " AND ".join(f"(:{f} = 'All' OR {f} = :{f})" for f in filters)


def revenue(name, select, group=""):
    dataset(name, f"SELECT {select} FROM {PREFIX}revenue_metrics WHERE {where(FILTERS)} {group}", FILTERS)


def health(name, select, group=""):
    dataset(name, f"SELECT {select} FROM {PREFIX}customer_health_metrics "
            f"WHERE {where(('region',))} {group}", ("region",))


def field(name):
    return {"name": name, "expression": f"`{name}`"}


def widget(name, ds, fields, kind, encodings, title, description=""):
    return {"name": name, "queries": [{"name": "main_query", "query": {
        "datasetName": ds, "fields": [field(f) for f in fields], "disaggregated": True}}],
        "spec": {"version": 2 if kind in ("counter", "table") else 3,
                 "widgetType": kind, "encodings": encodings,
                 "frame": {"showTitle": True, "title": title,
                           "showDescription": bool(description), "description": description}}}


def position(w, x, y, width, height):
    return {"widget": w, "position": {"x": x, "y": y, "width": width, "height": height}}


def text(name, value, y):
    return position({"name": name, "multilineTextboxSpec": {"lines": [value]}}, 0, y, 12, 1)


def encoding(name, label, fmt=None):
    result = {"fieldName": name, "displayName": label}
    if fmt:
        result["format"] = fmt
    return result


def bar(name, ds, dim, measure, title, fmt=CURRENCY):
    return widget(name, ds, [dim, measure], "bar", {
        "x": {**encoding(measure, title, fmt), "scale": {"type": "quantitative"}},
        "y": {"fieldName": dim, "scale": {"type": "categorical"}}}, title)


def main():
    revenue("revenue_summary", "MEASURE(net_revenue) AS net_revenue, "
            "MEASURE(revenue_leakage) AS revenue_leakage, MEASURE(aov) AS aov, "
            "MEASURE(on_time_delivery_pct) / 100.0 AS on_time_delivery")
    revenue("monthly_revenue", "order_month, MEASURE(gross_revenue) AS gross_revenue, "
            "MEASURE(net_revenue) AS net_revenue", "GROUP BY ALL ORDER BY order_month")
    revenue("channel_revenue", "sales_channel, MEASURE(net_revenue) AS net_revenue",
            "GROUP BY ALL ORDER BY net_revenue DESC")
    revenue("region_revenue", "region, MEASURE(net_revenue) AS net_revenue",
            "GROUP BY ALL ORDER BY net_revenue DESC")
    health("health_summary", "MEASURE(active_customers) AS active_customers, "
           "MEASURE(revenue_at_risk) AS revenue_at_risk")
    health("health_mix", "health_segment, MEASURE(customers) AS customers",
           "GROUP BY ALL ORDER BY customers DESC")
    health("regional_risk", "region, MEASURE(revenue_at_risk) AS revenue_at_risk",
           "GROUP BY ALL ORDER BY revenue_at_risk DESC")
    dataset("legacy_comparison", f"SELECT kpi, legacy_value, certified_value, difference, explanation "
            f"FROM {PREFIX}legacy_vs_certified ORDER BY kpi")
    dataset("normalized_comparison", "WITH base AS (SELECT kpi, legacy_value, certified_value "
            f"FROM {PREFIX}legacy_vs_certified WHERE kpi IN ('total_revenue', 'aov', 'avg_customer_ltv')) "
            "SELECT kpi, 'Legacy' AS series, 1.0 AS relative_value FROM base "
            "UNION ALL SELECT kpi, 'Certified' AS series, "
            "TRY_DIVIDE(certified_value, legacy_value) AS relative_value FROM base ORDER BY kpi, series")
    for f in FILTERS:
        dataset(f"options_{f}", f"SELECT 'All' AS {f} UNION ALL SELECT DISTINCT {f} "
                f"FROM {PREFIX}revenue_metrics GROUP BY ALL ORDER BY {f}")

    overview = [text("executive_title", "## Customer Health & Revenue", 0),
                text("executive_subtitle", "**As of 31 Dec 2025** · Net revenue recognizes complete orders only. Gross includes cancelled and returned orders.", 1),
                text("filter_scope", "Quarter & channel filter revenue. Region also filters customer health. Health is a lifetime snapshot; legacy comparisons stay all-company.", 2)]
    counters = [
        ("net_revenue", "revenue_summary", "Net revenue", CURRENCY, "Complete orders only"),
        ("revenue_leakage", "revenue_summary", "Revenue leakage", CURRENCY, "Cancelled + returned spend"),
        ("aov", "revenue_summary", "True AOV", CURRENCY, "Net revenue / completed orders"),
        ("active_customers", "health_summary", "Active customers", NUMBER, "Completed purchase within 90 days · snapshot"),
        ("revenue_at_risk", "health_summary", "Revenue at risk", CURRENCY, "At-risk customer lifetime value · snapshot"),
        ("on_time_delivery", "revenue_summary", "On-time delivery", PERCENT, "Delivered within 96h · undelivered excluded"),
    ]
    for i, (col, ds, title, fmt, desc) in enumerate(counters):
        overview.append(position(widget("kpi_" + col, ds, [col], "counter",
                                        {"value": encoding(col, title, fmt)}, title, desc),
                                 (i % 3) * 4, 3 + (i // 3) * 3, 4, 3))
    line = widget("monthly_trend", "monthly_revenue", ["order_month", "gross_revenue", "net_revenue"], "line", {
        "x": {"fieldName": "order_month", "scale": {"type": "temporal"}},
        "y": {"scale": {"type": "quantitative"}, "fields": [
            encoding("gross_revenue", "Gross revenue", CURRENCY), encoding("net_revenue", "Net revenue", CURRENCY)]}},
        "Revenue recognition gap by month (USD)", "Gross spend vs certified net revenue")
    overview += [position(line, 0, 9, 12, 5),
                 position(bar("by_channel", "channel_revenue", "sales_channel", "net_revenue", "Net revenue by channel"), 0, 14, 6, 5),
                 position(bar("by_region", "region_revenue", "region", "net_revenue", "Net revenue by region"), 6, 14, 6, 5),
                 position(bar("segment_mix", "health_mix", "health_segment", "customers", "Customer health mix · snapshot", NUMBER), 0, 19, 6, 5),
                 position(bar("risk_by_region", "regional_risk", "region", "revenue_at_risk", "Revenue at risk by region · snapshot"), 6, 19, 6, 5)]
    columns = [encoding("kpi", "KPI"), encoding("legacy_value", "Legacy"),
               encoding("certified_value", "Certified"), encoding("difference", "Certified − legacy"),
               encoding("explanation", "Why it changed")]
    comparison = [text("comparison_title", "## Legacy vs certified", 0),
                  text("comparison_scope", "All-company reconciliation · filters do not apply. Monetary KPIs are USD; return rate is a fraction. Q1 isolates the calendar fix at equal gross scope.", 1),
                  position(widget("comparison_table", "legacy_comparison", [c["fieldName"] for c in columns],
                                  "table", {"columns": columns}, "Five KPI corrections", "Difference = certified minus legacy"), 0, 2, 12, 6)]
    chart = widget("comparison_bars", "normalized_comparison", ["kpi", "series", "relative_value"], "bar", {
        "x": {"fieldName": "kpi", "scale": {"type": "categorical"}},
        "y": {**encoding("relative_value", "Relative to legacy", PERCENT), "scale": {"type": "quantitative"}},
        "color": {"fieldName": "series", "scale": {"type": "categorical", "mappings": [
            {"value": "Legacy", "color": "#94A3B8"}, {"value": "Certified", "color": "#087E8B"}]}}},
        "Revenue, AOV and LTV · legacy = 100%", "Normalized for comparison across different dollar scales")
    chart["spec"]["mark"] = {"layout": "group"}
    comparison.append(position(chart, 0, 8, 12, 6))

    filters = []
    for i, f in enumerate(FILTERS):
        queries = [{"name": "options", "query": {"datasetName": f"options_{f}", "fields": [field(f)], "disaggregated": False}}]
        bindings = [{"fieldName": f, "queryName": "options"}]
        for ds in datasets:
            if any(p["keyword"] == f for p in ds.get("parameters", [])):
                queries.append({"name": ds["name"], "query": {"datasetName": ds["name"],
                                "parameters": [{"name": f, "keyword": f}], "disaggregated": False}})
                bindings.append({"parameterName": f, "queryName": ds["name"]})
        filters.append(position({"name": "filter_" + f, "queries": queries,
                                 "spec": {"version": 2, "widgetType": "filter-single-select",
                                          "encodings": {"fields": bindings},
                                          "selection": {"defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": "All"}]}}},
                                          "frame": {"showTitle": True, "title": f.replace("_", " ").title()}}}, i * 4, 0, 4, 2))
    pages = [{"name": name, "displayName": label, "pageType": kind,
              "layoutVersion": "GRID_V1", "layout": layout} for name, label, kind, layout in [
                  ("executive_overview", "Executive overview", "PAGE_TYPE_CANVAS", overview),
                  ("legacy_vs_certified", "Legacy vs certified", "PAGE_TYPE_CANVAS", comparison),
                  ("global_filters", "Global filters", "PAGE_TYPE_GLOBAL_FILTERS", filters)]]
    theme = {"canvasBackgroundColor": {"light": "#F4F7FA", "dark": "#14212C"},
             "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#1C2D3B"},
             "widgetBorderColor": {"light": "#FFFFFF", "dark": "#1C2D3B"},
             "fontColor": {"light": "#18344B", "dark": "#E7F0F7"},
             "selectionColor": {"light": "#087E8B", "dark": "#61CAD4"},
             "visualizationColors": ["#94A3B8", "#087E8B", "#D97732", "#496AB0", "#A15B94", "#527C68"],
             "widgetHeaderAlignment": "LEFT"}
    output = ROOT / "dashboards/customer_health_revenue.lvdash.json"
    output.write_text(json.dumps({"datasets": datasets, "pages": pages, "uiSettings": {"theme": theme}}, indent=2) + "\n")


if __name__ == "__main__":
    main()
