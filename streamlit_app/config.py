"""Frontend settings. The API URL comes from the environment (or .env), never from code."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

APP_NAME = "AI Contract Risk Analyzer"
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
HEALTH_TIMEOUT = 2.0
REQUEST_TIMEOUT = float(os.getenv("API_TIMEOUT_SECONDS", "30"))
ANALYZE_TIMEOUT = float(os.getenv("API_ANALYZE_TIMEOUT_SECONDS", "120"))
STYLES_PATH = Path(__file__).resolve().parent / "styles" / "custom.css"

DISCLAIMER = (
    "Automated analysis for review assistance only. It does not replace a qualified "
    "lawyer and is not legal advice."
)
