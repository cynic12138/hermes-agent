"""Image capability service."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ..content.generation_service import generate_product
from ..inspiration.library_service import latest_inspiration_context
from ..material.pack_service import prepare_task_material_pack
from ...providers import check_live_readiness, create_generation_job, prepare_provider_payload, validate_provider_payload

from .shared import _list, _rel, _text

IMAGE_INTENT_SCHEMA_VERSION = "product_creative.image_intent.v4.1"

TARGET_PRESETS = {
    "ecommerce-main-image-copy": ("taobao-main-image", "ecommerce"),
    "xiaohongshu-seeding-note": ("xiaohongshu-cover", "xiaohongshu"),
    "douyin-short-video-script": ("douyin-9x16", "douyin"),
}

def _target_from_message(message: str, target: str) -> str:
    if target:
        return target
    lower = message.lower()
    if "小红书" in message or "xiaohongshu" in lower or "封面" in message or "种草" in message:
        return "xiaohongshu-seeding-note"
    if "抖音" in message or "douyin" in lower:
        return "douyin-short-video-script"
    if "竖版" in message or "竖屏" in message or "9:16" in message:
        return "xiaohongshu-seeding-note"
    return "ecommerce-main-image-copy"

def _style_from_message(message: str, style: str) -> str:
    if style:
        return style
    markers = []
    if "高级" in message:
        markers.append("高级感")
    if "促销" in message:
        markers.append("促销感")
    if "清爽" in message:
        markers.append("清爽")
    if "真实" in message:
        markers.append("真实自然")
    return "、".join(markers) if markers else ""

def _intent_markdown(intent: Dict[str, Any]) -> str:
    materials = intent.get("material_context", {}).get("selected_materials") or []
    lines = [
        f"# {intent['intent_id']}",
        "",
        f"Product: {intent['product_id']}",
        f"Target: {intent['target']}",
        f"Preset: {intent['preset']}",
        f"Count limit: {intent['count_limit']}",
        f"Provider: {intent['provider']}",
        "",
        "## User Message",
        "",
        intent.get("message", ""),
        "",
        "## Selected Materials",
        "",
    ]
    lines.extend([f"- {item.get('material_id')}: {item.get('role')} | {item.get('summary')}" for item in materials] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def resolve_image_intent(
    product_id: str,
    message: str,
    target: str = "",
    count: int = 3,
    style: str = "",
    provider: str = "volcengine-ark-image",
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    state = read_product_state(base)
    clean_target = _target_from_message(message, _text(target))
    preset, channel = TARGET_PRESETS.get(clean_target, ("taobao-main-image", "ecommerce"))
    clean_count = max(1, min(int(count or 3), 5))
    pack_result = prepare_task_material_pack(base.name, "image_brief", channel, 3)
    pack = pack_result.get("task_material_pack") if isinstance(pack_result.get("task_material_pack"), dict) else {}
    inspiration_context = latest_inspiration_context(base.name, clean_target or "image_brief")
    materials = []
    for item in _list(pack.get("selected_materials")):
        if isinstance(item, dict):
            materials.append(
                {
                    "material_id": _text(item.get("material_id")),
                    "role": _text(item.get("role")),
                    "score": item.get("score", 0),
                    "summary": _text(item.get("summary")),
                    "warnings": _list(item.get("warnings")),
                }
            )
    intent_id = f"image-intent-{timestamp()}"
    intent = {
        "schema_version": IMAGE_INTENT_SCHEMA_VERSION,
        "intent_id": intent_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_image_brief",
        "message": _text(message),
        "target": clean_target,
        "channel": channel,
        "preset": preset,
        "style_direction": _style_from_message(message, style),
        "count_limit": clean_count,
        "provider": _text(provider) or "volcengine-ark-image",
        "mode_policy": {
            "default_mode": "mock",
            "live_requires_confirmation": True,
            "max_live_calls": clean_count,
        },
        "product_snapshot": {
            "name": _text(state.get("name")) or base.name,
            "selling_points": _list(state.get("selling_points")),
            "image_generation_preferences": _list((state.get("learning") or {}).get("image_generation_preferences")),
            "material_preferences": _list((state.get("learning") or {}).get("material_preferences")),
        },
        "material_context": {
            "task_material_pack_id": _text(pack.get("task_material_pack_id")),
            "task": _text(pack.get("task")),
            "channel": _text(pack.get("channel")),
            "selected_materials": materials,
            "missing_requirements": _list(pack.get("missing_requirements")),
            "inspiration_context": inspiration_context if inspiration_context.get("available") else {},
        },
        "risk_notes": [
            "Generated images must not add unverified product claims.",
            "Generated images are candidates until the user selects and registers them.",
        ],
        "mutates_product_brain": False,
        "external_call_performed": False,
    }
    out_dir = base / "artifacts" / "image_intents"
    json_path = out_dir / f"{intent_id}.json"
    md_path = out_dir / f"{intent_id}.md"
    write_json(json_path, intent)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_intent_markdown(intent), encoding="utf-8")
    append_jsonl(
        base / "structured" / "image_intent_index.jsonl",
        {
            "intent_id": intent_id,
            "created_at": intent["created_at"],
            "target": clean_target,
            "channel": channel,
            "count_limit": clean_count,
            "task_material_pack_id": intent["material_context"]["task_material_pack_id"],
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "image-intent", intent_id, [f"Target: {clean_target}", f"Count: {clean_count}"])
    return {
        "success": True,
        "schema_version": IMAGE_INTENT_SCHEMA_VERSION,
        "product_id": base.name,
        "intent_id": intent_id,
        "status": intent["status"],
        "target": clean_target,
        "preset": preset,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "image_intent": intent,
    }
