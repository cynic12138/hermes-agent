"""Structured workflow evidence readers for Product Creative runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from ..ports.runtime_repositories import artifacts, product_brains, proposals


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _payload_id(payload: Dict[str, Any], *fields: str) -> str:
    for field in fields:
        value = _text(payload.get(field))
        if value:
            return value
    return ""


def _artifact_items(base: Path, artifact_type: str) -> List[Dict[str, Any]]:
    return artifacts().list_records(base.name, artifact_type)


def latest_json(base: Path, rel_dir: str, *id_fields: str) -> Dict[str, Any]:
    artifact_type = Path(rel_dir).name
    candidates: List[Dict[str, Any]] = []
    for item in _artifact_items(base, artifact_type):
        payload = item["payload"]
        candidates.append(
            {
                "id": _payload_id(payload, *id_fields) or item["artifact_id"],
                "path": item["relative_path"],
                "created_at": _text(payload.get("created_at")) or _text(payload.get("applied_at")) or item["recorded_at"],
                "status": _text(payload.get("status")),
                "payload": payload,
            }
        )
    if not candidates:
        return {}
    candidates.sort(key=lambda item: (item["created_at"], item["path"]))
    return candidates[-1]


def latest_json_matching(
    base: Path,
    rel_dir: str,
    matcher: Callable[[Dict[str, Any]], bool],
    *id_fields: str,
) -> Dict[str, Any]:
    artifact_type = Path(rel_dir).name
    candidates: List[Dict[str, Any]] = []
    for item in _artifact_items(base, artifact_type):
        payload = item["payload"]
        if not matcher(payload):
            continue
        candidates.append(
            {
                "id": _payload_id(payload, *id_fields) or item["artifact_id"],
                "path": item["relative_path"],
                "created_at": _text(payload.get("created_at")) or _text(payload.get("applied_at")) or item["recorded_at"],
                "status": _text(payload.get("status")),
                "payload": payload,
            }
        )
    if not candidates:
        return {}
    candidates.sort(key=lambda item: (item["created_at"], item["path"]))
    return candidates[-1]


def _event_time(item: Dict[str, Any]) -> str:
    return _text(item.get("created_at") or item.get("payload", {}).get("applied_at"))


def is_newer(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    if not left:
        return False
    if not right:
        return True
    return (_event_time(left), _text(left.get("id"))) >= (_event_time(right), _text(right.get("id")))


def is_strictly_newer(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    if not left:
        return False
    if not right:
        return True
    return _event_time(left) > _event_time(right)


def proposal_pair(base: Path) -> Dict[str, Any]:
    proposed: List[Dict[str, Any]] = []
    applied: List[Dict[str, Any]] = []
    for payload in proposals().list(base.name):
        item = {
            "id": payload.get("proposal_id", ""),
            "path": f"sqlite://proposal/{base.name}/{payload.get('proposal_id', '')}",
            "created_at": _text(payload.get("created_at")),
            "applied_at": _text(payload.get("applied_at")),
            "status": _text(payload.get("status")),
            "payload": payload,
        }
        if item["status"] == "applied":
            applied.append(item)
        elif item["status"] == "proposed":
            proposed.append(item)
    all_items = proposed + applied
    all_items.sort(key=lambda item: (_text(item.get("created_at")), _text(item.get("id"))))
    proposed.sort(key=lambda item: (_text(item.get("created_at")), _text(item.get("id"))))
    applied.sort(key=lambda item: (_text(item.get("applied_at") or item.get("created_at")), _text(item.get("id"))))
    return {
        "latest": all_items[-1] if all_items else {},
        "latest_proposed": proposed[-1] if proposed else {},
        "latest_applied": applied[-1] if applied else {},
    }


def source_count(base: Path) -> int:
    current = product_brains().current(base.name)
    state = current.get("state") if isinstance(current.get("state"), dict) else {}
    return len(state.get("sources") or [])
