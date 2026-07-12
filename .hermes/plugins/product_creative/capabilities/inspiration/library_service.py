"""Confirmed inspiration library service."""

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

from .shared import _list, _rel, _text
from .llm_service import _resolve_llm_pack

INSPIRATION_LIBRARY_ENTRY_SCHEMA_VERSION = "product_creative.inspiration_library_entry.v6.11"

def _library_entry_markdown(entry: Dict[str, Any]) -> str:
    lines = [
        f"# {entry['entry_id']}",
        "",
        f"Status: {entry.get('status', '')}",
        f"Source pack: {entry.get('source_pack_id', '')}",
        f"Channel: {entry.get('channel', '')}",
        f"Target: {entry.get('target', '')}",
        "",
        "## Brief Context",
        "",
        entry.get("brief_context", ""),
        "",
        "## Confirmation",
        "",
        entry.get("confirmation_note", ""),
        "",
    ]
    return "\n".join(lines)

def confirm_llm_inspiration_pack(
    product_id: str,
    pack: str,
    note: str = "",
    confirmed: bool = False,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    payload = _resolve_llm_pack(base, pack)
    pack_id = _text(payload.get("pack_id")) or Path(pack).stem
    if not confirmed:
        return {
            "success": True,
            "schema_version": INSPIRATION_LIBRARY_ENTRY_SCHEMA_VERSION,
            "product_id": base.name,
            "status": "review_required",
            "source_pack_id": pack_id,
            "message": "User confirmation is required before writing this LLM inspiration pack into the reusable inspiration library.",
            "mutates_product_brain": False,
        }
    existing = next(
        (
            item for item in artifacts().list(base.name, "inspiration_library")
            if item.get("status") == "active" and item.get("source_pack_id") == pack_id
        ),
        None,
    )
    if existing:
        entry_id = _text(existing.get("entry_id"))
        out_dir = base / "artifacts" / "inspiration_library"
        return {
            "success": True,
            "schema_version": INSPIRATION_LIBRARY_ENTRY_SCHEMA_VERSION,
            "product_id": base.name,
            "entry_id": entry_id,
            "status": "active",
            "source_pack_id": pack_id,
            "files": {
                "json": str(out_dir / f"{entry_id}.json"),
                "markdown": str(out_dir / f"{entry_id}.md"),
            },
            "inspiration_library_entry": existing,
            "mutates_product_brain": False,
            "idempotent_replay": True,
        }
    entry_id = f"inspiration-library-entry-{timestamp()}"
    entry = {
        "schema_version": INSPIRATION_LIBRARY_ENTRY_SCHEMA_VERSION,
        "entry_id": entry_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "active",
        "source_pack_id": pack_id,
        "channel": payload.get("channel", ""),
        "target": payload.get("target", ""),
        "source_snapshot_ids": _list(payload.get("source_snapshot_ids")),
        "llm_summary": payload.get("llm_summary") if isinstance(payload.get("llm_summary"), dict) else {},
        "brief_context": _text(payload.get("brief_context")),
        "confirmation_note": _text(note),
        "not_product_fact": True,
        "mutates_product_brain": False,
    }
    out_dir = base / "artifacts" / "inspiration_library"
    json_path = out_dir / f"{entry_id}.json"
    md_path = out_dir / f"{entry_id}.md"
    write_json(json_path, entry)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_library_entry_markdown(entry), encoding="utf-8")
    payload["confirmation_status"] = "confirmed"
    payload["confirmed_library_entry_id"] = entry_id
    payload["confirmed_at"] = entry["created_at"]
    source_pack_path = base / "artifacts" / "llm_inspiration_packs" / f"{pack_id}.json"
    if source_pack_path.exists():
        write_json(source_pack_path, payload)
    append_jsonl(
        base / "structured" / "inspiration_library_index.jsonl",
        {
            "entry_id": entry_id,
            "created_at": entry["created_at"],
            "status": "active",
            "source_pack_id": pack_id,
            "channel": entry["channel"],
            "target": entry["target"],
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(
        base,
        "inspiration-library-entry",
        entry_id,
        [f"Source pack: {pack_id}", f"Channel: {entry['channel']}", "Confirmed by user"],
    )
    return {
        "success": True,
        "schema_version": INSPIRATION_LIBRARY_ENTRY_SCHEMA_VERSION,
        "product_id": base.name,
        "entry_id": entry_id,
        "status": "active",
        "source_pack_id": pack_id,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "inspiration_library_entry": entry,
        "mutates_product_brain": False,
    }

def latest_inspiration_context(product_id: str, target: str = "") -> Dict[str, Any]:
    base = ensure_product(product_id)
    library_entries = []
    for payload in artifacts().list(base.name, "inspiration_library"):
        if payload.get("status") != "active":
            continue
        if target and payload.get("target") and payload.get("target") != target:
            continue
        path = base / "artifacts" / "inspiration_library" / f"{payload.get('entry_id')}.json"
        library_entries.append((path, payload))
    if library_entries:
        library_entries.sort(key=lambda pair: _text(pair[1].get("created_at")))
        path, entry = library_entries[-1]
        summary = entry.get("llm_summary") if isinstance(entry.get("llm_summary"), dict) else {}
        return {
            "available": True,
            "source": "inspiration_library",
            "pack_id": entry.get("source_pack_id", path.stem),
            "entry_id": entry.get("entry_id", ""),
            "path": _rel(base, path),
            "target": entry.get("target", ""),
            "brief_context": _text(entry.get("brief_context")),
            "candidate_count": 0,
            "llm_summary_title": summary.get("summary_title", ""),
            "not_product_fact": True,
        }
    packs = []
    for payload in artifacts().list(base.name, "inspiration_packs"):
        if target and payload.get("target") and payload.get("target") != target:
            continue
        path = base / "artifacts" / "inspiration_packs" / f"{payload.get('pack_id')}.json"
        packs.append((path, payload))
    if not packs:
        return {"available": False, "brief_context": "", "pack_id": "", "candidates": []}
    packs.sort(key=lambda pair: _text(pair[1].get("created_at")))
    path, pack = packs[-1]
    return {
        "available": True,
        "pack_id": pack.get("pack_id", path.stem),
        "path": _rel(base, path),
        "target": pack.get("target", ""),
        "brief_context": _text(pack.get("brief_context")),
        "candidate_count": len(_list(pack.get("candidates"))),
        "candidates": [
            {
                "candidate_id": item.get("candidate_id"),
                "angle": item.get("angle"),
                "hook": item.get("hook"),
                "confidence": item.get("confidence"),
                "not_product_fact": True,
            }
            for item in _list(pack.get("candidates"))
            if isinstance(item, dict)
        ],
        "not_product_fact": True,
    }
