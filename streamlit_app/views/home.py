from __future__ import annotations

import streamlit as st

from streamlit_app.components.header import disclaimer
from streamlit_app.nav import go
from streamlit_app.theme import render_html

FEATURES = [
    ("📄", "Contract Analysis", "Upload a PDF, DOCX or TXT contract and get a structured analysis in seconds."),
    ("⚠️", "Risk Detection", "Rule-based checks flag patterns such as unlimited liability, one-sided termination and auto-renewal."),
    ("🔎", "Clause Intelligence", "Detects 15 clause categories and shows which are present, with confidence and the matching text."),
    ("🧠", "AI Summary", "A local extractive summary by default; an optional OpenAI-compatible model can be enabled."),
]
STEPS = [("Upload", "PDF, DOCX, TXT"), ("Extract", "Read the text"), ("Detect Clauses", "15 categories"), ("Analyze Risks", "Score 0-100"), ("Generate Report", "PDF download")]


def render() -> None:
    render_html(
        """<div class="hero"><h1>AI Contract Risk Analyzer</h1>
        <p>Analyze contracts, identify risky clauses, and understand important obligations using NLP-powered analysis.</p></div>"""
    )
    if st.button("Analyze a Contract", type="primary"):
        go("analyze")

    st.write("")
    cols = st.columns(4)
    for col, (icon, title, text) in zip(cols, FEATURES):
        with col:
            render_html(f'<div class="card"><h4>{icon} {title}</h4><p>{text}</p></div>')

    st.markdown("### How it works")
    cols = st.columns(len(STEPS))
    for i, (col, (title, sub)) in enumerate(zip(cols, STEPS), start=1):
        with col:
            render_html(f'<div class="step">{i}. {title}<small>{sub}</small></div>')
    st.write("")
    disclaimer()
