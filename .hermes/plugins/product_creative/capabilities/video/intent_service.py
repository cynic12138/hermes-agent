"""Video intent resolution service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...ports.runtime_repositories import artifacts
from ..material.pack_service import prepare_task_material_pack


VIDEO_INTENT_SCHEMA_VERSION = "product_creative.video_intent.v2.17"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))


def _json_records(base: Path, folder: str) -> List[Dict[str, Any]]:
    records = artifacts().list(base.name, folder)
    records.sort(key=lambda value: (_text(value.get("created_at")), _text(value.get("material_id") or value.get("analysis_id") or value.get("alignment_id"))))
    return records


def _intent_type(message: str, has_asset: bool) -> str:
    text = message.lower()
    if any(item in message for item in ["今日视频", "今天视频", "今日内容", "今天内容", "今日选题"]) or "today" in text:
        return "today_video"
    if any(item in message for item in ["图生视频", "以这张图", "用这张图", "以这张主图", "用这张主图", "用这个主图", "主图做视频"]):
        return "image_to_video"
    if any(item in message for item in ["已有素材", "素材库", "本地素材", "根据素材"]):
        return "material_based_video"
    if has_asset:
        return "image_to_video"
    if any(item in message for item in ["视频", "短视频", "分镜", "拍一个", "生成视频"]):
        return "product_video"
    return "unknown"


def _platform(message: str) -> str:
    text = message.lower()
    if "小红书" in message or "xiaohongshu" in text or "种草" in message:
        return "xiaohongshu"
    if "抖音" in message or "douyin" in text or "短视频" in message:
        return "douyin"
    if "电商" in message or "主图" in message or "ecommerce" in text:
        return "ecommerce"
    return "douyin"


def _theme_hint(message: str) -> str:
    text = message.strip()
    for marker in ["关于", "围绕", "主题是", "方向是"]:
        if marker in text:
            return text.split(marker, 1)[1].strip(" ：:。")
    if "今日" in text or "今天" in text:
        return "today_theme_required"
    return ""


def _select_asset(records: List[Dict[str, Any]], preferred_asset: str = "") -> Dict[str, Any]:
    if preferred_asset:
        for item in records:
            if preferred_asset in {item.get("material_id"), item.get("stored_path"), item.get("source_path")}:
                return item
    roles = ["video_first_frame", "current_main_image", "product_photo", "style_reference"]
    for role in roles:
        for item in reversed(records):
            if item.get("role") == role and item.get("status") == "active":
                return item
    return records[-1] if records else {}


def _material_by_id(records: List[Dict[str, Any]], material_id: str) -> Dict[str, Any]:
    for item in records:
        if _text(item.get("material_id")) == material_id:
            return item
    return {}


def _latest_for_material(records: List[Dict[str, Any]], material_id: str, id_field: str) -> Dict[str, Any]:
    if not material_id:
        return {}
    matches = [item for item in records if item.get("material_id") == material_id]
    matches.sort(key=lambda item: (_text(item.get("created_at")), _text(item.get(id_field))))
    return matches[-1] if matches else {}


def _recommended_steps(
    intent_type: str,
    selected_asset: Dict[str, Any],
    latest_analysis: Dict[str, Any],
    latest_alignment: Dict[str, Any],
    theme_hint: str,
) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    if not selected_asset and intent_type in {"image_to_video", "material_based_video", "today_video", "product_video"}:
        steps.append(
            {
                "step": "register_material_asset",
                "status": "required",
                "tool": "product_asset_register",
                "reason": "No usable product material is registered yet.",
            }
        )
        return steps
    if selected_asset and not latest_analysis:
        steps.append(
            {
                "step": "analyze_image",
                "status": "required",
                "tool": "product_image_analyze",
                "args_template": {
                    "product_id": selected_asset.get("product_id"),
                    "asset": selected_asset.get("material_id"),
                    "provider": "mock-vision",
                },
                "reason": "Selected material has not been analyzed yet.",
            }
        )
        return steps
    if latest_analysis and not latest_alignment:
        steps.append(
            {
                "step": "visual_align",
                "status": "required",
                "tool": "product_visual_align",
                "args_template": {
                    "product_id": latest_analysis.get("product_id"),
                    "analysis": latest_analysis.get("analysis_id"),
                },
                "reason": "Image analysis has not been aligned with Product Brain yet.",
            }
        )
        return steps
    if intent_type == "today_video" and theme_hint == "today_theme_required":
        steps.append(
            {
                "step": "trend_context",
                "status": "recommended_later",
                "tool": "",
                "reason": "Today-video requests should use trend/topic context once trend provider is available.",
            }
        )
    steps.append(
        {
            "step": "create_image_to_video_brief",
            "status": "ready_next",
            "tool": "product_video_brief",
            "reason": "Material, analysis, and visual alignment are available for video brief generation.",
        }
    )
    return steps


def _intent_markdown(intent: Dict[str, Any]) -> str:
    lines = [
        f"# {intent['intent_id']}",
        "",
        f"Product: {intent['product_id']}",
        f"Intent type: {intent['intent']['type']}",
        f"Platform: {intent['intent']['platform']}",
        f"Status: {intent['status']}",
        "",
        "## User Message",
        "",
        intent.get("message") or "",
        "",
        "## Selected Material",
        "",
        f"- Material: {intent.get('selected_material', {}).get('material_id', '')}",
        f"- Role: {intent.get('selected_material', {}).get('role', '')}",
        "",
        "## Recommended Steps",
        "",
    ]
    for item in intent.get("recommended_steps", []):
        lines.append(f"- {item.get('step')} | {item.get('status')} | {item.get('reason')}")
    lines.extend(["", "## Missing Inputs", ""])
    lines.extend([f"- {item}" for item in intent.get("missing_inputs", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def resolve_video_intent(
    product_id: str,
    message: str,
    asset: str = "",
    platform: str = "",
    theme: str = "",
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    state = read_product_state(base)
    materials = _json_records(base, "material_assets")
    analyses = _json_records(base, "image_analysis")
    alignments = _json_records(base, "visual_alignments")
    inferred_type = _intent_type(message, bool(_text(asset)))
    inferred_platform = _text(platform) or _platform(message)
    inferred_theme = _text(theme) or _theme_hint(message)
    task_pack: Dict[str, Any] = {}
    selected_card: Dict[str, Any] = {}
    if _text(asset):
        selected = _select_asset(materials, _text(asset))
    else:
        pack_result = prepare_task_material_pack(base.name, "video_brief", inferred_platform, 3)
        task_pack = pack_result.get("task_material_pack") if isinstance(pack_result.get("task_material_pack"), dict) else {}
        first = (_list(task_pack.get("selected_materials")) or [{}])[0]
        selected_card = first if isinstance(first, dict) else {}
        selected = _material_by_id(materials, _text(selected_card.get("material_id"))) or _select_asset(materials, "")
    selected_id = _text(selected.get("material_id"))
    latest_analysis = _latest_for_material(analyses, selected_id, "analysis_id")
    latest_alignment = _latest_for_material(alignments, selected_id, "alignment_id")
    steps = _recommended_steps(inferred_type, selected, latest_analysis, latest_alignment, inferred_theme)
    missing_inputs = []
    if inferred_type == "unknown":
        missing_inputs.append("video_intent")
    if not selected:
        missing_inputs.append("material_asset")
    if inferred_type == "today_video" and inferred_theme == "today_theme_required":
        missing_inputs.append("trend_or_topic_context")
    status = "ready_for_video_brief" if steps and steps[-1].get("step") == "create_image_to_video_brief" else "needs_preparation"
    if missing_inputs and not selected:
        status = "waiting_for_user_input"

    intent_id = f"video-intent-{timestamp()}"
    intent = {
        "schema_version": VIDEO_INTENT_SCHEMA_VERSION,
        "intent_id": intent_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": status,
        "message": message,
        "intent": {
            "type": inferred_type,
            "platform": inferred_platform,
            "theme_hint": inferred_theme,
            "generation_route": "image_to_video_brief" if selected else "requires_material_first",
        },
        "product_context": {
            "name": state.get("name") or base.name,
            "has_product_brain": True,
            "selling_point_count": len(_list(state.get("selling_points"))),
        },
        "selected_material": {
            "material_id": selected_id,
            "material_card_id": _text(selected_card.get("material_card_id")),
            "task_material_pack_id": _text(task_pack.get("task_material_pack_id")),
            "role": selected.get("role", ""),
            "stored_path": selected.get("stored_path", ""),
            "can_be_video_first_frame": bool(selected.get("generation_policy", {}).get("can_be_video_first_frame")),
        },
        "readiness": {
            "has_material": bool(selected),
            "has_image_analysis": bool(latest_analysis),
            "has_visual_alignment": bool(latest_alignment),
            "has_confirmed_visual_learning": bool(_list(state.get("learning", {}).get("image_generation_preferences"))),
            "video_live_generation_supported": False,
        },
        "related_artifacts": {
            "image_analysis_id": latest_analysis.get("analysis_id", ""),
            "visual_alignment_id": latest_alignment.get("alignment_id", ""),
            "material_card_id": _text(selected_card.get("material_card_id")),
            "task_material_pack_id": _text(task_pack.get("task_material_pack_id")),
        },
        "missing_inputs": missing_inputs,
        "recommended_steps": steps,
        "safety": {
            "direct_write_to_product_brain": False,
            "executes_generation": False,
            "requires_human_review_before_video_generation": True,
        },
    }
    out_dir = base / "artifacts" / "video_intents"
    json_path = out_dir / f"{intent_id}.json"
    md_path = out_dir / f"{intent_id}.md"
    write_json(json_path, intent)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_intent_markdown(intent), encoding="utf-8")
    append_jsonl(base / "structured" / "video_intent_index.jsonl", {
        "intent_id": intent_id,
        "created_at": intent["created_at"],
        "type": inferred_type,
        "status": status,
        "material_id": selected_id,
        "path": _rel(base, json_path),
    })
    update_index_and_log(base, "video-intent", intent_id, [f"Type: {inferred_type}", f"Status: {status}"])
    return {
        "success": True,
        "product_id": base.name,
        "intent_id": intent_id,
        "status": status,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "video_intent": intent,
    }
