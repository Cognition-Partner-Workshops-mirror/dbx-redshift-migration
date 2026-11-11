"""Customer Lookup — a certified account-management workspace."""
import logging
import os

import streamlit as st
from backend import Backend
from databricks.sdk.errors import DatabricksError

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Customer Lookup", page_icon="👤", layout="wide")


@st.cache_resource
def backend():
    return Backend(os.environ["DATABRICKS_WAREHOUSE_ID"], os.environ["GENIE_SPACE_ID"])


def money(value):
    return "—" if value is None else f"${float(value):,.2f}"


def failure(area, error):
    logger.error("%s failed (%s)", area, type(error).__name__)
    st.error(f"{area} is unavailable. Please retry; contact the app owner if this persists.")


st.title("Customer Lookup")
st.caption("Account intelligence · completed-order revenue · USD")
st.subheader("Portfolio")
try:
    with st.spinner("Loading portfolio…"):
        segments = backend().portfolio()
    if segments:
        for column, segment in zip(st.columns(len(segments)), segments, strict=True):
            column.metric(segment["health_segment"], f"{int(segment['customers']):,}")
    else:
        st.info("No portfolio data available.")
except (DatabricksError, RuntimeError, TimeoutError, ValueError, KeyError) as error:
    failure("Portfolio", error)

st.divider()
with st.form("customer_search"):
    term = st.text_input("Name, email or customer ID", placeholder="Emerson Silva")
    submitted = st.form_submit_button("Search", type="primary")
if submitted:
    st.session_state.pop("matches", None)
    try:
        with st.spinner("Searching customers…"):
            st.session_state.matches = backend().search(term)
    except (DatabricksError, RuntimeError, TimeoutError, ValueError, KeyError) as error:
        failure("Customer search", error)
matches = st.session_state.get("matches")
if matches is not None:
    if not matches:
        st.info("No customers found. Enter a name, email or customer ID.")
    else:
        st.caption("Up to 50 matching customers. Refine the search if needed.")
        st.dataframe(matches, hide_index=True, width="stretch")
        selected = st.selectbox("Select customer", [m["customer_id"] for m in matches],
                                format_func=lambda value: next(
                                    f"{m['name']} · {m['email']} · #{value}" for m in matches
                                    if m["customer_id"] == value))
        try:
            with st.spinner("Loading customer and orders…"):
                card = backend().customer(selected)
                orders = backend().orders(selected)
            if card is None:
                st.warning("This customer is no longer available. Search again.")
            else:
                st.subheader(card["name"])
                colors = {"Champion": "green", "Loyal": "blue", "At risk": "orange",
                          "Hibernating": "red", "Promising": "violet", "Never ordered": "gray"}
                segment = card["health_segment"]
                st.markdown(f":{colors.get(segment, 'gray')}[**{segment}**]")
                left, middle, right = st.columns(3)
                with left:
                    st.write("**Email:**", card["email"] or "—")
                    st.write("**Phone:**", card["phone"] or "—")
                    st.write("**Region:**", card["region"] or "—")
                    st.write("**Account type:**", "Business" if str(card["is_business"]).lower() == "true" else "Consumer")
                    st.write("**Signup date:**", card["signup_date"] or "—")
                    st.write("**Preferred store:**", card["preferred_store_name"] or "—")
                    st.write("**Store city:**", card["preferred_store_city"] or "—")
                with middle:
                    st.metric("Net lifetime value", money(card["net_ltv"]))
                    st.metric("Completed orders", card["completed_orders"])
                    st.metric("True AOV", money(card["aov"]))
                with right:
                    st.metric("Recency · days since completed order",
                              card["recency_days"] if card["recency_days"] is not None else "No completed orders")
                    st.write("**Returns:**", card["return_count"])
                    st.write("**Top category:**", card["top_category"] or "—")
                    if segment == "At risk":
                        st.metric("Revenue at risk", money(card["revenue_at_risk"]))
                st.subheader("Recent orders")
                st.caption("Last 10 · gross includes all statuses; net recognizes complete orders only")
                if orders:
                    st.dataframe(orders, hide_index=True, width="stretch")
                else:
                    st.info("No recent orders for this customer.")
        except (DatabricksError, RuntimeError, TimeoutError, ValueError, KeyError) as error:
            failure("Customer details", error)

st.divider()
st.subheader("Ask Genie")
st.caption("Account Manager Assistant · questions use the certified snapshot, not today's date")
with st.form("ask_genie"):
    question = st.text_area("Your question", placeholder="How much revenue is at risk by region?")
    ask = st.form_submit_button("Ask Genie")
if ask:
    st.session_state.pop("answer", None)
    try:
        with st.spinner("Genie is analyzing your question…"):
            st.session_state.answer = backend().ask(question)
    except (DatabricksError, RuntimeError, TimeoutError, ValueError, KeyError) as error:
        failure("Genie", error)
if "answer" in st.session_state:
    answer = st.session_state.answer
    st.write(answer["text"])
    for result in answer["queries"]:
        if result["description"]:
            st.write(result["description"])
        with st.expander("Generated SQL"):
            st.code(result["sql"], language="sql")
        if result["rows"]:
            st.dataframe(result["rows"], hide_index=True, width="stretch")
        else:
            st.info("The query returned no rows.")
st.divider()
st.caption("Data as of 2025-12-31 · certified customer_360 metrics")
