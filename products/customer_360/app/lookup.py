"""Pure helpers for the Customer Lookup app (no Databricks or Streamlit imports, so they are unit-testable)."""

from __future__ import annotations

SCHEMA = "demo_redshift.customer_360"
FOOTER = "Data as of 2025-12-31 · certified customer_360 metrics"


def escape_dollars(text: str) -> str:
    """Streamlit renders paired $ as LaTeX, so escape them before st.markdown."""
    return text.replace("$", "\\$")


def money(value) -> str:
    return "—" if value is None else f"${float(value):,.2f}"


def search_query(term: str) -> tuple[str, dict[str, str]]:
    """Parameterized customer search by ID, name or email."""
    term = term.strip()
    literal = term.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    params = {"pattern": f"%{literal}%"}
    where = "lower(p.customer_name) LIKE :pattern OR lower(p.email) LIKE :pattern"
    if term.lstrip("#").isdigit():
        where = f"p.customer_id = CAST(:cid AS BIGINT) OR {where}"
        params["cid"] = term.lstrip("#")
    sql = (
        "SELECT p.customer_id, p.customer_name, p.email, p.phone, p.region, p.is_business, p.signup_date, "
        "p.first_order_date, p.last_order_date, p.completed_orders, p.net_ltv, p.gross_spend, p.aov, "
        "p.returned_orders, p.top_category, p.preferred_store, h.segment, h.recency_days, h.r_score, h.f_score, h.m_score, h.revenue_at_risk "
        f"FROM {SCHEMA}.customer_profile p JOIN {SCHEMA}.customer_health h USING (customer_id) "
        f"WHERE {where} ORDER BY p.customer_id LIMIT 25"
    )
    return sql, params


ORDERS_SQL = (
    "SELECT order_id, order_ts, channel, store, status, items, gross_amount, net_amount "
    f"FROM {SCHEMA}.order_facts WHERE customer_id = CAST(:cid AS BIGINT) ORDER BY order_ts DESC LIMIT 10"
)

PORTFOLIO_SQL = (
    "SELECT segment, MEASURE(customers) AS customers, MEASURE(revenue_at_risk) AS revenue_at_risk "
    f"FROM {SCHEMA}.customer_health_metrics GROUP BY segment ORDER BY customers DESC"
)
