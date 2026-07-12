"""M3 task material packs, usage, and lightweight feedback."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, read_json, timestamp, update_index_and_log, write_json
from .card_service import rebuild_material_cards, rebuild_material_library_map
from ...ports.runtime_repositories import artifacts


TASK_MATERIAL_PACK_SCHEMA_VERSION = "product_creative.task_material_pack.v3.4"
MATERIAL_USAGE_SCHEMA_VERSION = "product_creative.material_usage.v3.6"
MATERIAL_FEEDBACK_SCHEMA_VERSION = "product_creative.material_feedback.v3.7"


TASK_PRESETS: Dict[str, Dict[str, Any]] = {
    "video_brief": {
        "preferred_roles": ["video_first_frame", "current_main_image", "product_photo", "generated_candidate", "style_reference"],
        "preferred_usage": ["video_first_frame", "product_reference"],
        "primary_use": "video_first_frame",
    },
    "image_brief": {
        "preferred_roles": ["current_main_image", "product_photo", "detail_image", "generated_candidate", "style_reference"],
        "preferred_usage": ["product_reference", "image_reference"],
        "primary_use": "image_brief",
    },
    "channel_content": {
        "preferred_roles": ["current_main_image", "product_photo", "detail_image", "style_reference", "generated_candidate"],
        "preferred_usage": ["product_reference", "channel_reference"],
        "primary_use": "channel_content",
    },
    "provider_payload": {
        "preferred_roles": ["video_first_frame", "current_main_image", "product_photo", "generated_candidate"],
        "preferred_usage": ["video_reference", "product_reference"],
        "primary_use": "video_first_frame",
        "needs_remote_url": True,
    },
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))


def _json_records(base: Path, folder: str) -> List[Dict[str, Any]]:
    records = artifacts().list(base.name, folder)
    records.sort(key=lambda item: (_text(item.get("created_at")), _text(item.get("material_id") or item.get("material_card_id"))))
    return records


def _card_records(base: Path) -> List[Dict[str, Any]]:
    records = _json_records(base, "material_cards")
    if not records:
        rebuild_material_cards(base.name)
        records = _json_records(base, "material_cards")
    return [item for item in records if _text(item.get("status")) == "active"]


def _feedback_rows(base: Path) -> List[Dict[str, Any]]:
    rows = artifacts().list(base.name, "material_feedback")
    rows.sort(key=lambda item: (_text(item.get("created_at")), _text(item.get("feedback_id"))))
    return rows


def _feedback_score(card: Dict[str, Any], task: str, channel: str, feedback: List[Dict[str, Any]]) -> int:
    material_id = _text(card.get("material_id"))
    score = 0
    for row in feedback:
        if _text(row.get("material_id")) != material_id:
            continue
        if _text(row.get("task")) and _text(row.get("task")) != task:
            continue
        if _text(row.get("channel")) and channel and _text(row.get("channel")) != channel:
            continue
        if row.get("selected"):
            score += 12
        if row.get("rejected"):
            score -= 18
        try:
            rating = int(row.get("rating") or 0)
        except (TypeError, ValueError):
            rating = 0
        if rating:
            score += (rating - 3) * 4
    return score


def _score_card(card: Dict[str, Any], task: str, channel: str, feedback: List[Dict[str, Any]]) -> Dict[str, Any]:
    preset = TASK_PRESETS.get(task, TASK_PRESETS["channel_content"])
    role = _text(card.get("role"))
    usage = {str(item) for item in _list(card.get("usage"))}
    readiness = card.get("readiness") if isinstance(card.get("readiness"), dict) else {}
    recommended = card.get("recommended_use") if isinstance(card.get("recommended_use"), dict) else {}
    reasons: List[str] = []
    warnings: List[str] = []
    score = 0

    if role in preset["preferred_roles"]:
        role_score = max(5, 40 - preset["preferred_roles"].index(role) * 6)
        score += role_score
        reasons.append(f"role matches {role}")
    if usage.intersection(set(preset.get("preferred_usage", []))):
        score += 15
        reasons.append("usage matches task")
    if readiness.get("has_image_analysis"):
        score += 8
        reasons.append("image analysis is available")
    else:
        warnings.append("missing image analysis")
    if readiness.get("has_visual_alignment"):
        score += 8
        reasons.append("visual alignment is available")
    else:
        warnings.append("missing visual alignment")
    if readiness.get("blocked_as_primary_reference"):
        score -= 80
        warnings.append("visual alignment blocks primary reference use")
    if task == "video_brief" and readiness.get("can_video_first_frame"):
        score += 10
        reasons.append("can be used as video first frame")
    if task == "provider_payload" and preset.get("needs_remote_url"):
        if readiness.get("has_remote_url"):
            score += 10
            reasons.append("remote URL is available")
        else:
            score -= 20
            warnings.append("missing remote URL for live provider payload")
    use_value = _text(recommended.get(preset.get("primary_use", "")))
    if use_value == "suitable":
        score += 10
        reasons.append(f"recommended use is suitable for {preset.get('primary_use')}")
    if use_value == "not_recommended":
        score -= 40
        warnings.append(f"not recommended for {preset.get('primary_use')}")

    feedback_delta = _feedback_score(card, task, channel, feedback)
    if feedback_delta:
        score += feedback_delta
        reasons.append(f"material feedback adjusted score by {feedback_delta}")

    return {
        "material_card_id": _text(card.get("material_card_id")),
        "material_id": _text(card.get("material_id")),
        "role": role,
        "score": score,
        "reasons": reasons,
        "warnings": warnings,
        "markdown_path": f"artifacts/material_cards/{_text(card.get('material_card_id'))}.md",
        "stored_path": _text(card.get("image_file")),
        "remote_url": _text(card.get("remote_url")),
        "summary": (card.get("ai_readable_summary") or {}).get("visual_summary", ""),
        "card": card,
    }


def _selected_and_alternates(scored: List[Dict[str, Any]], limit: int) -> Dict[str, List[Dict[str, Any]]]:
    usable = [item for item in scored if item.get("score", 0) > -40]
    selected = usable[: max(1, min(limit, 5))]
    alternates = usable[len(selected): len(selected) + 5]
    return {"selected": selected, "alternates": alternates}


def _pack_markdown(pack: Dict[str, Any]) -> str:
    lines = [
        f"# Task Material Pack: {pack['task_material_pack_id']}",
        "",
        f"Product: {pack['product_id']}",
        f"Task: {pack['task']}",
        f"Channel: {pack.get('channel') or ''}",
        "",
        "## Selected Materials",
        "",
    ]
    for item in pack.get("selected_materials", []):
        lines.append(f"- {item.get('material_id')} ({item.get('role')}) score={item.get('score')} {item.get('markdown_path')}")
        for reason in item.get("reasons", []):
            lines.append(f"  - reason: {reason}")
        for warning in item.get("warnings", []):
            lines.append(f"  - warning: {warning}")
    if not pack.get("selected_materials"):
        lines.append("- None")
    lines.extend(["", "## Missing Requirements", ""])
    lines.extend([f"- {item}" for item in pack.get("missing_requirements", [])] or ["- None"])
    lines.extend(["", "## Not Recommended", ""])
    for item in pack.get("not_recommended", []):
        lines.append(f"- {item.get('material_id')} score={item.get('score')} warnings={'; '.join(item.get('warnings', []))}")
    lines.append("")
    return "\n".join(lines)


def prepare_task_material_pack(
    product_id: str,
    task: str = "channel_content",
    channel: str = "",
    limit: int = 3,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    task = _text(task) or "channel_content"
    if task not in TASK_PRESETS:
        raise ValueError(f"task must be one of: {', '.join(sorted(TASK_PRESETS))}")
    rebuild_material_cards(product_id)
    rebuild_material_library_map(product_id)
    cards = _card_records(base)
    feedback = _feedback_rows(base)
    scored = [_score_card(card, task, _text(channel), feedback) for card in cards]
    scored.sort(key=lambda item: (int(item.get("score") or 0), _text(item.get("material_id"))), reverse=True)
    split = _selected_and_alternates(scored, limit)
    missing: List[str] = []
    if not cards:
        missing.append("material_asset")
    if cards and not split["selected"]:
        missing.append("usable_material_card")
    if task == "provider_payload" and split["selected"] and not any(item.get("remote_url") for item in split["selected"]):
        missing.append("remote_url")
    not_recommended = [item for item in scored if item not in split["selected"] and item.get("score", 0) <= -40]
    pack_id = f"task-material-pack-{timestamp()}"
    pack = {
        "schema_version": TASK_MATERIAL_PACK_SCHEMA_VERSION,
        "task_material_pack_id": pack_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "task": task,
        "channel": _text(channel),
        "selected_materials": [
            {key: value for key, value in item.items() if key != "card"}
            for item in split["selected"]
        ],
        "alternate_materials": [
            {key: value for key, value in item.items() if key != "card"}
            for item in split["alternates"]
        ],
        "not_recommended": [
            {key: value for key, value in item.items() if key != "card"}
            for item in not_recommended
        ],
        "missing_requirements": missing,
        "safety": {
            "mutates_product_brain": False,
            "external_call_performed": False,
            "requires_confirmation": False,
        },
    }
    out_dir = base / "artifacts" / "task_material_packs"
    json_path = out_dir / f"{pack_id}.json"
    md_path = out_dir / f"{pack_id}.md"
    write_json(json_path, pack)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_pack_markdown(pack), encoding="utf-8")
    append_jsonl(
        base / "structured" / "task_material_pack_index.jsonl",
        {
            "task_material_pack_id": pack_id,
            "created_at": pack["created_at"],
            "task": task,
            "channel": _text(channel),
            "selected_material_ids": [item.get("material_id", "") for item in pack["selected_materials"]],
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "task-material-pack", pack_id, [f"Task: {task}", f"Selected: {len(pack['selected_materials'])}"])
    return {
        "success": True,
        "schema_version": TASK_MATERIAL_PACK_SCHEMA_VERSION,
        "product_id": base.name,
        "task_material_pack_id": pack_id,
        "selected_count": len(pack["selected_materials"]),
        "missing_requirements": missing,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "task_material_pack": pack,
        "mutates_product_brain": False,
        "external_call_performed": False,
    }


def _resolve_pack(base: Path, value: str) -> Dict[str, Any]:
    if not value:
        return {}
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("task material pack path must stay inside the product workspace")
        payload = read_json(resolved, {})
        return payload if isinstance(payload, dict) else {}
    name = value if value.endswith(".json") else f"{value}.json"
    path = base / "artifacts" / "task_material_packs" / name
    if path.exists():
        payload = read_json(path, {})
        return payload if isinstance(payload, dict) else {}
    return {}


def material_source_assets_from_pack(pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    assets: List[Dict[str, Any]] = []
    for item in _list(pack.get("selected_materials")):
        if not isinstance(item, dict):
            continue
        assets.append(
            {
                "asset_id": _text(item.get("material_id")),
                "material_id": _text(item.get("material_id")),
                "material_card_id": _text(item.get("material_card_id")),
                "role": _text(item.get("role")),
                "source": "",
                "stored": _text(item.get("stored_path")),
                "remote_url": _text(item.get("remote_url")),
                "missing": False,
                "description": _text(item.get("summary")) or "Selected by task material pack.",
                "task_material_pack_id": _text(pack.get("task_material_pack_id")),
                "use_as": _text(pack.get("task")),
            }
        )
    return assets


def record_material_usage(
    product_id: str,
    task: str = "",
    channel: str = "",
    task_material_pack_id: str = "",
    artifact_id: str = "",
    material_ids: List[str] | None = None,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    pack = _resolve_pack(base, _text(task_material_pack_id))
    selected_ids = [str(item).strip() for item in material_ids or [] if str(item).strip()]
    if not selected_ids and pack:
        selected_ids = [
            _text(item.get("material_id"))
            for item in _list(pack.get("selected_materials"))
            if isinstance(item, dict) and _text(item.get("material_id"))
        ]
    usage_id = f"material-usage-{timestamp()}"
    usage = {
        "schema_version": MATERIAL_USAGE_SCHEMA_VERSION,
        "usage_id": usage_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "task": _text(task) or _text(pack.get("task")),
        "channel": _text(channel) or _text(pack.get("channel")),
        "task_material_pack_id": _text(task_material_pack_id) or _text(pack.get("task_material_pack_id")),
        "artifact_id": _text(artifact_id),
        "used_material_ids": selected_ids,
        "brain_write_policy": {
            "direct_write_to_product_brain": False,
            "requires_human_confirmation_for_learning": True,
        },
    }
    out_dir = base / "artifacts" / "material_usage"
    json_path = out_dir / f"{usage_id}.json"
    md_path = out_dir / f"{usage_id}.md"
    write_json(json_path, usage)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        "\n".join(
            [
                f"# {usage_id}",
                "",
                f"Task: {usage['task']}",
                f"Channel: {usage['channel']}",
                f"Artifact: {usage['artifact_id']}",
                f"Task material pack: {usage['task_material_pack_id']}",
                "",
                "## Used Materials",
                "",
                *[f"- {item}" for item in selected_ids],
                "",
            ]
        ),
        encoding="utf-8",
    )
    append_jsonl(
        base / "structured" / "material_usage_index.jsonl",
        {
            "usage_id": usage_id,
            "created_at": usage["created_at"],
            "task": usage["task"],
            "channel": usage["channel"],
            "task_material_pack_id": usage["task_material_pack_id"],
            "artifact_id": usage["artifact_id"],
            "used_material_ids": selected_ids,
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "material-usage", usage_id, [f"Task: {usage['task']}", f"Materials: {len(selected_ids)}"])
    return {
        "success": True,
        "schema_version": MATERIAL_USAGE_SCHEMA_VERSION,
        "product_id": base.name,
        "usage_id": usage_id,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "usage": usage,
        "mutates_product_brain": False,
        "external_call_performed": False,
    }


def record_material_feedback(
    product_id: str,
    material_id: str,
    note: str,
    task: str = "",
    channel: str = "",
    selected: bool = False,
    rejected: bool = False,
    rating: int | None = None,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    feedback_id = f"material-feedback-{timestamp()}"
    payload = {
        "schema_version": MATERIAL_FEEDBACK_SCHEMA_VERSION,
        "feedback_id": feedback_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "material_id": _text(material_id),
        "task": _text(task),
        "channel": _text(channel),
        "note": _text(note),
        "selected": bool(selected),
        "rejected": bool(rejected),
        "rating": rating,
        "eligible_for_evolution_proposal": bool(note and (selected or rejected or rating)),
        "brain_write_policy": {
            "direct_write_to_product_brain": False,
            "requires_human_confirmation_for_learning": True,
        },
    }
    out_dir = base / "artifacts" / "material_feedback"
    json_path = out_dir / f"{feedback_id}.json"
    md_path = out_dir / f"{feedback_id}.md"
    write_json(json_path, payload)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        "\n".join(
            [
                f"# {feedback_id}",
                "",
                f"Material: {payload['material_id']}",
                f"Task: {payload['task']}",
                f"Channel: {payload['channel']}",
                f"Selected: {payload['selected']}",
                f"Rejected: {payload['rejected']}",
                f"Rating: {payload.get('rating') or ''}",
                "",
                "## Note",
                "",
                payload["note"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    row = {
        "feedback_id": feedback_id,
        "created_at": payload["created_at"],
        "material_id": payload["material_id"],
        "task": payload["task"],
        "channel": payload["channel"],
        "selected": payload["selected"],
        "rejected": payload["rejected"],
        "rating": payload["rating"],
        "note": payload["note"],
        "path": _rel(base, json_path),
        "eligible_for_evolution_proposal": payload["eligible_for_evolution_proposal"],
    }
    append_jsonl(base / "structured" / "material_feedback.jsonl", row)
    update_index_and_log(base, "material-feedback", feedback_id, [f"Material: {payload['material_id']}", f"Selected: {payload['selected']}"])
    return {
        "success": True,
        "schema_version": MATERIAL_FEEDBACK_SCHEMA_VERSION,
        "product_id": base.name,
        "feedback_id": feedback_id,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "feedback": payload,
        "mutates_product_brain": False,
        "external_call_performed": False,
    }
