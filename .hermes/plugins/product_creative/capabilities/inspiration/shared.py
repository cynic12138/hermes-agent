from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""

def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))

def _safe_limit(value: int, default: int = 5, maximum: int = 20) -> int:
    try:
        return max(1, min(int(value or default), maximum))
    except (TypeError, ValueError):
        return default

def _channel_for_target(target: str) -> str:
    clean = _text(target)
    if clean == "xiaohongshu-seeding-note":
        return "xiaohongshu"
    if clean == "douyin-short-video-script":
        return "douyin"
    return ""

def _sanitize_string(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]

def _candidate_dedupe_key(candidate: Dict[str, Any]) -> str:
    text = _sanitize_string(candidate.get("hook") or candidate.get("angle") or candidate.get("title") or "", 300).lower()
    normalized = re.sub(r"\W+", "", text)
    return normalized or _text(candidate.get("candidate_id"))

def _candidate_sort_key(candidate: Dict[str, Any]) -> tuple[float, str]:
    try:
        confidence = float(candidate.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    return (confidence, _text(candidate.get("created_at")))

def _select_pack_candidates(entries: List[Dict[str, Any]], target: str, limit: int) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    clean_limit = _safe_limit(limit, 3, 10)
    target_channel = _channel_for_target(target)
    sorted_entries = sorted(entries, key=_candidate_sort_key, reverse=True)
    primary_entries = [item for item in sorted_entries if not target_channel or item.get("channel") == target_channel]
    secondary_entries = [item for item in sorted_entries if target_channel and item.get("channel") != target_channel]
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    warnings: List[str] = []

    def add(items: List[Dict[str, Any]], role: str, remaining: int) -> None:
        for item in items:
            if len(selected) >= clean_limit or remaining <= 0:
                return
            key = _candidate_dedupe_key(item)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            copied = dict(item)
            copied["selection_role"] = role
            selected.append(copied)
            remaining -= 1

    add(primary_entries, "primary", clean_limit)
    primary_count = len(selected)
    if target_channel and primary_count < clean_limit:
        add(secondary_entries, "secondary_reference", clean_limit - primary_count)
        if primary_count == 0 and secondary_entries:
            warnings.append(f"No {target_channel} candidates found; using secondary references from other channels.")
        elif len(selected) > primary_count:
            warnings.append(f"Added {len(selected) - primary_count} secondary reference candidate(s) because primary channel candidates were insufficient.")

    policy = {
        "target_channel": target_channel,
        "primary_channel_filter": target_channel or "none",
        "dedupe_key": "normalized hook/angle/title",
        "primary_candidate_count": primary_count,
        "secondary_reference_count": len([item for item in selected if item.get("selection_role") == "secondary_reference"]),
        "warnings": warnings,
    }
    return selected, policy
