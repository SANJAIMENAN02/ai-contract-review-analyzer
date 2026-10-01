"""Plotly charts built strictly from backend data."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

import plotly.graph_objects as go

from streamlit_app.theme import CATEGORY_LABELS, RISK_COLORS

_LAYOUT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"family": "Segoe UI, Arial", "color": "#1F2937"})


def build_breakdown_chart(breakdown: Dict[str, int]) -> go.Figure:
    """Horizontal bars: each category's contribution (in points) to the overall score."""
    labels = [CATEGORY_LABELS[k] for k in CATEGORY_LABELS]
    values = [breakdown.get(k, 0) for k in CATEGORY_LABELS]
    fig = go.Figure(
        go.Bar(
            x=values, y=labels, orientation="h", marker_color="#23386B",
            text=values, textposition="outside", cliponaxis=False,
            hovertemplate="%{y}: %{x} points<extra></extra>",
        )
    )
    top = max(values + [10])
    fig.update_layout(
        height=300, margin=dict(l=10, r=30, t=10, b=30), **_LAYOUT,
        xaxis=dict(title="Contribution to overall score (points)", range=[0, top * 1.2], gridcolor="#E6E9F0"),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def build_severity_chart(risks: List[Dict]) -> go.Figure:
    counts = Counter(r.get("risk_level", "LOW") for r in risks)
    levels = [lv for lv in ("CRITICAL", "HIGH", "MEDIUM", "LOW") if counts.get(lv)]
    fig = go.Figure(
        go.Pie(
            labels=levels, values=[counts[lv] for lv in levels], hole=0.6, sort=False,
            marker=dict(colors=[RISK_COLORS[lv] for lv in levels]), textinfo="value",
            hovertemplate="%{label}: %{value} finding(s)<extra></extra>",
        )
    )
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), **_LAYOUT, legend=dict(orientation="h", y=-0.05))
    return fig
