from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ...common import read_json

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))

def _resolve_known_artifact(base: Path, value: str, folders: List[str]) -> Path:
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

def _path_from_rel(base: Path, rel_path: str) -> Path | None:
    if not rel_path:
        return None
    path = (base / rel_path).resolve()
    root = base.resolve()
    if path != root and root not in path.parents:
        return None
    return path if path.exists() else None
