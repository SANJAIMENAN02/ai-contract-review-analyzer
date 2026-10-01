from __future__ import annotations

import streamlit as st

from streamlit_app import api_client
from streamlit_app.components.charts import build_breakdown_chart, build_severity_chart
from streamlit_app.components.clause_table import render_clause_table
from streamlit_app.components.header import disclaimer, kpi_card, page_header
from streamlit_app.components.risk_cards import render_findings, render_recommendations
from streamlit_app.components.risk_gauge import build_risk_gauge
from streamlit_app.components.summary_card import render_summary
from streamlit_app.components.text_viewer import render_text_viewer
from streamlit_app.nav import go
from streamlit_app.theme import DEFAULT_THRESHOLDS, badge, format_date, render_html

PLOT_CONFIG = {"displayModeBar": False}


def _report_button(contract_id: str) -> None:
    cache = st.session_state.report_cache
    if contract_id not in cache:
        try:
            cache[contract_id] = api_client.download_report(contract_id)
        except api_client.ApiError as exc:
            st.warning(f"Report unavailable: {exc.message}")
            return
    st.download_button(
        "Download Analysis Report",
        data=cache[contract_id],
        file_name=f"contract_risk_report_{contract_id}.pdf",
        mime="application/pdf",
        type="primary",
    )


def render() -> None:
    analysis = st.session_state.get("current_analysis")
    if not analysis:
        page_header("Dashboard", "Results of the most recent analysis appear here.")
        st.info("No contract is loaded yet.")
        c1, c2 = st.columns(2)
        if c1.button("Analyze a contract", type="primary"):
            go("analyze")
        if c2.button("Open history"):
            go("history")
        return

    cfg = api_client.get_backend_config()
    thresholds = cfg["risk_thresholds"] if cfg else None

    head, action = st.columns([3, 1])
    with head:
        page_header(analysis["file_name"], f"Analyzed {format_date(analysis['upload_date'])}")
    with action:
        st.write("")
        _report_button(analysis["contract_id"])

    stats = analysis["statistics"]
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("Overall Risk Score", f"{analysis['risk_score']}/100")
    with k2:
        band = next((t for t in (thresholds or DEFAULT_THRESHOLDS) if t["level"] == analysis["risk_level"]), None)
        kpi_card("Risk Level", analysis["risk_level"], f"Score band {band['min_score']} to {band['max_score']}" if band else "")
    with k3:
        kpi_card("Clauses Detected", str(stats["clause_count"]), f"{stats['missing_clauses']} not detected")
    with k4:
        kpi_card("High-Risk Findings", str(stats["high_and_above_risks"]), f"{stats['risks_found']} findings in total")
    st.write("")

    tabs = st.tabs(["Overview", "Detected Clauses", "⚠️ High-Risk Findings", "Contract Summary", "Recommendations", "Contract Text"])
    with tabs[0]:
        left, right = st.columns([1, 1])
        with left:
            st.markdown("##### Risk score")
            st.plotly_chart(build_risk_gauge(analysis["risk_score"], analysis["risk_level"], thresholds), width="stretch", config=PLOT_CONFIG)
        with right:
            st.markdown("##### Risk breakdown")
            st.plotly_chart(build_breakdown_chart(analysis["risk_breakdown"]), width="stretch", config=PLOT_CONFIG)
        sev, bands = st.columns([1, 1])
        with sev:
            st.markdown("##### Findings by severity")
            if analysis["risks"]:
                st.plotly_chart(build_severity_chart(analysis["risks"]), width="stretch", config=PLOT_CONFIG)
            else:
                st.success("No risk findings were detected.")
        with bands:
            st.markdown("##### Score bands")
            st.caption("Thresholds are defined by the backend risk engine.")
            for t in thresholds or DEFAULT_THRESHOLDS:
                render_html(f'<div style="margin-bottom:.4rem">{badge(t["level"])} <span style="color:#5B6475;font-size:.9rem">&nbsp;{t["min_score"]} to {t["max_score"]}</span></div>')
    with tabs[1]:
        render_clause_table(analysis["clauses"])
    with tabs[2]:
        render_findings(analysis["risks"])
    with tabs[3]:
        render_summary(analysis)
    with tabs[4]:
        render_recommendations(analysis["risks"], analysis["recommendations"])
    with tabs[5]:
        with st.expander("Show Extracted Contract Text", expanded=False):
            render_text_viewer(analysis)
    st.write("")
    disclaimer()
