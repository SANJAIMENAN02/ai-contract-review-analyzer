"""Plotly gauge for the overall 0-100 risk score. Ranges come from the backend."""
from __future__ import annotations

from typing import Dict, List, Optional

import plotly.graph_objects as go

from streamlit_app.theme import DEFAULT_THRESHOLDS, RISK_COLORS

_BAND_TINTS = {"LOW": "#DCE9E0", "MEDIUM": "#F5E8CB", "HIGH": "#F1D6C6", "CRITICAL": "#EBC7C8"}


def build_risk_gauge(score: int, level: str, thresholds: Optional[List[Dict]] = None) -> go.Figure:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    steps = [
        {"range": [t["min_score"] if i == 0 else t["min_score"] - 1, t["max_score"]], "color": _BAND_TINTS.get(t["level"], "#EEE")}
        for i, t in enumerate(thresholds)
    ]
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 40, "color": "#14213D"}},
            title={"text": f"<b>{level}</b>", "font": {"size": 18, "color": RISK_COLORS.get(level, "#14213D")}},
            gauge={
                "axis": {"range": [0, 100], "tickvals": [0, 25, 50, 75, 100]},
                "bar": {"color": RISK_COLORS.get(level, "#14213D"), "thickness": 0.28},
                "steps": steps,
                "borderwidth": 0,
            },
        )
    )
    fig.update_layout(height=270, margin=dict(l=40, r=40, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", font={"family": "Segoe UI, Arial"})
    return fig
