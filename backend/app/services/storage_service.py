"""
storage_service.py

Persistence layer for contract analyses. Local JSON files by default (zero
config); MongoDB when MONGO_URI is set and reachable. The public functions
are identical either way, so nothing above this module knows which is used.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from app.utils import config

CONTRACT_ID_RE = re.compile(r"^contract_[a-f0-9]{12}$")


class StorageError(Exception):
    """Raised when reading or writing a stored analysis fails."""


_mongo_collection = None
if os.getenv("MONGO_URI"):
    try:
        from pymongo import MongoClient

        _client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=2000)
        _client.admin.command("ping")
        _mongo_collection = _client[os.getenv("MONGO_DB_NAME") or "contract_analyzer"]["contracts"]
        print("[storage_service] Connected to MongoDB.")
    except Exception as exc:  # noqa: BLE001
        print(f"[storage_service] MongoDB unavailable ({exc}); using local JSON storage.")
        _mongo_collection = None


def is_valid_contract_id(contract_id: str) -> bool:
    return bool(CONTRACT_ID_RE.match(contract_id or ""))


def _index_file() -> Path:
    return config.data_dir() / "index.json"


def _contract_file(contract_id: str) -> Path:
    # Path traversal guard: only ids we generated ourselves are accepted.
    if not is_valid_contract_id(contract_id):
        raise StorageError("Invalid contract id.")
    return config.data_dir() / f"{contract_id}.json"


def _load_index() -> List[Dict]:
    path = _index_file()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(index: List[Dict]) -> None:
    with open(_index_file(), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def save_contract(contract: Dict) -> None:
    """Persist a full contract analysis result."""
    try:
        if _mongo_collection is not None:
            _mongo_collection.update_one(
                {"contract_id": contract["contract_id"]}, {"$set": contract}, upsert=True
            )
            return
        with open(_contract_file(contract["contract_id"]), "w", encoding="utf-8") as f:
            json.dump(contract, f, indent=2)
        index = [c for c in _load_index() if c["contract_id"] != contract["contract_id"]]
        index.insert(
            0,
            {
                "contract_id": contract["contract_id"],
                "file_name": contract["file_name"],
                "upload_date": contract["upload_date"],
                "risk_score": contract["risk_score"],
                "risk_level": contract["risk_level"],
                "status": "Completed",
            },
        )
        _save_index(index)
    except StorageError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise StorageError("Could not store the analysis result.") from exc


def get_contract(contract_id: str) -> Optional[Dict]:
    if not is_valid_contract_id(contract_id):
        return None
    if _mongo_collection is not None:
        return _mongo_collection.find_one({"contract_id": contract_id}, {"_id": 0})
    path = _contract_file(contract_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise StorageError("The stored analysis could not be read.") from exc


def get_history() -> List[Dict]:
    if _mongo_collection is not None:
        docs = list(
            _mongo_collection.find(
                {},
                {"_id": 0, "contract_id": 1, "file_name": 1, "upload_date": 1, "risk_score": 1, "risk_level": 1},
            ).sort("upload_date", -1)
        )
        for d in docs:
            d["status"] = "Completed"
        return docs
    return _load_index()


def delete_contract(contract_id: str) -> bool:
    if not is_valid_contract_id(contract_id):
        return False
    if _mongo_collection is not None:
        return _mongo_collection.delete_one({"contract_id": contract_id}).deleted_count > 0
    path = _contract_file(contract_id)
    existed = path.exists()
    if existed:
        path.unlink()
    index = _load_index()
    new_index = [c for c in index if c["contract_id"] != contract_id]
    if len(new_index) != len(index):
        _save_index(new_index)
        existed = True
    return existed
