"""Structured record readers for Product Creative workspaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .common import read_json


def read_jsonl_records(path: Path, encoding: str = "utf-8") -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for line in path.read_text(encoding=encoding).splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def read_json_artifacts(folder: Path, base: Path | None = None, include_path: bool = False) -> List[Dict[str, Any]]:
    if not folder.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue
        if include_path:
            payload["_path"] = str(path.relative_to(base or folder))
        entries.append(payload)
    return entries
