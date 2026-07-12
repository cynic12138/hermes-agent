from __future__ import annotations

from typing import Any, Dict

PRIORITY = 30


def recommend_action(context: Dict[str, Any]) -> str:
    evidence = context["evidence"]
    newer = context["is_strictly_newer"]
    snapshot = evidence.get("latest_external_source_snapshot") or {}
    candidate = evidence.get("latest_inspiration_candidate") or {}
    pack = evidence.get("latest_inspiration_pack") or {}
    if snapshot and (not candidate or newer(snapshot, candidate)):
        return "create_inspiration_candidates"
    if candidate and (not pack or newer(candidate, pack)):
        return "create_inspiration_pack"
    return ""
