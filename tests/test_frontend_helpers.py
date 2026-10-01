import pytest
import requests

from streamlit_app import api_client
from streamlit_app.components.text_viewer import build_highlighted_html


class Resp:
    def __init__(self, status, body=None):
        self.status_code, self._body, self.content = status, body, b"x"
        self.ok = status < 400

    def json(self):
        if self._body is None:
            raise ValueError
        return self._body


@pytest.mark.parametrize("status,body,expect", [
    (400, {"detail": "Invalid file type '.exe'."}, "Invalid file type"),
    (404, None, "could not be found"),
    (413, {"detail": "File too large"}, "too large"),
    (500, None, "unexpected problem"),
])
def test_http_errors_become_friendly(monkeypatch, status, body, expect):
    monkeypatch.setattr(requests, "request", lambda *a, **k: Resp(status, body))
    with pytest.raises(api_client.ApiError) as exc:
        api_client.get_contract("contract_aaaaaaaaaaaa")
    assert expect in exc.value.message and exc.value.status_code == status


def test_connection_and_timeout_errors(monkeypatch):
    def conn(*a, **k): raise requests.exceptions.ConnectionError()
    def slow(*a, **k): raise requests.exceptions.Timeout()
    monkeypatch.setattr(requests, "request", conn)
    with pytest.raises(api_client.ApiError, match="Cannot reach"):
        api_client.get_contracts()
    monkeypatch.setattr(requests, "request", slow)
    with pytest.raises(api_client.ApiError, match="too long"):
        api_client.get_contracts()
    monkeypatch.setattr(requests, "get", conn)
    assert api_client.check_health() is False


def test_highlighter_escapes_html_and_skips_overlaps():
    text = "A <script>alert(1)</script> B clause"
    out = build_highlighted_html(text, [(2, 10, "risk"), (5, 12, "risk")])
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert out.count("<mark") == 1
