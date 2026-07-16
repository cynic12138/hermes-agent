"""Capability-owned workflow argument templates for inspiration."""
from __future__ import annotations

from typing import Any, Dict

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''

def plan_collect_external_source_snapshot(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {
                "product_id": product_id,
                "provider": "manual",
                "query": "<inspiration query>",
                "channel": target or "",
                "mode": "dry_run",
                "limit": 3,
                "import_path": "",
                "text": "",
                "url": "",
                "sidecar_url": "",
                "wait_seconds": 90,
                "transcribe_limit": 1,
                "analyze_first5_limit": 1,
                "auto_browser_cookie": False,
            }

def plan_create_inspiration_candidates(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_snapshot = evidence.get("latest_external_source_snapshot") or {}
    return {
                "product_id": product_id,
                "snapshot": latest_snapshot.get("id") or "<snapshot-id>",
                "goal": target or "",
                "max_candidates": 5,
            }

def plan_create_inspiration_pack(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {
                "product_id": product_id,
                "candidates": [],
                "goal": "",
                "target": target or "product-copy-pack",
                "limit": 3,
            }

def plan_create_llm_inspiration_pack(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_snapshot = evidence.get("latest_external_source_snapshot") or {}
    return {
                "product_id": product_id,
                "snapshots": [latest_snapshot.get("id")] if latest_snapshot.get("id") else [],
                "goal": "",
                "target": target or "",
                "channel": "",
                "max_items": 8,
                "provider": "",
                "model": "",
            }

def plan_confirm_inspiration_library_entry(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_pack = evidence.get("latest_llm_inspiration_pack") or {}
    return {
                "product_id": product_id,
                "pack": latest_pack.get("id") or "",
                "note": "",
                "confirmed": False,
            }

PLAN_TEMPLATES = {
    "collect_external_source_snapshot": plan_collect_external_source_snapshot,
    "create_inspiration_candidates": plan_create_inspiration_candidates,
    "create_inspiration_pack": plan_create_inspiration_pack,
    "create_llm_inspiration_pack": plan_create_llm_inspiration_pack,
    "confirm_inspiration_library_entry": plan_confirm_inspiration_library_entry,
}
