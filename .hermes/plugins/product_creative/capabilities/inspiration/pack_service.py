"""Deterministic inspiration pack service."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...ports.runtime_repositories import artifacts

from .shared import _channel_for_target, _list, _rel, _safe_limit, _select_pack_candidates, _text
from .candidate_service import _resolve_candidate

INSPIRATION_PACK_SCHEMA_VERSION = "product_creative.inspiration_pack.v6.7"

def _pack_markdown(pack: Dict[str, Any]) -> str:
    lines = [
        f"# {pack['pack_id']}",
        "",
        f"Goal: {pack['goal']}",
        f"Target: {pack.get('target', '')}",
        f"Candidates: {len(pack.get('candidates') or [])}",
        "",
        "## Brief Context",
        "",
        pack.get("brief_context", ""),
        "",
    ]
    return "\n".join(lines)

def create_inspiration_pack(
    product_id: str,
    candidates: List[str] | None = None,
    goal: str = "",
    target: str = "",
    limit: int = 3,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    selected: List[Dict[str, Any]] = []
    if candidates:
        for candidate_id in candidates[: _safe_limit(limit, 3, 10)]:
            item = dict(_resolve_candidate(base, candidate_id))
            item["selection_role"] = "explicit"
            selected.append(item)
        selection_policy = {
            "target_channel": _channel_for_target(target),
            "primary_channel_filter": "explicit_candidate_ids",
            "dedupe_key": "none",
            "primary_candidate_count": len(selected),
            "secondary_reference_count": 0,
            "warnings": [],
        }
    else:
        entries = artifacts().list(base.name, "inspiration_candidates")
        selected, selection_policy = _select_pack_candidates(entries, target, limit)

    pack_id = f"inspiration-pack-{timestamp()}"
    lines = []
    for item in selected:
        role = item.get("selection_role") or "primary"
        channel = item.get("channel") or "unknown"
        lines.append(f"- [{role}/{channel}] {item.get('angle')} Hook: {item.get('hook')}")
    pack = {
        "schema_version": INSPIRATION_PACK_SCHEMA_VERSION,
        "pack_id": pack_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready" if selected else "empty",
        "goal": _text(goal) or _text(target) or "creative generation",
        "target": _text(target),
        "target_channel": selection_policy.get("target_channel", ""),
        "selection_policy": selection_policy,
        "selection_warnings": selection_policy.get("warnings", []),
        "selected_candidate_ids": [item.get("candidate_id") for item in selected],
        "source_snapshot_ids": sorted({sid for item in selected for sid in _list(item.get("source_snapshot_ids")) if sid}),
        "candidates": selected,
        "brief_context": "\n".join(lines),
        "not_product_fact": True,
        "mutates_product_brain": False,
    }
    out_dir = base / "artifacts" / "inspiration_packs"
    json_path = out_dir / f"{pack_id}.json"
    md_path = out_dir / f"{pack_id}.md"
    write_json(json_path, pack)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_pack_markdown(pack), encoding="utf-8")
    append_jsonl(
        base / "structured" / "inspiration_pack_index.jsonl",
        {
            "pack_id": pack_id,
            "created_at": pack["created_at"],
            "status": pack["status"],
            "target": pack["target"],
            "target_channel": pack["target_channel"],
            "candidate_count": len(selected),
            "secondary_reference_count": selection_policy.get("secondary_reference_count", 0),
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "inspiration-pack", pack_id, [f"Candidates: {len(selected)}", f"Target: {pack['target']}"])
    return {
        "success": True,
        "schema_version": INSPIRATION_PACK_SCHEMA_VERSION,
        "product_id": base.name,
        "pack_id": pack_id,
        "status": pack["status"],
        "candidate_count": len(selected),
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "inspiration_pack": pack,
    }
