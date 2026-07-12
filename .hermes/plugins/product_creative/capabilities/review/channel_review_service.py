"""Channel review package service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json
from ...ports.runtime_repositories import artifacts
from .manifest_service import ARTIFACT_MANIFEST_SCHEMA_VERSION, rebuild_artifact_manifest

from .artifact_shared import _list, _rel, _resolve_known_artifact, _text

CHANNEL_REVIEW_PACKAGE_SCHEMA_VERSION = "product_creative.channel_review_package.v2.7"

def _short_text(value: Any, limit: int = 120) -> str:
    text = str(value).strip() if value is not None else ""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

def _string_list(value: Any, limit: int = 5) -> List[str]:
    return [str(item).strip() for item in _list(value) if str(item).strip()][:limit]

def _variant_number(variant: Dict[str, Any]) -> int:
    try:
        return int(variant.get("variant") or 0)
    except (TypeError, ValueError):
        return 0

def _channel_evaluations_by_variant(evaluation: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    items: Dict[int, Dict[str, Any]] = {}
    for item in _list(evaluation.get("variants")):
        if not isinstance(item, dict):
            continue
        try:
            variant = int(item.get("variant") or 0)
        except (TypeError, ValueError):
            continue
        if variant:
            items[variant] = item
    return items

def _find_latest_channel_evaluation(
    base: Path,
    artifact_id: str,
    artifact_rel: str,
) -> Tuple[Path | None, Dict[str, Any]]:
    matches: List[Tuple[str, str, Path, Dict[str, Any]]] = []
    for payload in artifacts().list(base.name, "channel_evaluations"):
        if payload.get("artifact_id") != artifact_id and payload.get("artifact_path") != artifact_rel:
            continue
        path = base / "artifacts" / "channel_evaluations" / f"{payload.get('evaluation_id')}.json"
        matches.append((_text(payload.get("created_at")), path.name, path, payload))
    if not matches:
        return None, {}
    matches.sort(key=lambda item: (item[0], item[1]))
    _, _, path, payload = matches[-1]
    return path, payload

def _resolve_channel_evaluation(
    base: Path,
    evaluation: str,
    artifact_id: str,
    artifact_rel: str,
) -> Tuple[Path | None, Dict[str, Any]]:
    if not evaluation:
        return _find_latest_channel_evaluation(base, artifact_id, artifact_rel)
    path = _resolve_known_artifact(base, evaluation, ["channel_evaluations"])
    payload = read_json(path, {})
    if not isinstance(payload, dict):
        raise ValueError("channel evaluation is not valid JSON")
    eval_artifact_id = _text(payload.get("artifact_id"))
    eval_artifact_path = _text(payload.get("artifact_path"))
    if eval_artifact_id and eval_artifact_id != artifact_id and eval_artifact_path != artifact_rel:
        raise ValueError("channel evaluation does not match the source channel artifact")
    return path, payload

def _channel_variant_summary(target: str, variant: Dict[str, Any]) -> Dict[str, Any]:
    if target == "ecommerce-main-image-copy":
        return {
            "primary": _short_text(variant.get("main_title"), 90),
            "secondary": _short_text(variant.get("subtitle"), 120),
            "highlights": _string_list(variant.get("image_text_suggestions"), 4),
            "brief_seed": _short_text(variant.get("visual_prompt_seed"), 180),
        }
    if target == "xiaohongshu-seeding-note":
        titles = _string_list(variant.get("title_options"), 3)
        return {
            "primary": titles[0] if titles else "",
            "secondary": _short_text(variant.get("opening_hook"), 120),
            "highlights": titles[1:] + _string_list(variant.get("hashtags"), 5),
            "brief_seed": _short_text(variant.get("body"), 220),
        }
    if target == "douyin-short-video-script":
        shots = [item for item in _list(variant.get("shots")) if isinstance(item, dict)]
        captions = _string_list([item.get("caption") for item in shots], 4)
        return {
            "primary": _short_text(variant.get("hook_0_3s"), 120),
            "secondary": f"{len(shots)} shot(s); CTA: {_short_text(variant.get('cta'), 60)}",
            "highlights": captions,
            "brief_seed": _short_text(variant.get("video_brief_seed"), 220),
        }
    return {
        "primary": _short_text(variant.get("style"), 90),
        "secondary": "",
        "highlights": [],
        "brief_seed": "",
    }

def _channel_feedback_command(product_id: str, artifact_id: str, variant: int | None) -> str:
    parts = [
        r".\.hermes\plugins\product_creative\scripts\product_creative.ps1",
        "channel-feedback",
        "--id",
        product_id,
        "--artifact",
        artifact_id,
    ]
    if variant:
        parts.extend(["--variant", str(variant)])
    parts.extend(
        [
            "--selected",
            "--rating",
            "5",
            "--allow-evolve",
            "--note",
            '"your review note"',
            "--channel-fit",
            "5",
            "--factuality",
            "5",
            "--tone-fit",
            "5",
            "--actionability",
            "5",
        ]
    )
    return " ".join(parts)

def _channel_next_actions(product_id: str, artifact_id: str, variant: int | None) -> Dict[str, Any]:
    command = _channel_feedback_command(product_id, artifact_id, variant)
    return {
        "record_selected_feedback": {
            "command": command,
            "source_artifact_id": artifact_id,
            "suggested_variant": variant,
            "requires_user_note": True,
            "creates_evolution_eligible_feedback": True,
            "mutates_product_brain": False,
        },
        "create_evolution_proposal": {
            "command": rf".\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id {product_id}",
            "requires_recorded_feedback": True,
            "mutates_product_brain": False,
        },
        "apply_evolution_proposal": {
            "command_template": rf".\.hermes\plugins\product_creative\scripts\product_creative.ps1 evolve --id {product_id} --apply <proposal-id>",
            "requires_human_confirmation": True,
            "mutates_product_brain": True,
        },
    }

def _md_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", "<br>")

def _channel_review_markdown(package: Dict[str, Any]) -> str:
    summary = package.get("summary", {})
    lines = [
        f"# Channel Review Package {package['channel_review_package_id']}",
        "",
        f"Product: {package['product_id']}",
        f"Target: {package['target']}",
        f"Artifact: {package['source_artifact_id']}",
        f"Evaluation: {package.get('source_evaluation_id') or 'not attached'}",
        "",
        "## Summary",
        "",
        f"- Status: {package['status']}",
        f"- Variant count: {summary.get('variant_count')}",
        f"- Best variant: {summary.get('best_variant') or 'not available'}",
        f"- Evaluation status: {summary.get('evaluation_status')}",
        f"- Overall score: {summary.get('overall_score') if summary.get('overall_score') is not None else 'not available'}",
        "",
        "## Variants",
        "",
        "| Variant | Style | Score | Recommendation | Summary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in package.get("items", []):
        score = item.get("evaluation", {}).get("total_score")
        recommendation = item.get("evaluation", {}).get("recommendation", "")
        variant_summary = item.get("summary", {})
        summary_text = " / ".join(
            part
            for part in [
                variant_summary.get("primary"),
                variant_summary.get("secondary"),
                "; ".join(variant_summary.get("highlights") or []),
            ]
            if part
        )
        lines.append(
            f"| {item.get('variant')} | {_md_cell(item.get('style'))} | "
            f"{score if score is not None else ''} | {_md_cell(recommendation)} | {_md_cell(summary_text)} |"
        )
    lines.extend(["", "## Review Checklist", ""])
    lines.extend(f"- {item}" for item in package.get("review_checklist", []))
    lines.extend(["", "## Feedback Command", "", "```powershell"])
    command = (
        package.get("next_actions", {})
        .get("record_selected_feedback", {})
        .get("command", package.get("feedback_commands", {}).get("selected_variant", ""))
    )
    lines.append(command)
    lines.extend(["```", ""])
    return "\n".join(lines)

def create_channel_review_package(product_id: str, artifact: str, evaluation: str = "") -> Dict[str, Any]:
    base = ensure_product(product_id)
    artifact_path = _resolve_known_artifact(base, artifact, ["channel_content"])
    artifact_payload = read_json(artifact_path, {})
    target = _text(artifact_payload.get("target"))
    if target not in {"ecommerce-main-image-copy", "xiaohongshu-seeding-note", "douyin-short-video-script"}:
        raise ValueError("channel review package requires a channel_content artifact")

    artifact_id = _text(artifact_payload.get("artifact_id")) or artifact_path.stem
    artifact_rel = _rel(base, artifact_path)
    evaluation_path, evaluation_payload = _resolve_channel_evaluation(base, evaluation, artifact_id, artifact_rel)
    eval_by_variant = _channel_evaluations_by_variant(evaluation_payload)
    eval_summary = evaluation_payload.get("summary") if isinstance(evaluation_payload.get("summary"), dict) else {}
    best_variant = eval_summary.get("best_variant")
    try:
        clean_best_variant = int(best_variant) if best_variant is not None else None
    except (TypeError, ValueError):
        clean_best_variant = None

    variants = [item for item in _list(artifact_payload.get("variants")) if isinstance(item, dict)]
    items: List[Dict[str, Any]] = []
    for variant in variants:
        variant_number = _variant_number(variant)
        evaluation_item = eval_by_variant.get(variant_number, {})
        issues = evaluation_item.get("issues") if isinstance(evaluation_item.get("issues"), list) else []
        items.append(
            {
                "variant": variant_number,
                "style": _text(variant.get("style")),
                "summary": _channel_variant_summary(target, variant),
                "evaluation": {
                    "total_score": evaluation_item.get("total_score"),
                    "recommendation": _text(evaluation_item.get("recommendation")),
                    "issue_count": len(issues),
                    "strengths": _string_list(evaluation_item.get("strengths"), 5),
                    "issues": _string_list(issues, 5),
                },
                "is_best_candidate": bool(clean_best_variant and variant_number == clean_best_variant),
                "feedback_command": _channel_feedback_command(base.name, artifact_id, variant_number),
            }
        )

    if clean_best_variant is None and items:
        clean_best_variant = items[0]["variant"]

    package_id = f"channel-review-pack-{timestamp()}"
    evaluation_id = _text(evaluation_payload.get("evaluation_id"))
    evaluation_rel = _rel(base, evaluation_path) if evaluation_path else ""
    package = {
        "schema_version": CHANNEL_REVIEW_PACKAGE_SCHEMA_VERSION,
        "channel_review_package_id": package_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": "ready_for_channel_review",
        "target": target,
        "source_artifact_id": artifact_id,
        "source_artifact_path": artifact_rel,
        "source_evaluation_id": evaluation_id,
        "source_evaluation_path": evaluation_rel,
        "summary": {
            "variant_count": len(items),
            "best_variant": clean_best_variant,
            "evaluation_status": eval_summary.get("status") or "not_attached",
            "overall_score": eval_summary.get("overall_score"),
            "grounding_warning_count": int(artifact_payload.get("grounding_audit", {}).get("warning_count") or 0),
            "next_actions": [
                "Review the best candidate and at least one alternative.",
                "Record explicit channel feedback before Product Brain evolution.",
                "Run channel-evaluate first if this package has no attached evaluation.",
            ],
        },
        "items": items,
        "review_checklist": [
            "Does the variant preserve verified product facts only?",
            "Does the tone fit the selected channel?",
            "Is the main product memory point clear enough?",
            "Is the output specific enough for the next image/video prompt step?",
            "What should be repeated or avoided in future generations?",
        ],
        "feedback_commands": {
            "selected_variant": _channel_feedback_command(base.name, artifact_id, clean_best_variant),
        },
        "next_actions": _channel_next_actions(base.name, artifact_id, clean_best_variant),
        "requires_human_selection": True,
        "mutates_product_brain": False,
    }

    out_dir = base / "artifacts" / "channel_review_packages"
    json_path = out_dir / f"{package_id}.json"
    md_path = out_dir / f"{package_id}.md"
    write_json(json_path, package)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_channel_review_markdown(package), encoding="utf-8")
    append_jsonl(
        base / "structured" / "channel_review_package_index.jsonl",
        {
            "channel_review_package_id": package_id,
            "artifact_id": artifact_id,
            "evaluation_id": evaluation_id,
            "target": target,
            "created_at": package["created_at"],
            "best_variant": clean_best_variant,
            "json": str(json_path.relative_to(base)),
            "markdown": str(md_path.relative_to(base)),
        },
    )
    update_index_and_log(
        base,
        "channel-review-package",
        package_id,
        [str(json_path.relative_to(base)), f"Best variant: {clean_best_variant or 'not available'}"],
    )
    return {
        "success": True,
        "product_id": base.name,
        "channel_review_package_id": package_id,
        "target": target,
        "artifact_id": artifact_id,
        "evaluation_id": evaluation_id,
        "best_variant": clean_best_variant,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "channel_review_package": package,
    }
