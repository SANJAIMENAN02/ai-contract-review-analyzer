"""Risk findings and review recommendations."""
from __future__ import annotations

from typing import Dict, List

import streamlit as st

from streamlit_app.theme import CATEGORY_LABELS, LEVEL_ORDER, badge, esc, render_html


def _affected_clause(risk: Dict) -> str:
    title = risk.get("risk_title", "")
    if title.startswith("Missing "):
        return "Compliance (clause not detected)"
    return CATEGORY_LABELS.get(risk.get("category", ""), "Other")


def render_finding(risk: Dict) -> None:
    level = (risk.get("risk_level") or "LOW").upper()
    excerpt = risk.get("matched_text")
    excerpt_html = f'<div class="excerpt">{esc(excerpt)}</div>' if excerpt else ""
    render_html(
        f"""<div class="finding sev-{level.lower()}">
        <span class="title">{esc(risk.get('risk_title'))}</span>{badge(level)}
        <div class="meta">Affected area: {esc(_affected_clause(risk))}</div>
        <p><b>Explanation.</b> {esc(risk.get('description'))}</p>
        <p><b>Recommendation.</b> {esc(risk.get('recommendation'))}</p>
        {excerpt_html}</div>"""
    )


def render_findings(risks: List[Dict]) -> None:
    st.caption(
        "These findings flag provisions that may warrant review or may create additional "
        "contractual exposure. They are pattern matches, not legal conclusions."
    )
    ordered = sorted(risks, key=lambda r: LEVEL_ORDER.get(r.get("risk_level", "LOW"), 4))
    high = [r for r in ordered if r.get("risk_level") in ("HIGH", "CRITICAL")]
    show_all = st.toggle("Include medium and low findings", value=not high, key="show_all_findings")
    shown = ordered if show_all else high
    if not shown:
        st.success("No high-risk patterns were detected. A full read-through is still advisable.")
        return
    for risk in shown:
        render_finding(risk)


def render_recommendations(risks: List[Dict], general: List[str]) -> None:
    st.info("Recommendations are automated analysis suggestions, not legal advice.")
    ordered = sorted(risks, key=lambda r: LEVEL_ORDER.get(r.get("risk_level", "LOW"), 4))
    if ordered:
        st.markdown("##### Issue-by-issue review actions")
    for r in ordered:
        with st.expander(f"{r.get('risk_title')}  ·  {r.get('risk_level')}"):
            st.markdown(f"**Issue.** {r.get('risk_title')}")
            st.markdown(f"**Why it matters.** {r.get('description')}")
            st.markdown(f"**Suggested review action.** {r.get('recommendation')}")
    risk_recs = {r.get("recommendation") for r in risks}
    extra = [g for g in general if g not in risk_recs]
    if extra:
        st.markdown("##### General guidance")
        for item in extra:
            st.markdown(f"- {item}")
