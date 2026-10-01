"""
clause_detector.py

Rule-based clause classification engine. Works without any paid AI API by
combining:
  * keyword / phrase matching
  * regex patterns
  * heading detection (from text_preprocessor.detect_sections)
  * simple confidence scoring based on match density

For each of the 15 target clause categories we keep a list of keywords and
optional heading aliases. A clause is considered "found" if enough
signal is present in a section, or anywhere in the document as a fallback.
"""
from __future__ import annotations

import re
from typing import List, Dict, Optional

from app.services.text_preprocessor import detect_sections, find_context_window

# ---------------------------------------------------------------------------
# Clause definitions
# ---------------------------------------------------------------------------
# Each entry: category key -> {
#   "display_name": str,
#   "heading_aliases": [regex-friendly strings that indicate a heading match],
#   "keywords": [phrases scored when found in body text],
#   "base_risk": default risk level if clause exists with no specific risk pattern triggered
# }

CLAUSE_DEFINITIONS: Dict[str, Dict] = {
    "confidentiality": {
        "display_name": "Confidentiality",
        "heading_aliases": ["confidential", "confidentiality", "non-disclosure", "nda"],
        "keywords": [
            "confidential information", "confidentiality", "non-disclosure",
            "proprietary information", "shall not disclose", "keep confidential",
            "trade secret",
        ],
        "base_risk": "LOW",
    },
    "payment_terms": {
        "display_name": "Payment Terms",
        "heading_aliases": ["payment", "payments", "compensation", "fees"],
        "keywords": [
            "payment terms", "payment schedule", "invoice", "due date",
            "shall pay", "compensation", "amount payable", "payment of",
            "fees", "remuneration",
        ],
        "base_risk": "LOW",
    },
    "termination": {
        "display_name": "Termination",
        "heading_aliases": ["termination", "cancellation"],
        "keywords": [
            "termination", "terminate", "termination clause", "notice period",
            "cancel agreement", "breach", "terminate this agreement",
            "right to terminate",
        ],
        "base_risk": "MEDIUM",
    },
    "liability": {
        "display_name": "Liability",
        "heading_aliases": ["liability", "limitation of liability"],
        "keywords": [
            "liability", "liable for", "limitation of liability",
            "consequential damages", "direct damages", "loss or damage",
        ],
        "base_risk": "MEDIUM",
    },
    "indemnification": {
        "display_name": "Indemnification",
        "heading_aliases": ["indemnification", "indemnity"],
        "keywords": [
            "indemnify", "indemnification", "hold harmless", "defend and indemnify",
            "indemnify and hold harmless",
        ],
        "base_risk": "MEDIUM",
    },
    "non_compete": {
        "display_name": "Non-Compete",
        "heading_aliases": ["non-compete", "non compete", "restrictive covenant"],
        "keywords": [
            "non-compete", "shall not compete", "restricted from working",
            "competing business", "non-solicitation", "restraint of trade",
        ],
        "base_risk": "MEDIUM",
    },
    "intellectual_property": {
        "display_name": "Intellectual Property",
        "heading_aliases": ["intellectual property", "ip rights", "ownership"],
        "keywords": [
            "intellectual property", "copyright", "patent", "trademark",
            "work product", "ownership of", "assigns all right, title",
        ],
        "base_risk": "LOW",
    },
    "data_privacy": {
        "display_name": "Data Privacy",
        "heading_aliases": ["data privacy", "data protection", "gdpr"],
        "keywords": [
            "data privacy", "personal data", "data protection", "gdpr",
            "data processing", "privacy policy", "personally identifiable information",
        ],
        "base_risk": "LOW",
    },
    "governing_law": {
        "display_name": "Governing Law",
        "heading_aliases": ["governing law", "applicable law", "jurisdiction"],
        "keywords": [
            "governing law", "governed by the laws of", "applicable law",
            "jurisdiction of the courts",
        ],
        "base_risk": "LOW",
    },
    "dispute_resolution": {
        "display_name": "Dispute Resolution",
        "heading_aliases": ["dispute resolution", "arbitration", "mediation"],
        "keywords": [
            "dispute resolution", "arbitration", "mediation", "resolve any dispute",
            "binding arbitration",
        ],
        "base_risk": "LOW",
    },
    "contract_duration": {
        "display_name": "Contract Duration",
        "heading_aliases": ["term", "duration", "contract period"],
        "keywords": [
            "term of this agreement", "effective date", "duration of this agreement",
            "shall remain in effect", "contract period",
        ],
        "base_risk": "LOW",
    },
    "renewal": {
        "display_name": "Renewal",
        "heading_aliases": ["renewal", "extension"],
        "keywords": [
            "automatically renew", "renewal term", "extend this agreement",
            "renew for successive", "auto-renewal",
        ],
        "base_risk": "LOW",
    },
    "force_majeure": {
        "display_name": "Force Majeure",
        "heading_aliases": ["force majeure", "act of god"],
        "keywords": [
            "force majeure", "act of god", "beyond its reasonable control",
            "natural disaster", "pandemic",
        ],
        "base_risk": "LOW",
    },
    "warranties": {
        "display_name": "Warranties",
        "heading_aliases": ["warranties", "warranty", "representations"],
        "keywords": [
            "warranties", "warrants that", "representations and warranties",
            "as is", "no warranty", "disclaims all warranties",
        ],
        "base_risk": "LOW",
    },
    "obligations": {
        "display_name": "Obligations",
        "heading_aliases": ["obligations", "responsibilities", "duties"],
        "keywords": [
            "obligations", "shall be responsible for", "duties of the parties",
            "responsibilities of each party",
        ],
        "base_risk": "LOW",
    },
}

