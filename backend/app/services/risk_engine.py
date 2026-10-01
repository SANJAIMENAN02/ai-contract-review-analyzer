"""
risk_engine.py

Rule-based risk detection engine. Scans contract text for known risky
language patterns (regex based, case-insensitive), assigns a severity to
each finding, and computes an overall 0-100 risk score plus a category
breakdown.

This module intentionally does NOT depend on any external AI API so the
project runs fully offline. See summarizer.py for the optional LLM hook.
"""
from __future__ import annotations

import re
import uuid
from typing import List, Dict, Tuple

from app.services.text_preprocessor import find_context_window

RISK_LEVEL_POINTS = {
    "LOW": 5,
    "MEDIUM": 12,
    "HIGH": 20,
    "CRITICAL": 30,
}

RISK_LEVEL_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Upper bound (inclusive) of each level on the 0-100 score. Single source of
# truth: exposed through GET /api/config so the frontend never hard-codes its own.
RISK_THRESHOLDS = [("LOW", 25), ("MEDIUM", 50), ("HIGH", 75), ("CRITICAL", 100)]


def level_for_score(score: int) -> str:
    for level, upper in RISK_THRESHOLDS:
        if score <= upper:
            return level
    return "CRITICAL"


# ---------------------------------------------------------------------------
# Risk pattern library
# ---------------------------------------------------------------------------
# Each pattern: id, title, category, level, regex (compiled lazily), description, recommendation
RISK_PATTERNS = [
    {
        "id": "unlimited_liability",
        "title": "Unlimited Liability",
        "category": "liability_risk",
        "level": "HIGH",
        "pattern": r"(unlimited liability|liable for all damages|without limitation[,]? (?:be )?liable|no limitation (?:on|of) liability|liability shall not be limited)",
        "description": (
            "The contract contains language that may expose one party to unlimited "
            "financial liability, with no cap on the damages that could be claimed."
        ),
        "recommendation": "Consider negotiating a reasonable liability cap to limit financial exposure.",
    },
    {
        "id": "immediate_termination",
        "title": "Immediate Termination Without Notice",
        "category": "termination_risk",
        "level": "HIGH",
        "pattern": r"(terminate(?:d|s)?\s+immediately|without prior notice|without (?:any )?notice|terminate.{0,20}sole discretion|at (?:its|their|the company'?s) sole discretion)",
        "description": (
            "The contract allows termination immediately or without prior notice, "
            "giving one party little to no time to respond or find alternatives."
        ),
        "recommendation": "Consider requesting a reasonable notice period (e.g. 30 days) before termination takes effect.",
    },
    {
        "id": "one_sided_termination",
        "title": "One-Sided Termination Rights",
        "category": "termination_risk",
        "level": "HIGH",
        "pattern": r"(only the (?:company|client|employer|licensor) may terminate|right to terminate.{0,40}(?:sole|exclusive)|may terminate this agreement at any time for any reason)",
        "description": (
            "The termination clause appears to grant termination rights primarily "
            "or exclusively to one party, creating an imbalance of power."
        ),
        "recommendation": "Negotiate mutual termination rights so both parties can exit the agreement under similar conditions.",
    },
    {
        "id": "broad_indemnification",
        "title": "Broad Indemnification",
        "category": "liability_risk",
        "level": "HIGH",
        "pattern": r"(indemnify and hold harmless from any and all claims|indemnify.{0,30}any and all (?:claims|losses|damages|liabilities)|defend, indemnify,? and hold harmless)",
        "description": (
            "The indemnification clause is broadly worded to cover 'any and all' "
            "claims, which may require one party to cover losses far beyond what "
            "is reasonable or foreseeable."
        ),
        "recommendation": "Narrow the indemnification scope to claims directly caused by breach, negligence, or misconduct.",
    },
    {
        "id": "aggressive_non_compete",
        "title": "Aggressive Non-Compete Restriction",
        "category": "other_risk",
        "level": "MEDIUM",
        "pattern": r"(shall not compete|restricted from working|non-compete.{0,40}(?:\d+\s*(?:year|month)s?)|for a period of (?:[3-9]|[1-9]\d)\s*years?)",
        "description": (
            "The contract includes a non-compete restriction that may be broad in "
            "scope or duration, potentially limiting future employment or business "
            "opportunities."
        ),
        "recommendation": "Review the geographic scope and duration of the non-compete clause and negotiate reasonable limits.",
    },
    {
        "id": "unclear_payment_terms",
        "title": "Unclear Payment Terms",
        "category": "payment_risk",
        "level": "MEDIUM",
        # This is evaluated programmatically (see check_unclear_payment_terms) rather than by simple regex
        "pattern": None,
        "description": (
            "Payment obligations are mentioned but the contract does not clearly "
            "specify an amount, currency, due date, or payment schedule."
        ),
        "recommendation": "Clarify exact payment amounts, currency, due dates, and the payment schedule in the contract.",
    },
    {
        "id": "auto_renewal_lockin",
        "title": "Automatic Renewal / Lock-In",
        "category": "termination_risk",
        "level": "MEDIUM",
        "pattern": r"(automatically renew|auto-renewal|shall automatically extend|renew for successive (?:periods|terms))",
        "description": (
            "The agreement automatically renews unless action is taken, which can "
            "lock a party into unwanted extended terms if a cancellation deadline is missed."
        ),
        "recommendation": "Track renewal deadlines carefully, or negotiate for renewal to require affirmative written consent.",
    },
    {
        "id": "unilateral_amendment",
        "title": "Unilateral Right to Amend",
        "category": "other_risk",
        "level": "MEDIUM",
        "pattern": r"(may (?:amend|modify|change) this agreement at any time|reserves the right to (?:amend|modify|change) .{0,40}without (?:notice|consent))",
        "description": (
            "One party may be able to unilaterally amend or modify contract terms, "
            "potentially without requiring the other party's consent."
        ),
        "recommendation": "Require that any amendments be made in writing and signed by both parties.",
    },
    {
        "id": "penalty_clause",
        "title": "Penalty / Liquidated Damages Clause",
        "category": "payment_risk",
        "level": "MEDIUM",
        "pattern": r"(liquidated damages|penalty (?:of|equal to|fee)|shall pay a penalty)",
        "description": (
            "The contract includes a penalty or liquidated damages clause that "
            "could impose significant costs for breach or delay."
        ),
        "recommendation": "Verify the penalty amount is proportionate and negotiate a cap where possible.",
    },
    {
        "id": "confidentiality_indefinite",
        "title": "Indefinite Confidentiality Obligation",
        "category": "confidentiality_risk",
        "level": "LOW",
        "pattern": r"(confidentiality obligations? shall survive indefinitely|in perpetuity|shall remain confidential forever)",
        "description": (
            "The confidentiality obligation has no defined end date, which may be "
            "overly broad and difficult to comply with long-term."
        ),
        "recommendation": "Consider negotiating a defined confidentiality period (e.g. 3-5 years post-termination).",
    },
    {
        "id": "waiver_of_rights",
        "title": "Broad Waiver of Rights",
        "category": "other_risk",
        "level": "MEDIUM",
        "pattern": r"(waives? (?:any and )?all rights|hereby waives? the right to)",
        "description": (
            "The contract asks one party to waive certain legal rights, which "
            "could limit their ability to seek remedies later."
        ),
        "recommendation": "Carefully review what rights are being waived and whether the waiver is reasonable and necessary.",
    },
]

