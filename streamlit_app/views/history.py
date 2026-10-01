from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from streamlit_app import api_client
from streamlit_app.components.header import disclaimer, page_header
from streamlit_app.nav import go
from streamlit_app.theme import badge, format_date, esc, render_html

PAGE_SIZE = 10


@st.dialog("Delete analysis")
def _confirm_delete(item: dict) -> None:
    st.write(f"Delete the stored analysis for **{item['file_name']}**? This cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Delete", type="primary", width="stretch"):
        try:
            api_client.delete_contract(item["contract_id"])
        except api_client.ApiError as exc:
            st.error(exc.message)
            return
        if st.session_state.get("current_contract_id") == item["contract_id"]:
            st.session_state.current_analysis = st.session_state.current_contract_id = st.session_state.current_filename = None
        st.session_state.report_cache.pop(item["contract_id"], None)
        st.rerun()
    if c2.button("Cancel", width="stretch"):
        st.rerun()


def _view(contract_id: str) -> None:
    try:
        analysis = api_client.get_contract(contract_id)
    except api_client.ApiError as exc:
        st.error(exc.message)
        return
    st.session_state.current_analysis = analysis
    st.session_state.current_contract_id = contract_id
    st.session_state.current_filename = analysis["file_name"]
    go("dashboard")


def render() -> None:
    page_header("History", "Previously analyzed contracts stored by the backend.")
    try:
        items = api_client.get_contracts()
    except api_client.ApiError as exc:
        st.error(exc.message)
        return
    if not items:
        st.info("No contracts have been analyzed yet.")
        if st.button("Analyze a contract", type="primary"):
            go("analyze")
        return

    df = pd.DataFrame(items)
    df["date"] = pd.to_datetime(df["upload_date"], errors="coerce", utc=True)

    f1, f2, f3 = st.columns([2, 2, 2])
    query = f1.text_input("Contract name", placeholder="Search by file name")
    levels = f2.multiselect("Risk level", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    valid = df["date"].dropna()
    date_range = None
    if not valid.empty:
        lo, hi = valid.min().date(), max(valid.max().date(), date.today())
        date_range = f3.date_input("Date range", value=(lo, hi), min_value=lo, max_value=hi)

    mask = pd.Series(True, index=df.index)
    if query:
        mask &= df["file_name"].str.contains(query, case=False, na=False, regex=False)
    if levels:
        mask &= df["risk_level"].isin(levels)
    if date_range and len(date_range) == 2:
        mask &= df["date"].dt.date.between(date_range[0], date_range[1]) | df["date"].isna()
    filtered = df[mask].sort_values("date", ascending=False, na_position="last")

    a, b, c = st.columns(3)
    a.metric("Contracts", len(filtered))
    b.metric("Average risk score", f"{filtered['risk_score'].mean():.0f}" if len(filtered) else "-")
    c.metric("High or critical", int(filtered["risk_level"].isin(["HIGH", "CRITICAL"]).sum()))
    st.write("")

    if filtered.empty:
        st.warning("No contracts match these filters.")
        return

    limit = st.session_state.setdefault("history_limit", PAGE_SIZE)
    hdr = st.columns([3.2, 1.9, 1, 1.2, 0.9, 1.1, 0.9])
    for col, label in zip(hdr, ["Contract", "Date", "Score", "Risk level", "Actions", "", ""]):
        if label:
            col.markdown(f"**{label}**")

    for item in filtered.head(limit).to_dict("records"):
        cid = item["contract_id"]
        cols = st.columns([3.2, 1.9, 1, 1.2, 0.9, 1.1, 0.9], vertical_alignment="center")
        cols[0].markdown(esc(item["file_name"]))
        cols[1].markdown(format_date(item["upload_date"]))
        cols[2].markdown(f"{item['risk_score']}/100")
        cols[3].markdown(badge(item["risk_level"]), unsafe_allow_html=True)
        if cols[4].button("View", key=f"view_{cid}"):
            _view(cid)
        cache = st.session_state.report_cache
        if cid in cache:
            cols[5].download_button("Report", cache[cid], file_name=f"contract_risk_report_{cid}.pdf", mime="application/pdf", key=f"dl_{cid}")
        elif cols[5].button("Report", key=f"prep_{cid}", help="Fetch the PDF from the backend"):
            try:
                cache[cid] = api_client.download_report(cid)
                st.rerun()
            except api_client.ApiError as exc:
                st.error(exc.message)
        if cols[6].button("Delete", key=f"del_{cid}"):
            _confirm_delete(item)

    if len(filtered) > limit and st.button("Show more"):
        st.session_state.history_limit = limit + PAGE_SIZE
        st.rerun()
    st.caption("Click Report once to fetch the PDF, then click again to download it.")
    disclaimer()
