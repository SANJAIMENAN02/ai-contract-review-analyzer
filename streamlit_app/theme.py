"""Shared colours and small HTML helpers. All user-derived text is escaped."""
from __future__ import annotations

import html
import re

import streamlit as st

from streamlit_app import config

RISK_COLORS = {
    "LOW": "#3F6B4F",
    "MEDIUM": "#C08A2E",
    "HIGH": "#B3541E",
    "CRITICAL": "#9B2226",
    "NONE": "#6B7280",
}
LEVEL_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "NONE": 4}

# Fallback only for when the backend config is unreachable; normally thresholds come from /api/config.
DEFAULT_THRESHOLDS = [
    {"level": "LOW", "min_score": 0, "max_score": 25},
    {"level": "MEDIUM", "min_score": 26, "max_score": 50},
    {"level": "HIGH", "min_score": 51, "max_score": 75},
    {"level": "CRITICAL", "min_score": 76, "max_score": 100},
]

CATEGORY_LABELS = {
    "termination_risk": "Termination",
    "liability_risk": "Liability",
    "payment_risk": "Payment",
    "compliance_risk": "Compliance",
    "confidentiality_risk": "Confidentiality",
    "other_risk": "Other",
}


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def badge(level: str) -> str:
    level = (level or "NONE").upper()
    return f'<span class="badge badge-{level.lower()}">{esc(level)}</span>'


def html_block(markup: str) -> str:
    """Collapse blank lines / indentation so Markdown treats the snippet as one raw HTML block."""
    return re.sub(r"\s*\n\s*", " ", markup.strip())


def render_html(markup: str) -> None:
    st.markdown(html_block(markup), unsafe_allow_html=True)


def inject_css() -> None:
    css = config.STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def format_date(value: str) -> str:
    try:
        from datetime import datetime

        return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError):
        return value or "-"
