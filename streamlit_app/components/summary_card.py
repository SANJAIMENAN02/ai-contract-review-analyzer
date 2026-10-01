"""Contract summary and extracted key facts. Missing facts always read 'Not detected'."""
from __future__ import annotations

from typing import Dict, List, Optional

import streamlit as st

from streamlit_app.theme import esc, render_html

NOT_DETECTED = "Not detected"


def _card(title: str, body_html: str) -> None:
    render_html(f'<div class="card"><h4>{esc(title)}</h4>{body_html}</div>')


def _list_html(items: List[str]) -> str:
    if not items:
        return f"<p>{NOT_DETECTED}</p>"
    return "<ul style='margin:0;padding-left:1.1rem;color:#2B3445;font-size:.9rem'>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def _text_html(value: Optional[str]) -> str:
    return f"<p>{esc(value)}</p>" if value else f"<p>{NOT_DETECTED}</p>"


def render_summary(analysis: Dict) -> None:
    mode = analysis.get("summary_mode", "local")
    label = "AI-enhanced summary" if mode == "ai" else "Local extractive summary"
    st.markdown(f"##### Summary  <span class='badge badge-soft'>{label}</span>", unsafe_allow_html=True)
    st.write(analysis.get("summary") or NOT_DETECTED)
    if mode != "ai":
        st.caption("Generated locally by sentence ranking; no external AI service was used.")

    details = analysis.get("details") or {}
    st.markdown("##### Key contract details")
    st.caption("Extracted with pattern matching. Anything not found is shown as 'Not detected'.")

    c1, c2 = st.columns(2)
    with c1:
        _card("Parties", _list_html(details.get("parties", [])))
    with c2:
        _card("Contract duration", _text_html(details.get("duration")))
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        _card("Important dates", _list_html(details.get("important_dates", [])))
    with c2:
        _card("Payment terms", _list_html(details.get("payment_terms", [])))
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        _card("Obligations", _list_html(details.get("obligations", [])))
    with c2:
        _card("Termination conditions", _list_html(details.get("termination_conditions", [])))
    st.write("")
    _card("Key provisions detected", _list_html(details.get("key_provisions", [])))
