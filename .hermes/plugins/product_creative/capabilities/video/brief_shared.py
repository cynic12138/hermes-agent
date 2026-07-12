from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from ...common import read_json
from ...ports.runtime_repositories import artifacts

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))

def _state_hash(state: Dict[str, Any]) -> str:
    payload = json.dumps(state, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _resolve_artifact(base: Path, value: str, folders: List[str]) -> Path:
    if not value:
        raise ValueError("artifact id or path is required")
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("artifact path must stay inside the product workspace")
        return resolved
    name = value if value.endswith(".json") else f"{value}.json"
    for folder in folders:
        path = base / "artifacts" / folder / name
        if path.exists():
            return path.resolve()
    raise FileNotFoundError(f"artifact '{value}' does not exist")

def _find_artifact_by_id(base: Path, folder: str, key: str, value: str) -> Dict[str, Any]:
    if not value:
        return {}
    path = base / "artifacts" / folder / f"{value}.json"
    if path.exists():
        payload = read_json(path, {})
        return payload if isinstance(payload, dict) else {}
    for payload in artifacts().list(base.name, folder):
        if payload.get(key) == value:
            return payload
    return {}
