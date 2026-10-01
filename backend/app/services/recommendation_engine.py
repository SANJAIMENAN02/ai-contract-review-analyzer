"""
recommendation_engine.py

Turns the raw list of detected risks into a de-duplicated, prioritized list
of plain-English recommendations for the "Final Recommendations" section of
the dashboard. Individual risk-level recommendations already live inside
risk_engine.RISK_PATTERNS; this module aggregates and prioritizes them.
"""
from __future__ import annotations

from typing import List, Dict

LEVEL_PRIORITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

GENERAL_RECOMMENDATIONS = [
    "Have a qualified legal professional review this contract before signing.",
    "Keep a signed copy of the final agreement along with all amendments.",
    "Clarify any ambiguous terms in writing with the other party before execution.",
]


def generate_recommendations(risks: List[Dict], risk_level: str) -> List[str]:
    """
    Build an ordered, de-duplicated recommendation list:
      1. One recommendation per unique risk, ordered by severity
      2. A general recommendation about overall risk level
      3. Standard boilerplate recommendations
    """
    sorted_risks = sorted(risks, key=lambda r: LEVEL_PRIORITY.get(r["risk_level"], 4))

    seen = set()
    recommendations: List[str] = []

    for risk in sorted_risks:
        rec = risk.get("recommendation")
        if rec and rec not in seen:
            recommendations.append(rec)
            seen.add(rec)

    overall_message = {
        "CRITICAL": "This contract carries CRITICAL overall risk. Do not sign without a full legal review and renegotiation of flagged clauses.",
        "HIGH": "This contract carries HIGH overall risk. A legal review is strongly recommended before signing.",
        "MEDIUM": "This contract carries MODERATE risk. Review flagged clauses carefully and consider negotiating key terms.",
        "LOW": "This contract carries LOW overall risk based on the patterns detected, but a final read-through is still advised.",
    }.get(risk_level)

    if overall_message:
        recommendations.insert(0, overall_message)

    for rec in GENERAL_RECOMMENDATIONS:
        if rec not in seen:
            recommendations.append(rec)
            seen.add(rec)

    return recommendations