REQUIRED_CLAUSE_CATEGORIES = {
    "governing_law": "Governing Law",
    "termination": "Termination",
    "confidentiality": "Confidentiality",
    "liability": "Liability",
}


def _compile(pattern: str):
    return re.compile(pattern, re.IGNORECASE)


def _new_risk_id() -> str:
    return f"risk_{uuid.uuid4().hex[:10]}"


def check_unclear_payment_terms(text: str) -> Dict | None:
    """
    Programmatic check: if payment-related language is present but no
    currency symbol / amount / explicit due-date language is found nearby,
    flag it as an unclear payment risk.
    """
    text_lower = text.lower()
    payment_signals = ["payment", "compensation", "fees", "invoice", "remuneration"]
    if not any(sig in text_lower for sig in payment_signals):
        return None

    has_amount = bool(re.search(r"(\$|₹|€|£|usd|inr|eur|gbp)\s?\d|\d+(\.\d+)?\s?(usd|inr|dollars|rupees)", text_lower))
    has_due_date = bool(re.search(r"(due (?:date|within|on)|net\s?\d+|within \d+ days|payment schedule)", text_lower))

    if has_amount and has_due_date:
        return None  # payment terms look sufficiently specified

    idx = text_lower.find("payment")
    if idx == -1:
        idx = 0
    snippet = find_context_window(text, idx, window=200)

    pattern_def = next(p for p in RISK_PATTERNS if p["id"] == "unclear_payment_terms")
    return {
        "risk_id": _new_risk_id(),
        "risk_title": pattern_def["title"],
        "risk_level": pattern_def["level"],
        "category": pattern_def["category"],
        "description": pattern_def["description"],
        "recommendation": pattern_def["recommendation"],
        "matched_text": snippet,
        "start_index": idx,
        "end_index": idx + len("payment"),
    }


