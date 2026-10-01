import pytest

from app.services import document_processor as dp


def test_valid_pdf(make_pdf, sample_text):
    path = make_pdf(sample_text)
    text = dp.extract_text(str(path), "c.pdf")
    assert "SERVICE AGREEMENT" in text and "TERMINATION" in text


def test_valid_docx(make_docx, sample_text):
    path = make_docx(sample_text)
    assert "Northbridge Consulting" in dp.extract_text(str(path), "c.docx")


def test_valid_txt(tmp_path, sample_text):
    path = tmp_path / "c.txt"
    path.write_text(sample_text, encoding="utf-8")
    assert "INDEMNIFICATION" in dp.extract_text(str(path), "c.txt")


def test_empty_document(tmp_path):
    path = tmp_path / "e.txt"
    path.write_text("   \n\n  ")
    with pytest.raises(dp.EmptyDocumentError):
        dp.extract_text(str(path), "e.txt")


def test_too_little_text(tmp_path):
    path = tmp_path / "s.txt"
    path.write_text("hi")
    with pytest.raises(dp.TextExtractionError):
        dp.extract_text(str(path), "s.txt")


def test_unsupported_file():
    with pytest.raises(dp.UnsupportedFileTypeError) as exc:
        dp.validate_file("malware.exe", 100)
    assert exc.value.status_code == 400


def test_zero_bytes_and_oversize(monkeypatch):
    with pytest.raises(dp.EmptyDocumentError):
        dp.validate_file("a.pdf", 0)
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
    with pytest.raises(dp.FileTooLargeError) as exc:
        dp.validate_file("a.pdf", 2 * 1024 * 1024)
    assert exc.value.status_code == 413


def test_signature_mismatch_rejected():
    with pytest.raises(dp.UnsupportedFileTypeError):
        dp.validate_content_signature("fake.pdf", b"MZ\x90\x00 not a pdf")
    with pytest.raises(dp.UnsupportedFileTypeError):
        dp.validate_content_signature("fake.docx", b"plain text")
    dp.validate_content_signature("ok.pdf", b"%PDF-1.7 ...")


def test_corrupted_docx(tmp_path):
    path = tmp_path / "bad.docx"
    path.write_bytes(b"PK\x03\x04 garbage")
    with pytest.raises(dp.TextExtractionError):
        dp.extract_text(str(path), "bad.docx")


def test_safe_filename_ignores_uploaded_name():
    assert dp.make_safe_filename("contract_abc", "../../etc/passwd.pdf") == "contract_abc.pdf"
