"""
contract_details.py

Best-effort extraction of headline facts (parties, duration, dates, payment,
obligations, termination) using regular expressions. Anything that cannot be
found is returned as None / an empty list; the frontend shows "Not detected".
Nothing is inferred or invented.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.services.text_preprocessor import split_sentences, strip_leading_heading

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(
    rf"\b(?:(?:{_MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}"
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS}),?\s+\d{{4}}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}/\d{1,2}/\d{4})\b",
    re.IGNORECASE,
)
PARTIES_RE = re.compile(
    r"(?:by and )?between\s+(?P<a>[^,(]{3,80}?)\s*(?:\([^)]*\))?\s*,?[^,]{0,80}?,?\s+and\s+(?P<b>[^,(.]{3,80}?)\s*(?:\(|,|\.)",
    re.IGNORECASE | re.DOTALL,
)
_SPAN = r"((?:\w+\s+\(\d+\)|\d+|\w+)\s+(?:year|month|week|day)s?(?:\s*\(\d+\))?)"
# Deliberately strict: only phrases that describe the term of the contract itself,
# so periods that belong to confidentiality / non-compete clauses are not mistaken for it.
DURATION_RES = [
    re.compile(r"\binitial term of\s+" + _SPAN, re.IGNORECASE),
    re.compile(r"\bterm of this (?:agreement|contract) (?:shall be|is|will be)\s+(?:a period of\s+)?" + _SPAN, re.IGNORECASE),
    re.compile(r"\bthis (?:agreement|contract) (?:shall|will) (?:remain in (?:effect|force)|continue|be effective)[^.]{0,40}?\bfor\s+(?:a (?:period|term) of\s+)?" + _SPAN, re.IGNORECASE),
]
AMOUNT_RE = re.compile(r"(?:[$€£₹]\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:USD|INR|EUR|GBP|dollars|rupees)\b)", re.IGNORECASE)


def _clean(sentence: str, limit: int = 300) -> str:
    sentence = re.sub(r"\s+", " ", sentence).strip()
    sentence = strip_leading_heading(sentence)  # drop a merged ALL-CAPS section heading
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rstrip() + "…"


def _sentences_matching(sentences: List[str], pattern: str, limit: int) -> List[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    out: List[str] = []
    for s in sentences:
        if regex.search(s) and len(s.split()) >= 5:
            cleaned = _clean(s)
            if cleaned not in out:
                out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _parties(text: str) -> List[str]:
    head = re.sub(r"\s+", " ", text[:1500])
    m = PARTIES_RE.search(head)
    if not m:
        return []
    return [re.sub(r"\s+", " ", m.group(k)).strip(" ,\"'") for k in ("a", "b")]


def _duration(text: str) -> Optional[str]:
    flat = re.sub(r"\s+", " ", text)
    for regex in DURATION_RES:
        m = regex.search(flat)
        if m:
            return _clean(m.group(1), 80)
    return None


def _dates(text: str, limit: int = 8) -> List[str]:
    seen: List[str] = []
    for m in DATE_RE.finditer(text):
        value = m.group(0)
        if value not in seen:
            seen.append(value)
        if len(seen) >= limit:
            break
    return seen


def extract_contract_details(text: str, clauses: List[Dict]) -> Dict:
    sentences = split_sentences(text)
    payment = _sentences_matching(sentences, r"\b(pay|payment|fee|fees|invoice|compensation|remuneration)\b", 6)
    # Prefer sentences that actually state an amount; otherwise fall back to the first payment sentences.
    with_amount = [s for s in payment if AMOUNT_RE.search(s)]
    payment_terms = (with_amount or payment)[:2]

    return {
        "parties": _parties(text),
        "duration": _duration(text),
        "important_dates": _dates(text),
        "payment_terms": payment_terms,
        "obligations": _sentences_matching(sentences, r"\b(shall be responsible for|agrees to provide|shall (?:deliver|provide|perform)|obligated to)\b", 4),
        "termination_conditions": _sentences_matching(
            sentences, r"(?=.*\b(?:terminate|terminated|terminates|termination)\b)(?=.*\b(?:may|right|notice|upon|breach|cause|convenience)\b)", 3
        ),
        # Only categories the clause detector actually found are listed here.
        "key_provisions": [c["clause_name"] for c in clauses if c.get("found")],
    }
