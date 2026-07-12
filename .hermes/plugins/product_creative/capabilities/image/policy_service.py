"""Image capability service."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...providers import check_live_readiness, create_generation_job, prepare_provider_payload, validate_provider_payload

from .brief_service import _resolve_image_brief, _resolve_image_intent
from .shared import _rel, _text

BATCH_GENERATION_POLICY_SCHEMA_VERSION = "product_creative.batch_generation_policy.v4.3"

def create_batch_generation_policy(
    product_id: str,
    intent: str = "",
    brief: str = "",
    provider: str = "volcengine-ark-image",
    mode: str = "mock",
    count: int = 3,
    note: str = "",
    confirmed: bool = False,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    clean_count = max(1, min(int(count or 3), 5))
    intent_payload: Dict[str, Any] = {}
    brief_payload: Dict[str, Any] = {}
    brief_path: Path | None = None
    if _text(intent):
        intent_payload = _resolve_image_intent(base, intent)
    if _text(brief):
        brief_path, brief_payload = _resolve_image_brief(base, brief)
    policy_id = f"batch-policy-{timestamp()}-image"
    target = _text(intent_payload.get("target")) or _text((brief_payload.get("target") or {}).get("channel")) or "ecommerce-main-image-copy"
    pack = intent_payload.get("material_context") if isinstance(intent_payload.get("material_context"), dict) else {}
    policy = {
        "schema_version": BATCH_GENERATION_POLICY_SCHEMA_VERSION,
        "policy_id": policy_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "active" if confirmed else "draft",
        "source_image_intent_id": _text(intent_payload.get("intent_id")),
        "source_image_intent_path": _text(intent_payload.get("_path")),
        "source_brief_id": _text(brief_payload.get("brief_id")),
        "source_brief_path": _rel(base, brief_path) if brief_path else "",
        "target": target,
        "allowed_material_pack": _text(pack.get("task_material_pack_id")) or _text((brief_payload.get("source_material_pack") or {}).get("task_material_pack_id")),
        "style_direction": _text(intent_payload.get("style_direction")),
        "prompt_variation_rules": [
            "Keep product facts and visible identity stable.",
            "Vary composition, background, and emphasis only within the same channel target.",
        ],
        "count_limit": clean_count,
        "provider": _text(provider) or "volcengine-ark-image",
        "mode": _text(mode) or "mock",
        "external_call_limit": clean_count if mode == "live" else 0,
        "budget_note": "Live calls require explicit user-approved policy.",
        "forbidden_claims": ["unverified ingredients", "certifications", "medical or functional claims"],
        "must_keep_product_facts": True,
        "one_run_only": True,
        "note": _text(note),
        "confirmed": bool(confirmed),
        "confirmed_at": now_iso() if confirmed else "",
        "mutates_product_brain": False,
    }
    out_dir = base / "artifacts" / "batch_generation_policies"
    json_path = out_dir / f"{policy_id}.json"
    md_path = out_dir / f"{policy_id}.md"
    write_json(json_path, policy)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        "\n".join(
            [
                f"# {policy_id}",
                "",
                f"Status: {policy['status']}",
                f"Target: {target}",
                f"Provider: {policy['provider']}",
                f"Mode: {policy['mode']}",
                f"Count limit: {clean_count}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    append_jsonl(
        base / "structured" / "batch_generation_policy_index.jsonl",
        {
            "policy_id": policy_id,
            "created_at": policy["created_at"],
            "status": policy["status"],
            "target": target,
            "provider": policy["provider"],
            "mode": policy["mode"],
            "count_limit": clean_count,
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "batch-generation-policy", policy_id, [f"Status: {policy['status']}"])
    return {
        "success": True,
        "schema_version": BATCH_GENERATION_POLICY_SCHEMA_VERSION,
        "product_id": base.name,
        "policy_id": policy_id,
        "status": policy["status"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "policy": policy,
    }
