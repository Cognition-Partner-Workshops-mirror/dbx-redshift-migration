"""Streamlit front end for the certified Customer 360 snapshot."""

import logging
import os
from decimal import Decimal

import streamlit as st
from databricks.sdk import WorkspaceClient

from data import ORDERS, PORTFOLIO, PORTFOLIO_SEGMENTS, SEARCH, ask, query

LOG = logging.getLogger(__name__)


@st.cache_resource
def client():
    return WorkspaceClient()


def money(amount):
    return f"${Decimal(amount):,.2f}" if amount is not None else "—"


def show_portfolio(workspace, warehouse):
    try:
        totals, = query(workspace, warehouse, PORTFOLIO)
        counts = {row["segment"]: row["customers"] for row in query(workspace, warehouse, PORTFOLIO_SEGMENTS)}
    except Exception:
        LOG.exception("Portfolio query failed")
        st.warning("Portfolio unavailable. Refresh to try again.")
        return
    for column, (label, value) in zip(st.columns(3), (
        ("Customers", totals["customers"]), ("Active customers", totals["active_customers"]),
        ("At risk", counts.get("At risk", "0")),
    ), strict=True):
        column.metric(label, f"{int(value):,}", border=True)


def show_customer(customer, workspace, warehouse):
    with st.container(border=True):
        st.subheader(customer["full_name"])
        st.caption(f"Customer #{customer['customer_id']}  ·  {customer['region']}  ·  {customer['segment']}")
        for column, (label, value) in zip(st.columns(4), (
            ("Net LTV", money(customer["net_ltv"])),
            ("Avg. order", money(customer["aov"])),
            ("Completed orders", customer["completed_orders"]),
            ("Days since purchase", customer["recency_days"] or "—"),
        ), strict=True):
            column.metric(label, value)

        details = [
            ("Email", customer["email"]), ("Phone", customer["phone"]),
            ("Customer type", "Business" if customer["is_business"] == "true" else "Consumer"),
            ("Joined", customer["signup_date"]), ("Preferred store", customer["preferred_store"]),
            ("Top category", customer["top_category"]), ("First order", customer["first_order_date"]),
            ("Last order", customer["last_order_date"]),
        ]
        for field_column, fields in zip(st.columns(2), (details[:4], details[4:]), strict=True):
            for label, value in fields:
                field_column.text(f"{label}: {value or '—'}")

    st.subheader("Last 10 orders")
    try:
        orders = query(workspace, warehouse, ORDERS, customer_id=int(customer["customer_id"]))
    except Exception:
        LOG.exception("Order history query failed")
        st.error("Order history unavailable. Refresh to try again.")
        return
    if orders:
        st.dataframe(orders, width="stretch", hide_index=True)
    else:
        st.info("This customer has no orders.")


def show_lookup(workspace, warehouse):
    with st.form("customer_search"):
        term = st.text_input("Name, email, or customer ID", placeholder="e.g. #342", max_chars=200).strip()
        submitted = st.form_submit_button("Search", type="primary")
    if submitted:
        st.session_state.pop("matches", None)
        if not term:
            st.info("Enter a name, email, or customer ID.")
        else:
            try:
                with st.spinner("Finding customers…"):
                    st.session_state.matches = query(workspace, warehouse, SEARCH, term=term)
            except Exception:
                LOG.exception("Customer search failed")
                st.error("Search unavailable. Try again shortly.")

    matches = st.session_state.get("matches")
    if matches == []:
        st.info("No matching customers. Try a different name, email, or ID.")
    elif matches:
        if len(matches) > 1:
            if len(matches) == 25:
                st.caption("Showing the first 25 matches. Use a more specific search to narrow the list.")
            index = st.selectbox(
                "Matching customers", range(len(matches)),
                format_func=lambda i: f"{matches[i]['full_name']} · #{matches[i]['customer_id']}",
            )
        else:
            index = 0
        show_customer(matches[index], workspace, warehouse)


def show_genie(workspace, space_id):
    st.subheader("Ask Genie")
    st.caption("Ask about the certified snapshot. Try “Which regions have the most revenue at risk?”")
    history = st.session_state.setdefault("history", [])
    if history and st.button("New conversation"):
        history.clear()
        st.session_state.pop("conversation_id", None)
    with st.form("genie_question", clear_on_submit=True):
        question = st.text_input("Question", max_chars=1000).strip()
        send = st.form_submit_button("Ask Genie", type="primary")
    if send and not question:
        st.info("Enter a question for Genie.")
    elif send:
        with st.spinner("Genie is querying Customer 360…"):
            try:
                conversation_id, response = ask(
                    workspace, space_id, question, st.session_state.get("conversation_id")
                )
            except Exception:
                LOG.exception("Genie request failed")
                st.error("Genie could not complete the request. Try again shortly.")
            else:
                st.session_state.conversation_id = conversation_id
                history.append((question, response))

    for question, response in reversed(history):
        with st.chat_message("user"):
            st.text(question)
        with st.chat_message("assistant"):
            for answer in response["answer"]:
                st.markdown(answer.replace("$", r"\$"))
            for result in response["queries"]:
                if result["description"] and not response["answer"]:
                    st.markdown(result["description"].replace("$", r"\$"))
                elif not result["description"] and not response["answer"]:
                    st.caption("Genie returned the query result below.")
                if result["rows"]:
                    st.dataframe(result["rows"], width="stretch", hide_index=True)
                    if len(result["rows"]) == 50:
                        st.caption("Up to 50 result rows are displayed.")
                else:
                    st.info("The query returned no rows.")
                with st.expander("View generated SQL"):
                    st.code(result["sql"], language="sql")
            if not response["answer"] and not response["queries"]:
                st.info("Genie returned no answer. Try rephrasing your question.")


def main():
    st.set_page_config(page_title="Customer Lookup", layout="wide")
    st.title("Customer Lookup")
    st.caption("Search the portfolio, review customer health, and ask questions about certified metrics.")
    try:
        workspace = client()
        warehouse = os.environ["CUSTOMER_360_WAREHOUSE_ID"]
        space_id = os.environ["CUSTOMER_360_GENIE_ID"]
    except (KeyError, ValueError):
        LOG.exception("Customer Lookup configuration is incomplete")
        st.error("Customer Lookup is missing its Databricks configuration.")
        return
    show_portfolio(workspace, warehouse)
    lookup_tab, genie_tab = st.tabs(["Find a customer", "Ask Genie"])
    with lookup_tab:
        show_lookup(workspace, warehouse)
    with genie_tab:
        show_genie(workspace, space_id)
    st.divider()
    st.caption("Data as of 2025-12-31 · certified customer_360 metrics")


if __name__ == "__main__":
    main()