def check_missing_clauses(clauses: List[Dict]) -> List[Dict]:
    """Generate risk entries for critical clauses that were not detected."""
    found_categories = {c["category"] for c in clauses if c.get("found")}
    risks = []
    for category, display_name in REQUIRED_CLAUSE_CATEGORIES.items():
        if category not in found_categories:
            risks.append(
                {
                    "risk_id": _new_risk_id(),
                    "risk_title": f"Missing {display_name} Clause",
                    "risk_level": "MEDIUM",
                    "category": "compliance_risk",
                    "description": (
                        f"No clear '{display_name}' clause was detected in this contract. "
                        f"Its absence can create ambiguity and legal exposure."
                    ),
                    "recommendation": f"Add a clearly defined {display_name} clause to the contract.",
                    "matched_text": None,
                    "start_index": None,
                    "end_index": None,
                }
            )
    return risks


def detect_risks(text: str, clauses: List[Dict]) -> List[Dict]:
    """Run all regex-based and programmatic risk checks over the contract text."""
    risks: List[Dict] = []
    text_lower_len = len(text)

    for pattern_def in RISK_PATTERNS:
        if pattern_def["pattern"] is None:
            continue  # handled by a dedicated programmatic check below
        regex = _compile(pattern_def["pattern"])
        match = regex.search(text)
        if match:
            start = match.start()
            snippet = find_context_window(text, start, window=180)
            risks.append(
                {
                    "risk_id": _new_risk_id(),
                    "risk_title": pattern_def["title"],
                    "risk_level": pattern_def["level"],
                    "category": pattern_def["category"],
                    "description": pattern_def["description"],
                    "recommendation": pattern_def["recommendation"],
                    "matched_text": snippet,
                    "start_index": start,
                    "end_index": min(match.end(), text_lower_len),  # exact matched span, used for highlighting
                }
            )

    payment_risk = check_unclear_payment_terms(text)
    if payment_risk:
        risks.append(payment_risk)

    risks.extend(check_missing_clauses(clauses))

    return risks


def calculate_risk_score(risks: List[Dict]) -> Tuple[int, str, Dict]:
    """
    Compute an overall 0-100 risk score from individual risk findings, plus
    a category breakdown for the dashboard charts.
    """
    breakdown = {
        "termination_risk": 0,
        "liability_risk": 0,
        "payment_risk": 0,
        "compliance_risk": 0,
        "confidentiality_risk": 0,
        "other_risk": 0,
    }

    raw_total = 0
    for risk in risks:
        points = RISK_LEVEL_POINTS.get(risk["risk_level"], 5)
        raw_total += points
        category = risk.get("category", "other_risk")
        if category in breakdown:
            breakdown[category] += points
        else:
            breakdown["other_risk"] += points

    # Normalize: cap contribution so a huge number of low risks doesn't
    # unfairly dominate over a couple of critical ones. We use a soft cap
    # of 140 raw points -> 100 score, with diminishing returns beyond that.
    max_raw_for_100 = 140
    normalized = round((raw_total / max_raw_for_100) * 100) if max_raw_for_100 else 0
    risk_score = max(0, min(100, normalized))

    # Normalize breakdown into 0-100-ish relative values too (for the bar chart)
    breakdown_normalized = {
        key: min(100, round((value / max_raw_for_100) * 100)) for key, value in breakdown.items()
    }

    risk_level = level_for_score(risk_score)

    return risk_score, risk_level, breakdown_normalized


def count_by_level(risks: List[Dict]) -> Dict[str, int]:
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for risk in risks:
        level = risk.get("risk_level", "LOW")
        if level in counts:
            counts[level] += 1
    return counts