CATEGORY_ORDER = list(CLAUSE_DEFINITIONS.keys())


def _alias_in_heading(alias: str, heading_lower: str) -> bool:
    """Whole-word match, so the alias 'term' does not match a 'Termination' heading."""
    return re.search(rf"\b{re.escape(alias)}\b", heading_lower) is not None


def _score_keywords(text_lower: str, keywords: List[str]) -> (int, List[str]):
    """Count distinct keyword hits and return (hits, matched_keywords)."""
    matched = []
    for kw in keywords:
        if kw in text_lower:
            matched.append(kw)
    return len(matched), matched


def _confidence_from_hits(hits: int, heading_matched: bool) -> int:
    base = 40 if heading_matched else 20
    confidence = base + min(hits, 6) * 10
    return min(confidence, 98)


def detect_clauses(text: str) -> List[Dict]:
    """
    Scan the full contract text and return a list of clause dicts (one per
    CLAUSE_DEFINITIONS entry, whether found or not) so the frontend can show
    both present and missing clauses.
    """
    text_lower = text.lower()
    sections = detect_sections(text)

    results = []

    for category, definition in CLAUSE_DEFINITIONS.items():
        heading_matched_section = None

        # 1) Try to find a section whose heading matches an alias
        for section in sections:
            heading_lower = (section["heading"] or "").lower()
            if any(_alias_in_heading(alias, heading_lower) for alias in definition["heading_aliases"]):
                heading_matched_section = section
                break

        if heading_matched_section:
            content = heading_matched_section["content"] or heading_matched_section["heading"]
            hits, matched_kw = _score_keywords(content.lower(), definition["keywords"])
            confidence = _confidence_from_hits(max(hits, 1), heading_matched=True)
            start_index = heading_matched_section["start_index"]
            snippet = content.strip()[:600]
            found = True
        else:
            # 2) Fallback: search keywords across the whole document
            hits, matched_kw = _score_keywords(text_lower, definition["keywords"])
            if hits == 0:
                results.append(
                    {
                        "clause_name": definition["display_name"],
                        "category": category,
                        "content": "",
                        "risk_level": "NONE",
                        "confidence": 0,
                        "explanation": (
                            f"No '{definition['display_name']}' clause was clearly detected in "
                            f"this document. Consider adding one for completeness."
                        ),
                        "found": False,
                        "start_index": None,
                        "end_index": None,
                    }
                )
                continue

            # locate first keyword occurrence for a text snippet
            first_kw = matched_kw[0]
            idx = text_lower.find(first_kw)
            snippet = find_context_window(text, idx, window=250)
            confidence = _confidence_from_hits(hits, heading_matched=False)
            start_index = idx
            found = True

        risk_level = definition["base_risk"]
        explanation = (
            f"Detected based on {len(matched_kw)} matching keyword(s)"
            + (f" including '{matched_kw[0]}'" if matched_kw else "")
            + f". Classified under the {definition['display_name']} category."
        )

        results.append(
            {
                "clause_name": definition["display_name"],
                "category": category,
                "content": snippet,
                "risk_level": risk_level,
                "confidence": confidence,
                "explanation": explanation,
                "found": found,
                "start_index": start_index,
                "end_index": (start_index + len(snippet)) if start_index is not None else None,
            }
        )

    return results


def get_missing_clauses(clauses: List[Dict]) -> List[str]:
    return [c["clause_name"] for c in clauses if not c.get("found")]
