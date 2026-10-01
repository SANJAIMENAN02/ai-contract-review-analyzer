from app.services import clause_detector as cd
from app.services import risk_engine as re_

LOW_RISK = """MASTER SERVICES AGREEMENT

This Agreement is made on 1 March 2025 between Acme Ltd and Beta Inc.

1. PAYMENT
Beta shall pay $5,000 per month, due within 30 days of invoice.

2. TERMINATION
Either party may terminate this Agreement with thirty (30) days written notice.

3. CONFIDENTIALITY
Each party shall keep confidential information confidential for two (2) years.

4. LIABILITY
Each party's liability is capped at the fees paid in the preceding twelve months.

5. GOVERNING LAW
This Agreement is governed by the laws of England and Wales.
"""


def _run(text):
    clauses = cd.detect_clauses(text)
    risks = re_.detect_risks(text, clauses)
    return risks, re_.calculate_risk_score(risks)


def test_low_risk_contract():
    risks, (score, level, _) = _run(LOW_RISK)
    assert level == "LOW" and score <= 25
    assert not [r for r in risks if r["risk_level"] in ("HIGH", "CRITICAL")]


def test_high_risk_pattern():
    text = LOW_RISK + "\nThe Company may terminate immediately and without prior notice.\nContractor shall have unlimited liability."
    risks, _ = _run(text)
    titles = {r["risk_title"] for r in risks}
    assert "Unlimited Liability" in titles and "Immediate Termination Without Notice" in titles


def test_multiple_patterns_and_sample_baseline(sample_text):
    risks, (score, level, breakdown) = _run(sample_text)
    # Baseline captured from the original backend before any changes.
    assert (score, level) == (77, "CRITICAL")
    assert sorted(r["risk_title"] for r in risks) == [
        "Aggressive Non-Compete Restriction", "Automatic Renewal / Lock-In", "Broad Indemnification",
        "Immediate Termination Without Notice", "Missing Governing Law Clause", "Unclear Payment Terms",
        "Unlimited Liability",
    ]
    assert breakdown["liability_risk"] == 29 and breakdown["termination_risk"] == 23


def test_deterministic_scores(sample_text):
    assert _run(sample_text)[1] == _run(sample_text)[1]


def test_thresholds_are_single_source_of_truth():
    assert [re_.level_for_score(s) for s in (0, 25, 26, 50, 51, 75, 76, 100)] == [
        "LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH", "HIGH", "CRITICAL", "CRITICAL"]


def test_highlight_span_is_exact_match(sample_text):
    risks, _ = _run(sample_text)
    r = next(x for x in risks if x["risk_title"] == "Unlimited Liability")
    assert "without limitation" in sample_text[r["start_index"]:r["end_index"]].lower() or \
        "unlimited" in sample_text[r["start_index"]:r["end_index"]].lower() or \
        "liable for all damages" in sample_text[r["start_index"]:r["end_index"]].lower()
