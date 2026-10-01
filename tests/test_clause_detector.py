from app.services import clause_detector as cd


def _by_cat(clauses):
    return {c["category"]: c for c in clauses}


def test_returns_all_15_categories(sample_text):
    assert len(cd.detect_clauses(sample_text)) == 15


def test_known_confidentiality_clause(sample_text):
    c = _by_cat(cd.detect_clauses(sample_text))["confidentiality"]
    assert c["found"] and c["confidence"] > 0 and "confidential" in c["content"].lower()


def test_termination_clause(sample_text):
    c = _by_cat(cd.detect_clauses(sample_text))["termination"]
    assert c["found"] and "terminate" in c["content"].lower()


def test_payment_clause(sample_text):
    c = _by_cat(cd.detect_clauses(sample_text))["payment_terms"]
    assert c["found"] and c["start_index"] is not None


def test_missing_clause(sample_text):
    clauses = cd.detect_clauses(sample_text)
    c = _by_cat(clauses)["governing_law"]
    assert not c["found"] and c["risk_level"] == "NONE" and c["confidence"] == 0
    assert "Governing Law" in cd.get_missing_clauses(clauses)


def test_term_heading_does_not_hijack_termination_section():
    text = "1. TERMINATION\n\nEither party may terminate this agreement with notice.\n\n2. PAYMENT\n\nInvoices are due within 30 days.\n" * 2
    c = _by_cat(cd.detect_clauses(text))["contract_duration"]
    assert "terminate" not in c["content"].lower() or not c["found"]
