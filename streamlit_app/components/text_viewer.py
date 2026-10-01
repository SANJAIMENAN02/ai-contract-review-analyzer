"""Scrollable contract text with optional highlighting. The original file is never modified."""
from __future__ import annotations

from typing import Dict, List, Tuple

import streamlit as st

from streamlit_app.theme import esc

MAX_CHARS = 200_000


def build_highlighted_html(text: str, ranges: List[Tuple[int, int, str]]) -> str:
    """Wrap (start, end, css_class) ranges in <mark>; overlaps are skipped. Everything is escaped."""
    parts, cursor = [], 0
    for start, end, css in sorted(ranges):
        if start < cursor or end <= start or start >= len(text):
            continue
        end = min(end, len(text))
        parts.append(esc(text[cursor:start]))
        parts.append(f'<mark class="{css}">{esc(text[start:end])}</mark>')
        cursor = end
    parts.append(esc(text[cursor:]))
    return "".join(parts)


def render_text_viewer(analysis: Dict) -> None:
    text = analysis.get("full_text") or ""
    if not text:
        st.info("No extracted text is available for this analysis.")
        return

    clauses = [c for c in analysis.get("clauses", []) if c.get("found") and c.get("start_index") is not None]
    options = ["Risk findings", "None"] + [f"Clause: {c['clause_name']}" for c in clauses]
    choice = st.selectbox("Highlight", options, key="viewer_highlight")

    ranges: List[Tuple[int, int, str]] = []
    if choice == "Risk findings":
        ranges = [(r["start_index"], r["end_index"], "risk") for r in analysis.get("risks", []) if r.get("start_index") is not None and r.get("end_index")]
    elif choice.startswith("Clause: "):
        name = choice[len("Clause: "):]
        for c in clauses:
            if c["clause_name"] == name:
                ranges = [(c["start_index"], c["end_index"], "clause")]

    shown = text[:MAX_CHARS]
    with st.container(height=520, border=True):
        st.html(f'<div class="contract-text">{build_highlighted_html(shown, ranges)}</div>')
    if len(text) > MAX_CHARS:
        st.caption(f"Showing the first {MAX_CHARS:,} characters of {len(text):,}.")
    st.caption("Highlights show where matched patterns were found in the extracted text.")
