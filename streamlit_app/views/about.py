from __future__ import annotations

import streamlit as st

from streamlit_app.components.header import page_header
from streamlit_app.theme import render_html


def render() -> None:
    page_header("About", "What this application is and what it is not.")
    st.markdown("### What is this?")
    st.write(
        "An AI-assisted contract analysis application that extracts contract text, detects important "
        "clauses, identifies potential risk patterns, summarizes provisions, and provides review suggestions."
    )
    st.markdown("### How the analysis works")
    st.write(
        "The core engine is deterministic and rule-based: keyword and regular-expression matching for "
        "clauses and risk patterns, and a TextRank-style extractive summarizer. The same document always "
        "produces the same score. An optional OpenAI-compatible model can improve the summary wording; "
        "if it is not configured or fails, the local summary is used automatically."
    )
    st.markdown("### Technology")
    st.code("Python\nFastAPI\nStreamlit\nNLP\nPyMuPDF\npython-docx\nPlotly\nPydantic", language=None)
    st.markdown("### Important disclaimer")
    st.warning(
        "This application provides automated contract analysis and educational/review assistance. "
        "It does not replace a qualified lawyer or constitute legal advice."
    )
