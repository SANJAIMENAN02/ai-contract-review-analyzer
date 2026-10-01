from __future__ import annotations

import os

import streamlit as st

from streamlit_app import api_client
from streamlit_app.components.header import kpi_card, page_header
from streamlit_app.nav import go


def _fmt_size(n: int) -> str:
    return f"{n / 1024:.1f} KB" if n < 1024 * 1024 else f"{n / (1024 * 1024):.2f} MB"


def render() -> None:
    page_header("Analyze Contract", "Upload a contract; the FastAPI backend performs the analysis.")

    cfg = api_client.get_backend_config()
    max_mb = cfg["max_file_size_mb"] if cfg else None
    exts = [e.lstrip(".") for e in cfg["allowed_extensions"]] if cfg else ["pdf", "docx", "txt"]

    c1, c2 = st.columns(2)
    c1.markdown(f"**Supported formats:** {', '.join(e.upper() for e in exts)}")
    c2.markdown(f"**Maximum file size:** {f'{max_mb} MB' if max_mb else 'set by the backend (backend offline)'}")

    upload = st.file_uploader("Choose a contract file", type=exts, accept_multiple_files=False)
    if upload is None:
        st.info("Select a file to begin. Sample contracts are in the `sample_contracts/` folder.")
        return

    m1, m2, m3 = st.columns(3)
    with m1:
        kpi_card("Filename", os.path.basename(upload.name), small=True)
    with m2:
        kpi_card("File type", os.path.splitext(upload.name)[1].lstrip(".").upper() or "-")
    with m3:
        kpi_card("File size", _fmt_size(upload.size))
    st.write("")

    too_big = bool(max_mb) and upload.size > max_mb * 1024 * 1024
    if too_big:
        st.error(f"This file is larger than the {max_mb} MB limit.")

    if st.button("Analyze Contract", type="primary", disabled=too_big):
        try:
            with st.spinner("Analyzing: extracting text, detecting clauses, scoring risks..."):
                analysis = api_client.analyze_contract(upload)
        except api_client.ApiError as exc:
            st.error(exc.message)
            return
        st.session_state.current_analysis = analysis
        st.session_state.current_contract_id = analysis["contract_id"]
        st.session_state.current_filename = analysis["file_name"]
        go("dashboard")
