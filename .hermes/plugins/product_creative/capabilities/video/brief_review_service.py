"""Video brief review and revision service."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...context_safety import apply_generation_safe_state, generation_safe_list

from .brief_shared import _list, _rel, _resolve_artifact, _state_hash, _text
from .brief_creation_service import _brief_markdown, _prompt, _set_provider_prompt_segment

VIDEO_BRIEF_REVIEW_SCHEMA_VERSION = "product_creative.video_brief_review_package.v2.19"

VIDEO_BRIEF_PATCH_SCHEMA_VERSION = "product_creative.video_brief_patch.v2.28"

VIDEO_BRIEF_REVISION_SCHEMA_VERSION = "product_creative.video_brief.v2.28"

SHOT_UPDATE_FIELDS = [
    "duration",
    "purpose",
    "scene",
    "action",
    "camera",
    "motion",
    "composition",
    "product_visibility",
    "lighting",
    "transition",
    "audio",
    "caption",
    "visual_prompt",
    "negative_prompt",
    "reference_usage",
]

def _patch_template(brief: Dict[str, Any], review_id: str) -> Dict[str, Any]:
    patch_id = f"video-brief-patch-{timestamp()}"
    storyboard = []
    for shot in (brief.get("story") or {}).get("storyboard", []):
        storyboard.append(
            {
                "shot": shot.get("shot"),
                "duration": "",
                "purpose": "",
                "scene": "",
                "action": "",
                "camera": "",
                "motion": "",
                "composition": "",
                "product_visibility": "",
                "lighting": "",
                "transition": "",
                "audio": "",
                "caption": "",
                "visual_prompt": "",
                "negative_prompt": "",
                "reference_usage": "",
            }
        )
    return {
        "schema_version": VIDEO_BRIEF_PATCH_SCHEMA_VERSION,
        "patch_id": patch_id,
        "product_id": brief.get("product_id", ""),
        "created_at": now_iso(),
        "status": "editable_template",
        "source_brief_id": brief.get("brief_id", ""),
        "source_review_package_id": review_id,
        "instructions": [
            "Only fill fields that need to change; empty fields keep the source brief value.",
            "Set confirmation.confirmed to true only after human review.",
            "Do not add unverified product facts, packaging text, certifications, awards, origin details, or efficacy claims.",
        ],
        "story_updates": {
            "theme": "",
            "estimated_duration": "",
            "pacing": "",
            "caption_plan": "",
            "audio_plan": [],
            "editing_rules": [],
        },
        "shot_updates": storyboard,
        "confirmation": {
            "confirmed": False,
            "confirmed_by": "human",
            "note": "",
        },
    }

def _patch_markdown(patch: Dict[str, Any]) -> str:
    lines = [
        f"# {patch['patch_id']}",
        "",
        f"Source brief: {patch.get('source_brief_id', '')}",
        f"Review package: {patch.get('source_review_package_id', '')}",
        "",
        "## How To Edit",
        "",
    ]
    lines.extend([f"- {item}" for item in patch.get("instructions", [])])
    lines.extend(["", "## Editable JSON", "", "```json"])
    lines.append(json.dumps(patch, ensure_ascii=False, indent=2))
    lines.extend(["```", ""])
    return "\n".join(lines)

def _write_patch_template(base: Path, brief: Dict[str, Any], review_id: str) -> Dict[str, Any]:
    patch = _patch_template(brief, review_id)
    out_dir = base / "artifacts" / "video_brief_patches"
    json_path = out_dir / f"{patch['patch_id']}.json"
    md_path = out_dir / f"{patch['patch_id']}.md"
    write_json(json_path, patch)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_patch_markdown(patch), encoding="utf-8")
    append_jsonl(base / "structured" / "video_brief_patch_index.jsonl", {
        "patch_id": patch["patch_id"],
        "created_at": patch["created_at"],
        "source_brief_id": patch["source_brief_id"],
        "source_review_package_id": review_id,
        "status": patch["status"],
    })
    return {
        "patch_id": patch["patch_id"],
        "json": str(json_path),
        "markdown": str(md_path),
        "path": _rel(base, json_path),
    }

def _non_empty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return value is not None

def _apply_story_updates(story: Dict[str, Any], updates: Dict[str, Any]) -> None:
    for field in ["theme", "estimated_duration", "pacing", "caption_plan"]:
        value = updates.get(field)
        if _non_empty(value):
            story[field] = value.strip() if isinstance(value, str) else value
    for field in ["audio_plan", "editing_rules"]:
        value = updates.get(field)
        if isinstance(value, list) and value:
            story[field] = [str(item).strip() for item in value if str(item).strip()]

def _apply_shot_updates(storyboard: List[Dict[str, Any]], updates: List[Any]) -> List[Dict[str, Any]]:
    by_shot = {str(item.get("shot")): item for item in storyboard if isinstance(item, dict)}
    for update in updates:
        if not isinstance(update, dict):
            continue
        target = by_shot.get(str(update.get("shot")))
        if not target:
            continue
        for field in SHOT_UPDATE_FIELDS:
            value = update.get(field)
            if _non_empty(value):
                target[field] = value.strip() if isinstance(value, str) else value
        _set_provider_prompt_segment(target)
    return storyboard

def _patch_confirmation(patch: Dict[str, Any], confirmed: bool, note: str) -> Dict[str, Any]:
    confirmation = patch.get("confirmation") if isinstance(patch.get("confirmation"), dict) else {}
    return {
        "confirmed": bool(confirmed or confirmation.get("confirmed")),
        "confirmed_by": _text(confirmation.get("confirmed_by")) or "human",
        "note": note or _text(confirmation.get("note")),
    }

def _revision_number(brief: Dict[str, Any]) -> int:
    revision = brief.get("revision") if isinstance(brief.get("revision"), dict) else {}
    try:
        return int(revision.get("revision_number") or 0) + 1
    except (TypeError, ValueError):
        return 1

def _review_markdown(package: Dict[str, Any]) -> str:
    lines = [
        f"# {package['review_package_id']}",
        "",
        f"Product: {package['product']['name']}",
        f"Brief: {package['source_brief_id']}",
        f"Status: {package['status']}",
        "",
        "## Creative Summary",
        "",
        f"- Platform: {package['creative_summary'].get('platform', '')}",
        f"- Theme: {package['creative_summary'].get('theme', '')}",
        f"- Duration: {package['creative_summary'].get('estimated_duration', '')}",
        "",
        "## Storyboard",
        "",
        "| Shot | Duration | Purpose | Action | Camera | Audio | Caption |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for shot in package.get("creative_summary", {}).get("storyboard", []):
        lines.append(
            f"| {shot.get('shot')} | {shot.get('duration')} | {shot.get('purpose')} | "
            f"{shot.get('action')} | {shot.get('camera')} | {shot.get('audio')} | {shot.get('caption')} |"
        )
    lines.extend(["", "## Prompt", "", package.get("creative_summary", {}).get("prompt", ""), "", "## Review Checklist", ""])
    lines.extend([f"- [ ] {item}" for item in package.get("review_checklist", [])])
    lines.extend(["", "## Risk Notes", ""])
    lines.extend([f"- {item}" for item in package.get("risk_notes", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def create_video_brief_review_package(product_id: str, brief: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    brief_path = _resolve_artifact(base, brief, ["video_scripts"])
    brief_payload = read_json(brief_path, {})
    if brief_payload.get("brief_type") != "video":
        raise ValueError("video brief review requires a video brief")
    state = apply_generation_safe_state(read_product_state(base))
    review_id = f"video-brief-review-{timestamp()}"
    editable_patch = _write_patch_template(base, brief_payload, review_id)
    package = {
        "schema_version": VIDEO_BRIEF_REVIEW_SCHEMA_VERSION,
        "review_package_id": review_id,
        "review_type": "video_brief",
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_human_review",
        "source_brief_id": brief_payload.get("brief_id", brief_path.stem),
        "source_brief_path": _rel(base, brief_path),
        "source_intent_id": brief_payload.get("source_intent_id", ""),
        "external_call_performed": False,
        "mutates_product_brain": False,
        "product": {
            "name": state.get("name", base.name),
            "brief": (state.get("basic") or {}).get("brief", ""),
            "selling_points": (state.get("generation_safe") or {}).get("selling_points") if isinstance(state.get("generation_safe"), dict) else state.get("selling_points", []),
        },
        "creative_summary": {
            "platform": (brief_payload.get("target") or {}).get("platform", ""),
            "theme": (brief_payload.get("story") or {}).get("theme", ""),
            "estimated_duration": (brief_payload.get("story") or {}).get("estimated_duration", ""),
            "storyboard": (brief_payload.get("story") or {}).get("storyboard", []),
            "pacing": (brief_payload.get("story") or {}).get("pacing", ""),
            "audio_plan": (brief_payload.get("story") or {}).get("audio_plan", []),
            "caption_plan": (brief_payload.get("story") or {}).get("caption_plan", ""),
            "prompt": (brief_payload.get("generation_contract") or {}).get("prompt", ""),
            "source_assets": brief_payload.get("source_assets", []),
        },
        "visual_grounding": brief_payload.get("visual_grounding", {}),
        "editable_patch": editable_patch,
        "risk_notes": [
            "Approve or edit this brief before building a provider payload.",
            "Confirm the selected reference image can be used as first frame/reference image.",
            "Confirm no packaging text, claims, certification, origin, or efficacy was invented.",
            "Mock image analysis is not enough for final packaging/claim validation.",
        ],
        "review_checklist": [
            "Product name and visible subject are correct.",
            "Selected material is appropriate as video first frame/reference image.",
            "Storyboard follows the requested platform and theme.",
            "Each shot has concrete action, camera, motion, audio, and product visibility instructions.",
            "Captions are short enough for video rendering.",
            "No unverified facts or exaggerated promises are introduced.",
            "Prompt is ready to convert into a provider payload.",
        ],
        "next_actions": {
            "revise_or_confirm_brief": {
                "tool": "product_video_brief_revise",
                "command": rf".\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-brief-revise --id {base.name} --brief {brief_payload.get('brief_id', brief_path.stem)} --patch {editable_patch['patch_id']} --confirmed",
            },
            "build_provider_payload": {
                "tool": "product_video_generate",
                "command": rf".\.hermes\plugins\product_creative\scripts\product_creative.ps1 video-generate --id {base.name} --brief {brief_payload.get('brief_id', brief_path.stem)} --provider generic",
            },
            "record_feedback_later": {
                "tool": "product_result_feedback",
                "note": "Feedback should be recorded after a generated video result exists.",
            },
        },
        "source_artifacts": [
            {"id": brief_payload.get("brief_id", brief_path.stem), "type": "video_brief", "path": _rel(base, brief_path)},
            {"id": editable_patch["patch_id"], "type": "video_brief_patch", "path": editable_patch["path"]},
            {"id": brief_payload.get("source_intent_id", ""), "type": "video_intent"},
        ],
    }
    out_dir = base / "artifacts" / "review_packages"
    json_path = out_dir / f"{review_id}.json"
    md_path = out_dir / f"{review_id}.md"
    write_json(json_path, package)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_review_markdown(package), encoding="utf-8")
    append_jsonl(base / "structured" / "video_brief_review_index.jsonl", {
        "review_package_id": review_id,
        "created_at": package["created_at"],
        "source_brief_id": package["source_brief_id"],
        "status": package["status"],
    })
    update_index_and_log(base, "video-brief-review", review_id, [f"Brief: {package['source_brief_id']}"])
    return {
        "success": True,
        "product_id": base.name,
        "review_package_id": review_id,
        "status": package["status"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "editable_patch": editable_patch,
        "review_package": package,
    }

def revise_video_brief(
    product_id: str,
    brief: str,
    patch: str = "",
    note: str = "",
    confirmed: bool = False,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    brief_path = _resolve_artifact(base, brief, ["video_scripts"])
    source_brief = read_json(brief_path, {})
    if source_brief.get("brief_type") != "video":
        raise ValueError("video brief revision requires a video brief")

    patch_payload: Dict[str, Any] = {}
    patch_path: Path | None = None
    if _text(patch):
        patch_path = _resolve_artifact(base, patch, ["video_brief_patches"])
        patch_payload = read_json(patch_path, {})
        if patch_payload.get("schema_version") != VIDEO_BRIEF_PATCH_SCHEMA_VERSION:
            raise ValueError("video brief revision requires a M2.28 video brief patch")
        source_id = _text(patch_payload.get("source_brief_id"))
        if source_id and source_id != _text(source_brief.get("brief_id", brief_path.stem)):
            raise ValueError("video brief patch does not match the source brief")

    state = read_product_state(base)
    revision_number = _revision_number(source_brief)
    revision_id = f"video-brief-{timestamp()}-rev{revision_number}"
    story = dict(source_brief.get("story") or {})
    storyboard = [dict(item) for item in _list(story.get("storyboard")) if isinstance(item, dict)]

    _apply_story_updates(story, patch_payload.get("story_updates") if isinstance(patch_payload.get("story_updates"), dict) else {})
    story["storyboard"] = _apply_shot_updates(storyboard, _list(patch_payload.get("shot_updates")))

    product = source_brief.get("product") if isinstance(source_brief.get("product"), dict) else {}
    target = source_brief.get("target") if isinstance(source_brief.get("target"), dict) else {}
    product_name = _text(product.get("name")) or _text(state.get("name")) or base.name
    platform = _text(target.get("platform")) or "douyin"
    theme = _text(story.get("theme")) or "产品短视频"
    inspiration_context = source_brief.get("inspiration_context") if isinstance(source_brief.get("inspiration_context"), dict) else {}
    prompt = _prompt(product_name, theme, platform, story["storyboard"], _list(source_brief.get("source_assets")), state, inspiration_context)
    confirmation = _patch_confirmation(patch_payload, confirmed, note)

    revised = dict(source_brief)
    revised.update(
        {
            "schema_version": VIDEO_BRIEF_REVISION_SCHEMA_VERSION,
            "brief_id": revision_id,
            "created_at": now_iso(),
            "status": "confirmed_for_provider_payload" if confirmation["confirmed"] else "ready_for_review",
            "source_artifact_id": source_brief.get("brief_id", brief_path.stem),
            "source_variant": revision_number + 1,
            "story": story,
            "generation_contract": dict(source_brief.get("generation_contract") or {}),
            "revision": {
                "revision_number": revision_number,
                "revision_of": source_brief.get("brief_id", brief_path.stem),
                "source_brief_path": _rel(base, brief_path),
                "source_patch_id": patch_payload.get("patch_id", ""),
                "source_patch_path": _rel(base, patch_path) if patch_path else "",
                "review_note": confirmation["note"],
                "confirmed_for_provider_payload": confirmation["confirmed"],
                "confirmed_by": confirmation["confirmed_by"],
                "confirmed_at": now_iso() if confirmation["confirmed"] else "",
            },
        }
    )
    revised["generation_contract"].update(
        {
            "prompt": prompt,
            "provider_prompt": prompt,
            "storyboard_prompt_segments": [shot.get("provider_prompt_segment", "") for shot in story["storyboard"]],
            "requires_human_review": not confirmation["confirmed"],
            "review_status": revised["status"],
        }
    )
    source_artifacts = _list(revised.get("source_artifacts"))
    source_artifacts.append({"id": source_brief.get("brief_id", brief_path.stem), "type": "video_brief", "path": _rel(base, brief_path)})
    if patch_payload:
        source_artifacts.append({"id": patch_payload.get("patch_id", ""), "type": "video_brief_patch", "path": _rel(base, patch_path)})
    revised["source_artifacts"] = source_artifacts
    revised["brain_write_policy"] = {
        "direct_write_to_product_brain": False,
        "requires_human_confirmation_for_learning": True,
    }

    out_dir = base / "artifacts" / "video_scripts"
    json_path = out_dir / f"{revision_id}.json"
    md_path = out_dir / f"{revision_id}.md"
    write_json(json_path, revised)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_brief_markdown(revised), encoding="utf-8")
    append_jsonl(base / "structured" / "brief_index.jsonl", {
        "export_id": revision_id,
        "created_at": revised["created_at"],
        "kind": "video",
        "source": "video_brief_revision",
        "source_brief_id": source_brief.get("brief_id", brief_path.stem),
        "outputs": [{"brief_id": revision_id, "brief_type": "video", "source_variant": revised["source_variant"]}],
    })
    append_jsonl(base / "structured" / "video_brief_revision_index.jsonl", {
        "brief_id": revision_id,
        "created_at": revised["created_at"],
        "revision_of": source_brief.get("brief_id", brief_path.stem),
        "patch_id": patch_payload.get("patch_id", ""),
        "status": revised["status"],
        "confirmed_for_provider_payload": confirmation["confirmed"],
    })
    update_index_and_log(
        base,
        "video-brief-revise",
        revision_id,
        [
            f"Revision of: {source_brief.get('brief_id', brief_path.stem)}",
            f"Status: {revised['status']}",
            f"Patch: {patch_payload.get('patch_id', '')}",
        ],
    )
    return {
        "success": True,
        "product_id": base.name,
        "brief_id": revision_id,
        "source_brief_id": source_brief.get("brief_id", brief_path.stem),
        "patch_id": patch_payload.get("patch_id", ""),
        "status": revised["status"],
        "confirmed_for_provider_payload": confirmation["confirmed"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "brief": revised,
    }
