import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

# Tests must never need Mongo or an external AI API.
os.environ.pop("MONGO_URI", None)
os.environ.pop("OPENAI_API_KEY", None)

import pytest  # noqa: E402

SAMPLES = ROOT / "sample_contracts"


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "contracts"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    yield tmp_path


@pytest.fixture
def sample_text():
    return (SAMPLES / "sample_contract.txt").read_text(encoding="utf-8")


@pytest.fixture
def make_pdf(tmp_path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    def _make(text: str, name: str = "c.pdf"):
        path = tmp_path / name
        pdf = canvas.Canvas(str(path), pagesize=A4)
        y = 800
        for line in text.split("\n"):
            pdf.drawString(40, y, line[:110])
            y -= 14
            if y < 40:
                pdf.showPage()
                y = 800
        pdf.save()
        return path

    return _make


@pytest.fixture
def make_docx(tmp_path):
    import docx

    def _make(text: str, name: str = "c.docx"):
        path = tmp_path / name
        d = docx.Document()
        for para in text.split("\n"):
            d.add_paragraph(para)
        d.save(str(path))
        return path

    return _make
