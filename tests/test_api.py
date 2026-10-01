import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _upload(name, data, mime="application/octet-stream"):
    return client.post("/api/analyze", files={"file": (name, data, mime)})


@pytest.fixture
def analyzed(sample_text):
    r = _upload("sample.txt", sample_text.encode(), "text/plain")
    assert r.status_code == 200, r.text
    return r.json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "healthy", "service": "AI Contract Risk Analyzer"}
    assert client.get("/api/health").status_code == 200


def test_docs_available():
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/health", "/api/analyze", "/api/contracts", "/api/contracts/{contract_id}", "/api/contracts/{contract_id}/report"):
        assert p in paths


def test_config_exposes_thresholds():
    r = client.get("/api/config").json()
    assert r["max_file_size_mb"] == 10
    assert [(t["level"], t["min_score"], t["max_score"]) for t in r["risk_thresholds"]] == [
        ("LOW", 0, 25), ("MEDIUM", 26, 50), ("HIGH", 51, 75), ("CRITICAL", 76, 100)]


def test_upload_txt(analyzed):
    assert analyzed["risk_score"] == 77 and analyzed["risk_level"] == "CRITICAL"
    assert analyzed["summary_mode"] == "local"          # no API key -> local fallback
    assert analyzed["details"]["parties"] == ["Northbridge Consulting LLC", "Alex Rivera"]
    assert len(analyzed["clauses"]) == 15 and analyzed["statistics"]["risks_found"] == 7


def test_upload_pdf_and_docx(make_pdf, make_docx, sample_text):
    for path, mime in ((make_pdf(sample_text), "application/pdf"), (make_docx(sample_text), "application/octet-stream")):
        r = _upload(path.name, path.read_bytes(), mime)
        assert r.status_code == 200, r.text
        assert r.json()["risk_level"] in ("HIGH", "CRITICAL")


def test_retrieve_history_delete(analyzed):
    cid = analyzed["contract_id"]
    assert client.get(f"/api/contracts/{cid}").json()["contract_id"] == cid
    assert [h["contract_id"] for h in client.get("/api/contracts").json()] == [cid]
    d = client.delete(f"/api/contracts/{cid}")
    assert d.status_code == 200 and d.json() == {"deleted": True, "contract_id": cid}
    assert client.get(f"/api/contracts/{cid}").status_code == 404
    assert client.delete(f"/api/contracts/{cid}").status_code == 404
    assert client.get("/api/contracts").json() == []


def test_report(analyzed):
    cid = analyzed["contract_id"]
    r = client.get(f"/api/contracts/{cid}/report")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert f"contract_risk_report_{cid}.pdf" in r.headers["content-disposition"]


def test_error_codes(sample_text):
    assert _upload("evil.exe", b"MZ....").status_code == 400
    assert _upload("empty.txt", b"").status_code == 400
    assert _upload("fake.pdf", b"not really a pdf").status_code == 400          # signature check
    assert _upload("short.txt", b"tiny").status_code == 422
    assert client.get("/api/contracts/contract_000000000000").status_code == 404
    assert client.get("/api/contracts/contract_000000000000/report").status_code == 404


def test_too_large_is_413(monkeypatch, sample_text):
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
    r = _upload("big.txt", b"a" * (1024 * 1024 + 10))
    assert r.status_code == 413 and "too large" in r.json()["detail"].lower()


def test_path_traversal_ids_rejected():
    for bad in ("..%2F..%2Fetc%2Fpasswd", "contract_../x", "x"):
        assert client.get(f"/api/contracts/{bad}").status_code in (404, 405)
        assert client.delete(f"/api/contracts/{bad}").status_code in (404, 405)


def test_uploaded_file_removed_and_name_not_trusted(analyzed, isolated_storage):
    assert list((isolated_storage / "uploads").glob("*")) == []
    r = _upload("../../evil.txt", (b"This Agreement is between A Corp and B Corp. " * 3), "text/plain")
    assert r.status_code == 200 and r.json()["file_name"] == "evil.txt"


def test_no_stack_trace_leak(monkeypatch, sample_text):
    from app.services import clause_detector

    def boom(_):
        raise RuntimeError("secret internal path /srv/x")

    monkeypatch.setattr(clause_detector, "detect_clauses", boom)
    r = _upload("s.txt", sample_text.encode())
    assert r.status_code == 500 and "secret" not in r.text and "Traceback" not in r.text


def test_ai_summary_used_when_available(monkeypatch, sample_text):
    from app.services import summarizer

    async def fake_ai(_text):
        return "AI generated summary."

    monkeypatch.setattr(summarizer, "ai_summary", fake_ai)
    r = _upload("s.txt", sample_text.encode())
    assert r.json()["summary"] == "AI generated summary." and r.json()["summary_mode"] == "ai"


def test_ai_failure_falls_back_to_local(monkeypatch, sample_text):
    # Key configured but endpoint unreachable -> must silently use the local summarizer.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9/v1")
    r = _upload("s.txt", sample_text.encode())
    assert r.status_code == 200 and r.json()["summary_mode"] == "local" and r.json()["summary"]
