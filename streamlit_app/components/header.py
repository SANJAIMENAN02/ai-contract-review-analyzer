"""Page header, disclaimer and the small KPI card used across pages."""
from __future__ import annotations

import streamlit as st

from streamlit_app import config
from streamlit_app.theme import esc, render_html


def page_header(title: str, subtitle: str = "") -> None:
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    render_html(f'<div class="page-header"><h1>{esc(title)}</h1>{sub}</div>')


def disclaimer() -> None:
    st.caption(config.DISCLAIMER)


def kpi_card(label: str, value: str, sub: str = "", badge_html: str = "", small: bool = False) -> None:
    render_html(
        f"""<div class="card"><div class="label">{esc(label)}</div>
        <div class="value{" small" if small else ""}">{esc(value)}</div>
        <div class="sub">{badge_html}{esc(sub)}</div></div>"""
    )
