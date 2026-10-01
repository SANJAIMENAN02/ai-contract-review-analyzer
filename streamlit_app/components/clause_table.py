"""Detected-clauses table plus one expandable panel per clause."""
from __future__ import annotations

from typing import Dict, List

import pandas as pd
import streamlit as st

from streamlit_app.theme import badge, esc, render_html


def clauses_dataframe(clauses: List[Dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Clause": c["clause_name"],
                "Detected": "Yes" if c.get("found") else "No",
                "Confidence": c.get("confidence", 0) if c.get("found") else None,
                "Risk": c["risk_level"].title() if c.get("found") else "-",
            }
            for c in clauses
        ]
    )


def render_clause_table(clauses: List[Dict]) -> None:
    detected = sum(1 for c in clauses if c.get("found"))
    st.caption(f"{detected} of {len(clauses)} clause categories detected")
    st.dataframe(
        clauses_dataframe(clauses),
        hide_index=True,
        width="stretch",
        height=35 * (len(clauses) + 1) + 3,  # show every row; no inner scrolling
        column_config={
            "Confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%d%%"),
        },
    )

    st.markdown("##### Clause details")
    for c in clauses:
        status = "" if c.get("found") else "  (not detected)"
        with st.expander(f"{c['clause_name']}{status}"):
            render_html(
                f"""<div style="margin-bottom:.4rem">{badge(c['risk_level']) if c.get('found') else '<span class="badge badge-soft">NOT DETECTED</span>'}
                <span class="badge badge-soft">Confidence {c.get('confidence', 0)}%</span></div>"""
            )
            st.markdown(f"**Explanation.** {c.get('explanation', '')}")
            if c.get("found") and c.get("content"):
                st.markdown("**Detected text**")
                st.code(c["content"], language=None, wrap_lines=True)
                st.markdown(
                    "**Suggested review action.** Read this provision in full and confirm it matches "
                    "what was agreed. Clause risk here is a category baseline; see the findings tab "
                    "for specific concerns."
                )
            else:
                st.markdown(
                    "**Suggested review action.** If this topic matters for the agreement, consider "
                    "whether a clause covering it should be added."
                )
