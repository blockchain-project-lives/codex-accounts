from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..store import auth_hash
from .models import AuthMaterial


ACCESS_KEYS = {"access_token", "id_token", "session_token", "authorization", "bearer", "api_key"}
REFRESH_KEYS = {"refresh_token"}


def extract_auth_material(account_id: str, auth_path: Path) -> AuthMaterial:
    raw_hash = auth_hash(auth_path)
    access_token = None
    refresh_token = None
    try:
        data = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        data = {}
    for key, value in walk_key_values(data):
        normalized = key.lower().replace("-", "_")
        if access_token is None and (normalized in ACCESS_KEYS or "access_token" in normalized or normalized == "token"):
            access_token = string_value(value)
        if refresh_token is None and (normalized in REFRESH_KEYS or "refresh_token" in normalized):
            refresh_token = string_value(value)
    return AuthMaterial(account_id=account_id, auth_path=auth_path, access_token=access_token, refresh_token=refresh_token, raw_auth_hash=raw_hash)


def walk_key_values(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key), child
            yield from walk_key_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_key_values(child)


def string_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
