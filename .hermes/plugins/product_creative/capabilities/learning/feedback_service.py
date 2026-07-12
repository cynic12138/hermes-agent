"""Artifact feedback writers for Product Creative review loops."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, read_json, timestamp, update_index_and_log, write_json


RESULT_FEEDBACK_SCHEMA_VERSION = "product_creative.result_feedback.v7.3"
CHANNEL_FEEDBACK_SCHEMA_VERSION = "product_creative.channel_feedback.v3.0"
VIDEO_BRIEF_FEEDBACK_SCHEMA_VERSION = "product_creative.video_brief_feedback.v2.29"

__all__ = [
    "CHANNEL_FEEDBACK_SCHEMA_VERSION",
    "RESULT_FEEDBACK_SCHEMA_VERSION",
    "VIDEO_BRIEF_FEEDBACK_SCHEMA_VERSION",
    "record_channel_feedback",
    "record_result_feedback",
    "record_video_brief_feedback",
]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))


def _resolve_known_artifact(base: Path, value: str, folders: List[str]) -> Path:
    if not value:
        raise ValueError("artifact id or path is required")
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("artifact path must stay inside the product workspace")
        return resolved

    name = value if value.endswith(".json") else f"{value}.json"
    for folder in folders:
        path = base / "artifacts" / folder / name
        if path.exists():
            return path.resolve()
    raise FileNotFoundError(f"artifact '{value}' does not exist")


def _feedback_markdown(feedback: Dict[str, Any]) -> str:
    lines = [
        f"# {feedback['feedback_id']}",
        "",
        f"Result: {feedback['source_result_id']}",
        f"Selected: {feedback['selected']}",
        f"Rating: {feedback.get('rating') or ''}",
        f"Ready for evolution: {feedback['eligible_for_evolution_proposal']}",
        "",
        "## Note",
        "",
        feedback.get("note", ""),
        "",
        "## Issues",
        "",
    ]
    lines.extend([f"- {item}" for item in feedback.get("issues", [])] or ["- None"])
    lines.extend(["", "## Like Reasons", ""])
    lines.extend([f"- {item}" for item in feedback.get("like_reasons", [])] or ["- None"])
    lines.extend(["", "## Quality Scores", ""])
    scores = feedback.get("quality_scores") or {}
    lines.extend([f"- {key}: {value}" for key, value in scores.items()] or ["- None"])
    lines.extend(["", "## Dislike Reasons", ""])
    lines.extend([f"- {item}" for item in feedback.get("dislike_reasons", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def _clean_quality_scores(scores: Dict[str, Any] | None) -> Dict[str, int]:
    allowed = [
        "subject_clarity",
        "product_recognizability",
        "composition",
        "style_fit",
        "copy_fit",
        "packaging_fidelity",
        "text_control",
        "motion_quality",
        "scene_fit",
        "first_frame_consistency",
        "factuality",
    ]
    clean: Dict[str, int] = {}
    for key in allowed:
        value = (scores or {}).get(key)
        if value is None:
            continue
        clean[key] = max(1, min(int(value), 5))
    return clean


def record_result_feedback(
    product_id: str,
    result: str,
    note: str,
    selected: bool = False,
    rating: int | None = None,
    issues: List[str] | None = None,
    allow_evolve: bool = False,
    quality_scores: Dict[str, Any] | None = None,
    like_reasons: List[str] | None = None,
    dislike_reasons: List[str] | None = None,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    result_path = _resolve_known_artifact(base, result, ["generated_images", "generated_videos"])
    result_payload = read_json(result_path, {})
    clean_rating = None
    if rating is not None:
        clean_rating = max(1, min(int(rating), 5))
    clean_scores = _clean_quality_scores(quality_scores)
    average_score = round(sum(clean_scores.values()) / len(clean_scores), 2) if clean_scores else None
    clean_like_reasons = [str(item) for item in like_reasons or [] if str(item).strip()]
    clean_dislike_reasons = [str(item) for item in dislike_reasons or [] if str(item).strip()]
    ready_for_feedback = bool(result_payload.get("review", {}).get("ready_for_feedback"))
    feedback_id = f"result-feedback-{timestamp()}"
    feedback = {
        "schema_version": RESULT_FEEDBACK_SCHEMA_VERSION,
        "feedback_id": feedback_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "source_result_id": result_payload.get("result_id", result_path.stem),
        "source_result_path": _rel(base, result_path),
        "job_id": result_payload.get("job_id", ""),
        "brief_type": result_payload.get("brief_type", ""),
        "provider": result_payload.get("provider", ""),
        "result_ready_for_feedback": ready_for_feedback,
        "selected": bool(selected),
        "rating": clean_rating,
        "issues": [str(item) for item in issues or [] if str(item).strip()],
        "quality_scores": clean_scores,
        "average_quality_score": average_score,
        "like_reasons": clean_like_reasons,
        "dislike_reasons": clean_dislike_reasons,
        "note": note or "",
        "allow_product_brain_evolution": bool(allow_evolve),
        "eligible_for_evolution_proposal": bool(ready_for_feedback and allow_evolve and selected),
        "status": "recorded",
    }
    out_dir = base / "artifacts" / "result_feedback"
    json_path = out_dir / f"{feedback_id}.json"
    md_path = out_dir / f"{feedback_id}.md"
    feedback["feedback_path"] = _rel(base, json_path)
    write_json(json_path, feedback)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_feedback_markdown(feedback), encoding="utf-8")
    append_jsonl(base / "structured" / "result_feedback.jsonl", feedback)
    update_index_and_log(base, "result-feedback", feedback_id, [str(json_path.relative_to(base))])
    return {
        "success": True,
        "product_id": base.name,
        "feedback_id": feedback_id,
        "eligible_for_evolution_proposal": feedback["eligible_for_evolution_proposal"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "feedback": feedback,
    }


def _channel_feedback_markdown(feedback: Dict[str, Any]) -> str:
    lines = [
        f"# {feedback['feedback_id']}",
        "",
        f"Target: {feedback['target']}",
        f"Artifact: {feedback['source_artifact_id']}",
        f"Variant: {feedback.get('variant') or ''}",
        f"Selected: {feedback['selected']}",
        f"Rating: {feedback.get('rating') or ''}",
        f"Ready for evolution: {feedback['eligible_for_evolution_proposal']}",
        "",
        "## Note",
        "",
        feedback.get("note", ""),
        "",
        "## Like Reasons",
        "",
    ]
    lines.extend([f"- {item}" for item in feedback.get("like_reasons", [])] or ["- None"])
    lines.extend(["", "## Dislike Reasons", ""])
    lines.extend([f"- {item}" for item in feedback.get("dislike_reasons", [])] or ["- None"])
    lines.extend(["", "## Issues", ""])
    lines.extend([f"- {item}" for item in feedback.get("issues", [])] or ["- None"])
    lines.extend(["", "## Quality Scores", ""])
    scores = feedback.get("quality_scores") or {}
    lines.extend([f"- {key}: {value}" for key, value in scores.items()] or ["- None"])
    lines.extend(["", "## Channel Performance", ""])
    metrics = feedback.get("performance_metrics") or {}
    lines.extend([f"- {key}: {value}" for key, value in metrics.items()] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def _clean_channel_quality_scores(scores: Dict[str, Any] | None) -> Dict[str, int]:
    allowed = [
        "channel_fit",
        "factuality",
        "tone_fit",
        "actionability",
    ]
    clean: Dict[str, int] = {}
    for key in allowed:
        value = (scores or {}).get(key)
        if value is None:
            continue
        clean[key] = max(1, min(int(value), 5))
    return clean


def _clean_performance_metrics(metrics: Dict[str, Any] | None) -> Dict[str, float]:
    clean: Dict[str, float] = {}
    for key in ("impressions", "views", "clicks", "likes", "saves", "shares", "comments", "conversions", "spend", "revenue"):
        value = (metrics or {}).get(key)
        if value is None:
            continue
        clean[key] = max(0.0, float(value))
    views = clean.get("views") or clean.get("impressions") or 0.0
    engagements = sum(clean.get(key, 0.0) for key in ("likes", "saves", "shares", "comments"))
    if views:
        clean["engagement_rate"] = round(engagements / views, 6)
        clean["click_through_rate"] = round(clean.get("clicks", 0.0) / views, 6)
    denominator = clean.get("clicks") or views
    if denominator:
        clean["conversion_rate"] = round(clean.get("conversions", 0.0) / denominator, 6)
    if clean.get("spend"):
        clean["return_on_ad_spend"] = round(clean.get("revenue", 0.0) / clean["spend"], 4)
    return clean


def _clean_video_brief_quality_scores(scores: Dict[str, Any] | None) -> Dict[str, int]:
    allowed = [
        "hook_strength",
        "storyboard_clarity",
        "product_grounding",
        "prompt_specificity",
        "channel_fit",
        "factuality",
    ]
    clean: Dict[str, int] = {}
    for key in allowed:
        value = (scores or {}).get(key)
        if value is None:
            continue
        clean[key] = max(1, min(int(value), 5))
    return clean


def _variant_exists(artifact_payload: Dict[str, Any], variant: int | None) -> bool:
    if variant is None:
        return True
    return any(int(item.get("variant") or 0) == int(variant) for item in _list(artifact_payload.get("variants")))


def record_channel_feedback(
    product_id: str,
    artifact: str,
    note: str,
    selected: bool = False,
    variant: int | None = None,
    rating: int | None = None,
    issues: List[str] | None = None,
    like_reasons: List[str] | None = None,
    dislike_reasons: List[str] | None = None,
    allow_evolve: bool = False,
    quality_scores: Dict[str, Any] | None = None,
    performance_metrics: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    artifact_path = _resolve_known_artifact(base, artifact, ["channel_content"])
    artifact_payload = read_json(artifact_path, {})
    target = _text(artifact_payload.get("target"))
    if target not in {"ecommerce-main-image-copy", "xiaohongshu-seeding-note", "douyin-short-video-script"}:
        raise ValueError("channel feedback requires a channel_content artifact")
    clean_variant = int(variant) if variant else None
    if not _variant_exists(artifact_payload, clean_variant):
        raise ValueError(f"variant {clean_variant} does not exist in artifact")
    clean_rating = None
    if rating is not None:
        clean_rating = max(1, min(int(rating), 5))
    clean_scores = _clean_channel_quality_scores(quality_scores)
    average_score = round(sum(clean_scores.values()) / len(clean_scores), 2) if clean_scores else None
    clean_performance = _clean_performance_metrics(performance_metrics)
    feedback_id = f"channel-feedback-{timestamp()}"
    feedback = {
        "schema_version": CHANNEL_FEEDBACK_SCHEMA_VERSION,
        "feedback_id": feedback_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "target": target,
        "source_artifact_id": artifact_payload.get("artifact_id", artifact_path.stem),
        "source_artifact_path": _rel(base, artifact_path),
        "variant": clean_variant,
        "selected": bool(selected),
        "rating": clean_rating,
        "quality_scores": clean_scores,
        "average_quality_score": average_score,
        "performance_metrics": clean_performance,
        "like_reasons": [str(item) for item in like_reasons or [] if str(item).strip()],
        "dislike_reasons": [str(item) for item in dislike_reasons or [] if str(item).strip()],
        "issues": [str(item) for item in issues or [] if str(item).strip()],
        "note": note or "",
        "allow_product_brain_evolution": bool(allow_evolve),
        "eligible_for_evolution_proposal": bool(allow_evolve and selected),
        "status": "recorded",
    }
    out_dir = base / "artifacts" / "channel_feedback"
    json_path = out_dir / f"{feedback_id}.json"
    md_path = out_dir / f"{feedback_id}.md"
    feedback["source_feedback_path"] = str(json_path.relative_to(base))
    write_json(json_path, feedback)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_channel_feedback_markdown(feedback), encoding="utf-8")
    append_jsonl(base / "structured" / "channel_feedback.jsonl", feedback)
    update_index_and_log(base, "channel-feedback", feedback_id, [str(json_path.relative_to(base))])
    return {
        "success": True,
        "product_id": base.name,
        "feedback_id": feedback_id,
        "eligible_for_evolution_proposal": feedback["eligible_for_evolution_proposal"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "feedback": feedback,
    }


def _video_brief_feedback_markdown(feedback: Dict[str, Any]) -> str:
    lines = [
        f"# {feedback['feedback_id']}",
        "",
        f"Brief: {feedback['source_brief_id']}",
        f"Selected: {feedback['selected']}",
        f"Rating: {feedback.get('rating') or ''}",
        f"Ready for evolution: {feedback['eligible_for_evolution_proposal']}",
        "",
        "## Note",
        "",
        feedback.get("note", ""),
        "",
        "## Like Reasons",
        "",
    ]
    lines.extend([f"- {item}" for item in feedback.get("like_reasons", [])] or ["- None"])
    lines.extend(["", "## Dislike Reasons", ""])
    lines.extend([f"- {item}" for item in feedback.get("dislike_reasons", [])] or ["- None"])
    lines.extend(["", "## Issues", ""])
    lines.extend([f"- {item}" for item in feedback.get("issues", [])] or ["- None"])
    lines.extend(["", "## Quality Scores", ""])
    scores = feedback.get("quality_scores") or {}
    lines.extend([f"- {key}: {value}" for key, value in scores.items()] or ["- None"])
    lines.append("")
    return "\n".join(lines)


def record_video_brief_feedback(
    product_id: str,
    brief: str,
    note: str,
    selected: bool = False,
    rating: int | None = None,
    issues: List[str] | None = None,
    like_reasons: List[str] | None = None,
    dislike_reasons: List[str] | None = None,
    allow_evolve: bool = False,
    quality_scores: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    brief_path = _resolve_known_artifact(base, brief, ["video_scripts"])
    brief_payload = read_json(brief_path, {})
    if brief_payload.get("brief_type") != "video":
        raise ValueError("video brief feedback requires a video brief")
    clean_rating = None
    if rating is not None:
        clean_rating = max(1, min(int(rating), 5))
    clean_scores = _clean_video_brief_quality_scores(quality_scores)
    average_score = round(sum(clean_scores.values()) / len(clean_scores), 2) if clean_scores else None
    feedback_id = f"video-brief-feedback-{timestamp()}"
    feedback = {
        "schema_version": VIDEO_BRIEF_FEEDBACK_SCHEMA_VERSION,
        "feedback_id": feedback_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "source_brief_id": brief_payload.get("brief_id", brief_path.stem),
        "source_brief_path": _rel(base, brief_path),
        "source_intent_id": brief_payload.get("source_intent_id", ""),
        "brief_status": brief_payload.get("status", ""),
        "target": (brief_payload.get("target") or {}).get("platform", ""),
        "selected": bool(selected),
        "rating": clean_rating,
        "quality_scores": clean_scores,
        "average_quality_score": average_score,
        "like_reasons": [str(item) for item in like_reasons or [] if str(item).strip()],
        "dislike_reasons": [str(item) for item in dislike_reasons or [] if str(item).strip()],
        "issues": [str(item) for item in issues or [] if str(item).strip()],
        "note": note or "",
        "allow_product_brain_evolution": bool(allow_evolve),
        "eligible_for_evolution_proposal": bool(allow_evolve and selected),
        "status": "recorded",
    }
    out_dir = base / "artifacts" / "video_brief_feedback"
    json_path = out_dir / f"{feedback_id}.json"
    md_path = out_dir / f"{feedback_id}.md"
    feedback["source_feedback_path"] = str(json_path.relative_to(base))
    write_json(json_path, feedback)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_video_brief_feedback_markdown(feedback), encoding="utf-8")
    append_jsonl(base / "structured" / "video_brief_feedback.jsonl", feedback)
    update_index_and_log(base, "video-brief-feedback", feedback_id, [str(json_path.relative_to(base))])
    return {
        "success": True,
        "product_id": base.name,
        "feedback_id": feedback_id,
        "eligible_for_evolution_proposal": feedback["eligible_for_evolution_proposal"],
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "feedback": feedback,
    }
