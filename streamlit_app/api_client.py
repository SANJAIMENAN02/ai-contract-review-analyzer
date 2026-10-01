"""
HTTP client for the FastAPI backend. This is the only module that talks to the
API; Streamlit pages never import backend code.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from streamlit_app import config


class ApiError(Exception):
    """An error already phrased for end users."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


_STATUS_FALLBACKS = {
    400: "The request was not valid. Please check the file and try again.",
    404: "That contract analysis could not be found. It may have been deleted.",
    413: "The file is too large for the server's upload limit.",
    422: "The document could not be read. It may be empty, scanned, or corrupted.",
    500: "The server hit an unexpected problem. Please try again.",
}


def _detail(response: requests.Response) -> Optional[str]:
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        return None
    return detail if isinstance(detail, str) and detail.strip() else None


def _request(method: str, path: str, timeout: Optional[float] = None, **kwargs) -> requests.Response:
    url = f"{config.API_BASE_URL}{path}"
    try:
        response = requests.request(method, url, timeout=timeout or config.REQUEST_TIMEOUT, **kwargs)
    except requests.exceptions.ConnectionError as exc:
        raise ApiError(
            f"Cannot reach the backend at {config.API_BASE_URL}. Make sure FastAPI is running."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise ApiError("The backend took too long to respond. Try again, or use a smaller file.") from exc
    except requests.exceptions.RequestException as exc:
        raise ApiError("A network error occurred while contacting the backend.") from exc

    if response.status_code >= 400:
        message = _detail(response) or _STATUS_FALLBACKS.get(
            response.status_code, f"Unexpected response from the backend (HTTP {response.status_code})."
        )
        raise ApiError(message, response.status_code)
    return response


def check_health() -> bool:
    """True only if GET /health answers with status 'healthy'."""
    try:
        response = requests.get(f"{config.API_BASE_URL}/health", timeout=config.HEALTH_TIMEOUT)
        return response.ok and response.json().get("status") == "healthy"
    except (requests.exceptions.RequestException, ValueError):
        return False


_config_cache: Dict[str, Any] = {"at": 0.0, "value": None}


def get_backend_config() -> Optional[Dict[str, Any]]:
    """Upload limits and risk thresholds from the backend (cached briefly). None if offline."""
    if _config_cache["value"] and time.time() - _config_cache["at"] < 30:
        return _config_cache["value"]
    try:
        value = _request("GET", "/api/config", timeout=config.HEALTH_TIMEOUT).json()
    except ApiError:
        return None
    _config_cache.update(at=time.time(), value=value)
    return value


def analyze_contract(file) -> Dict[str, Any]:
    """Upload a Streamlit UploadedFile (or any object with .name/.getvalue()) for analysis."""
    files = {"file": (file.name, file.getvalue(), getattr(file, "type", None) or "application/octet-stream")}
    return _request("POST", "/api/analyze", timeout=config.ANALYZE_TIMEOUT, files=files).json()


def get_contracts() -> List[Dict[str, Any]]:
    return _request("GET", "/api/contracts").json()


def get_contract(contract_id: str) -> Dict[str, Any]:
    return _request("GET", f"/api/contracts/{contract_id}").json()


def delete_contract(contract_id: str) -> bool:
    return bool(_request("DELETE", f"/api/contracts/{contract_id}").json().get("deleted"))


def download_report(contract_id: str) -> bytes:
    return _request("GET", f"/api/contracts/{contract_id}/report", timeout=config.ANALYZE_TIMEOUT).content
