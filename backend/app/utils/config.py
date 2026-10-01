"""
config.py

Central place for backend settings. Values are read from environment
variables (a `.env` file in the project root is loaded automatically) and
evaluated lazily, so tests can override them with monkeypatch.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

SERVICE_NAME = "AI Contract Risk Analyzer"
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt")


def max_file_size_mb() -> int:
    try:
        return max(1, int(os.getenv("MAX_FILE_SIZE_MB", "10")))
    except ValueError:
        return 10


def max_file_size_bytes() -> int:
    return max_file_size_mb() * 1024 * 1024


def data_dir() -> Path:
    """Directory that holds stored analyses (JSON). Lives outside the source tree."""
    path = Path(os.getenv("DATA_DIR") or PROJECT_ROOT / "data" / "contracts")
    path.mkdir(parents=True, exist_ok=True)
    return path


def upload_dir() -> Path:
    """Temporary upload directory (files are deleted right after processing)."""
    path = Path(os.getenv("UPLOAD_DIR") or PROJECT_ROOT / "data" / "uploads")
    path.mkdir(parents=True, exist_ok=True)
    return path


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
    return [o.strip() for o in raw.split(",") if o.strip()]
