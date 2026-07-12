from __future__ import annotations

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

def _resolve_json_artifact(base: Path, value: str, folder: str, id_field: str) -> Path:
    clean = _text(value)
    if not clean:
        raise ValueError(f"{id_field} is required")
    candidate = Path(clean)
    if candidate.exists():
        return candidate.resolve()
    product_candidate = base / clean
    if product_candidate.exists():
        return product_candidate.resolve()
    name = clean if clean.endswith(".json") else f"{clean}.json"
    direct = base / "artifacts" / folder / name
    if direct.exists():
        return direct.resolve()
    for payload in artifacts().list(base.name, folder):
        if payload.get(id_field) == clean:
            path = base / "artifacts" / folder / f"{clean}.json"
            if path.exists():
                return path.resolve()
    raise FileNotFoundError(f"{id_field} '{value}' does not exist")

def _latest_json(base: Path, folder: str, id_field: str, matcher=None) -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    for payload in artifacts().list(base.name, folder):
        if matcher and not matcher(payload):
            continue
        artifact_id = _text(payload.get(id_field))
        path = base / "artifacts" / folder / f"{artifact_id}.json"
        out.append(
            {
                "id": artifact_id,
                "path": _rel(base, path),
                "created_at": _text(payload.get("created_at")) or _text(payload.get("confirmed_at")),
                "status": _text(payload.get("status")),
                "payload": payload,
            }
        )
    if not out:
        return {}
    out.sort(key=lambda item: (item["created_at"], item["path"]))
    return out[-1]
