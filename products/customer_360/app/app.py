import os

import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem
from lookup import FOOTER, ORDERS_SQL, PORTFOLIO_SQL, escape_dollars, money, search_query

st.set_page_config(page_title="Customer Lookup", layout="wide")
WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "")


@st.cache_resource
def client() -> WorkspaceClient:
    return WorkspaceClient()


def run_sql(sql: str, params: dict[str, str] | None = None) -> pd.DataFrame:
    resp = client().statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=sql,
        parameters=[StatementParameterListItem(name=k, value=v) for k, v in (params or {}).items()],
        wait_timeout="50s",
    )
    if resp.status.state.value != "SUCCEEDED":
        raise RuntimeError(resp.status.error.message if resp.status.error else resp.status.state.value)
    cols = [c.name for c in resp.manifest.schema.columns]
    return pd.DataFrame((resp.result.data_array if resp.result else None) or [], columns=cols)


@st.cache_data(ttl=600)
def portfolio() -> pd.DataFrame:
    return run_sql(PORTFOLIO_SQL)


def md(text: str) -> None:
    st.markdown(escape_dollars(text))


st.title("Customer Lookup")
st.caption("Search certified customer_360 profiles by name, email or customer ID.")

with st.sidebar:
    st.subheader("Portfolio")
    try:
        pf = portfolio()
        for _, r in pf.iterrows():
            st.metric(r["segment"], f"{int(r['customers']):,}")
        md(f"**Revenue at risk:** {money(pf['revenue_at_risk'].astype(float).sum())}")
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not load portfolio counts: {e}")

lookup_tab, genie_tab = st.tabs(["Lookup", "Ask Genie"])

with lookup_tab:
    term = st.text_input("Customer name, email or ID", placeholder="e.g. Emerson Silva, emerson.silva342@example.com or 342")
    if term.strip():
        try:
            with st.spinner("Searching..."):
                matches = run_sql(*search_query(term))
        except Exception as e:  # noqa: BLE001
            st.error(f"Search failed: {e}")
            matches = pd.DataFrame()
        if matches.empty:
            st.info("No customers match that search.")
        else:
            labels = [f"#{r.customer_id} {r.customer_name} ({r.region}, {r.email})" for r in matches.itertuples()]
            idx = st.selectbox(f"{len(matches)} match(es)", range(len(labels)), format_func=lambda i: labels[i])
            c = matches.iloc[idx]
            st.subheader(f"#{c.customer_id} {c.customer_name}")
            m = st.columns(3)
            m[0].metric("Segment", c.segment)
            m[1].metric("Net LTV", money(c.net_ltv))
            m[2].metric("AOV", money(c.aov))
            m = st.columns(3)
            m[0].metric("Recency (days)", "—" if c.recency_days is None else c.recency_days)
            m[1].metric("Completed orders", c.completed_orders)
            md(
                f"**Email:** {c.email} · **Phone:** {c.phone} · **Region:** {c.region} · "
                f"**Business:** {'yes' if c.is_business == 'true' else 'no'} · **Signed up:** {c.signup_date}  \n"
                f"**Preferred store:** {c.preferred_store} · **Top category:** {c.top_category} · "
                f"**First / last order:** {c.first_order_date} / {c.last_order_date} · "
                f"**Gross spend:** {money(c.gross_spend)} · **Returned orders:** {c.returned_orders} · "
                f"**R/F/M:** {c.r_score}/{c.f_score}/{c.m_score} · **Revenue at risk:** {money(c.revenue_at_risk)}"
            )
            st.markdown("##### Last 10 orders")
            try:
                orders = run_sql(ORDERS_SQL, {"cid": str(c.customer_id)})
                if orders.empty:
                    st.info("This customer has no orders.")
                else:
                    st.dataframe(orders, hide_index=True, use_container_width=True)
            except Exception as e:  # noqa: BLE001
                st.error(f"Could not load orders: {e}")

with genie_tab:
    md("Ask the **Account Manager Assistant** Genie space a question in plain English.")
    question = st.text_input("Question", placeholder="Which region has the most revenue at risk?")
    if st.button("Ask Genie", type="primary", disabled=not question.strip()):
        if not GENIE_SPACE_ID:
            st.error("GENIE_SPACE_ID is not configured.")
        else:
            try:
                with st.spinner("Genie is thinking..."):
                    w = client()
                    msg = w.genie.start_conversation_and_wait(GENIE_SPACE_ID, question)
                answered = False
                for a in msg.attachments or []:
                    if a.text and a.text.content:
                        md(a.text.content)
                        answered = True
                    if a.query:
                        with st.expander("SQL"):
                            st.code(a.query.query, language="sql")
                        res = w.genie.get_message_attachment_query_result(
                            GENIE_SPACE_ID, msg.conversation_id, msg.id, a.attachment_id
                        ).statement_response
                        cols = [col.name for col in res.manifest.schema.columns]
                        rows = (res.result.data_array if res.result else None) or []
                        if rows:
                            st.dataframe(pd.DataFrame(rows, columns=cols), hide_index=True, use_container_width=True)
                        else:
                            st.info("The query returned no rows.")
                        answered = True
                if not answered:
                    st.info("Genie did not return an answer. Try rephrasing the question.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Genie request failed: {e}")

st.divider()
st.caption(FOOTER)
