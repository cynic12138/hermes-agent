"""Channel content evaluation service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, today, update_index_and_log, write_json

from .evaluation_shared import _clip_score, _list, _resolve_channel_artifact_path, _score_text_length, _text

CHANNEL_EVALUATION_SCHEMA_VERSION = "product_creative.channel_evaluation.v2.4"

CHANNEL_TARGETS = {
    "ecommerce-main-image-copy",
    "xiaohongshu-seeding-note",
    "douyin-short-video-script",
}

def _channel_grounding_issues(artifact: Dict[str, Any], variant: int) -> List[Dict[str, Any]]:
    warnings = artifact.get("grounding_audit", {}).get("warnings") or []
    return [item for item in warnings if item.get("variant") in {variant, str(variant), None}]

def _base_channel_scores(pack: Dict[str, Any], artifact: Dict[str, Any]) -> Tuple[int, List[str], List[str]]:
    variant = int(pack.get("variant") or 0)
    issues: List[str] = []
    strengths: List[str] = []
    score = 0
    if _text(pack.get("style")):
        score += 5
    else:
        issues.append("Missing style")
    if _list(pack.get("avoid_claims")):
        score += 5
        strengths.append("Includes avoid-claims guardrails.")
    else:
        issues.append("Missing avoid_claims")
    notes = pack.get("generation_notes") or {}
    if bool(notes.get("requires_human_review", True)):
        score += 5
    if _text(notes.get("basis")):
        score += 5
    grounding_issues = _channel_grounding_issues(artifact, variant)
    if grounding_issues:
        issues.extend(f"Grounding warning: {item.get('term')}" for item in grounding_issues)
    else:
        score += 20
        strengths.append("No grounding warnings after lite audit.")
    return score, issues, strengths

def _score_ecommerce_channel(pack: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    score, issues, strengths = _base_channel_scores(pack, artifact)
    scores = {"structure": score, "channel_fit": 0, "actionability": 0}
    required = [
        ("main_title", _text(pack.get("main_title"))),
        ("subtitle", _text(pack.get("subtitle"))),
        ("selling_point_lines", _list(pack.get("selling_point_lines"))),
        ("image_text_suggestions", _list(pack.get("image_text_suggestions"))),
        ("visual_prompt_seed", _text(pack.get("visual_prompt_seed"))),
    ]
    present = sum(1 for _name, value in required if bool(value))
    scores["structure"] += round(present / len(required) * 20)
    for name, value in required:
        if not value:
            issues.append(f"Missing required field: {name}")

    title = _text(pack.get("main_title"))
    subtitle = _text(pack.get("subtitle"))
    prompt = _text(pack.get("visual_prompt_seed"))
    title_score, reason = _score_text_length(title, 4, 30, 8)
    scores["channel_fit"] += title_score
    if reason:
        issues.append(f"Main title {reason}")
    subtitle_score, reason = _score_text_length(subtitle, 8, 56, 6)
    scores["channel_fit"] += subtitle_score
    if reason:
        issues.append(f"Subtitle {reason}")
    scores["channel_fit"] += 6 if 1 <= len(_list(pack.get("image_text_suggestions"))) <= 4 else 2
    scores["actionability"] += 10 if len(prompt) >= 40 else 4
    scores["actionability"] += 10 if any(word in prompt for word in ["主体", "背景", "构图", "风格"]) else 3
    if scores["channel_fit"] >= 16:
        strengths.append("Main image copy is concise enough for visual use.")
    return _channel_eval_result(pack, scores, issues, strengths)

def _score_xiaohongshu_channel(pack: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    score, issues, strengths = _base_channel_scores(pack, artifact)
    scores = {"structure": score, "channel_fit": 0, "actionability": 0}
    required = [
        ("title_options", _list(pack.get("title_options"))),
        ("opening_hook", _text(pack.get("opening_hook"))),
        ("body", _text(pack.get("body"))),
        ("selling_point_mapping", _list(pack.get("selling_point_mapping"))),
        ("tone", _text(pack.get("tone"))),
        ("hashtags", _list(pack.get("hashtags"))),
    ]
    present = sum(1 for _name, value in required if bool(value))
    scores["structure"] += round(present / len(required) * 20)
    for name, value in required:
        if not value:
            issues.append(f"Missing required field: {name}")

    body = _text(pack.get("body"))
    hook = _text(pack.get("opening_hook"))
    title_count = len(_list(pack.get("title_options")))
    tag_count = len(_list(pack.get("hashtags")))
    scores["channel_fit"] += 6 if title_count >= 2 else 2
    hook_score, reason = _score_text_length(hook, 8, 80, 6)
    scores["channel_fit"] += hook_score
    if reason:
        issues.append(f"Opening hook {reason}")
    body_score, reason = _score_text_length(body, 80, 800, 10)
    scores["channel_fit"] += body_score
    if reason:
        issues.append(f"Body {reason}")
    ad_words = ["立刻下单", "全网最低", "必买", "爆款"]
    if any(word in body for word in ad_words):
        issues.append("Body may feel too promotional for Xiaohongshu.")
    else:
        scores["channel_fit"] += 4
        strengths.append("No obvious hard-sell phrase detected.")
    scores["actionability"] += 8 if tag_count >= 2 else 3
    scores["actionability"] += 12 if len(_list(pack.get("selling_point_mapping"))) >= 2 else 4
    return _channel_eval_result(pack, scores, issues, strengths)

def _score_douyin_channel(pack: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    score, issues, strengths = _base_channel_scores(pack, artifact)
    scores = {"structure": score, "channel_fit": 0, "actionability": 0}
    shots = _list(pack.get("shots"))
    required = [
        ("hook_0_3s", _text(pack.get("hook_0_3s"))),
        ("shots", shots),
        ("product_exposure_points", _list(pack.get("product_exposure_points"))),
        ("cta", _text(pack.get("cta"))),
        ("video_brief_seed", _text(pack.get("video_brief_seed"))),
    ]
    present = sum(1 for _name, value in required if bool(value))
    scores["structure"] += round(present / len(required) * 20)
    for name, value in required:
        if not value:
            issues.append(f"Missing required field: {name}")

    hook_score, reason = _score_text_length(_text(pack.get("hook_0_3s")), 8, 70, 8)
    scores["channel_fit"] += hook_score
    if reason:
        issues.append(f"Hook {reason}")
    if 3 <= len(shots) <= 6:
        scores["channel_fit"] += 8
        strengths.append("Shot count is usable for a short-video draft.")
    else:
        scores["channel_fit"] += 3
        issues.append(f"Shot count {len(shots)} outside 3-6")
    complete_shots = 0
    for shot in shots:
        if all(_text(shot.get(key)) for key in ["duration", "visual", "voiceover", "caption"]):
            complete_shots += 1
    scores["channel_fit"] += round((complete_shots / max(1, len(shots))) * 8)
    prompt = _text(pack.get("video_brief_seed"))
    scores["actionability"] += 10 if len(prompt) >= 40 else 4
    scores["actionability"] += 10 if len(_list(pack.get("product_exposure_points"))) >= 2 else 4
    return _channel_eval_result(pack, scores, issues, strengths)

def _channel_eval_result(
    pack: Dict[str, Any],
    scores: Dict[str, int],
    issues: List[str],
    strengths: List[str],
) -> Dict[str, Any]:
    total = _clip_score(sum(scores.values()))
    if total >= 85:
        recommendation = "ready_for_human_review"
    elif total >= 70:
        recommendation = "minor_revision"
    else:
        recommendation = "needs_revision"
    return {
        "variant": int(pack.get("variant") or 0),
        "style": pack.get("style", ""),
        "total_score": total,
        "scores": scores,
        "recommendation": recommendation,
        "strengths": strengths,
        "issues": issues,
    }

def _score_channel_variant(pack: Dict[str, Any], artifact: Dict[str, Any], target: str) -> Dict[str, Any]:
    if target == "ecommerce-main-image-copy":
        return _score_ecommerce_channel(pack, artifact)
    if target == "xiaohongshu-seeding-note":
        return _score_xiaohongshu_channel(pack, artifact)
    if target == "douyin-short-video-script":
        return _score_douyin_channel(pack, artifact)
    raise ValueError(f"unsupported channel target '{target}'")

def _channel_summary(variant_evals: List[Dict[str, Any]], artifact: Dict[str, Any]) -> Dict[str, Any]:
    if not variant_evals:
        return {
            "overall_score": 0,
            "status": "needs_revision",
            "best_variant": None,
            "next_actions": ["Generate at least one channel variant before evaluation."],
        }
    overall = round(sum(item["total_score"] for item in variant_evals) / len(variant_evals))
    best = max(variant_evals, key=lambda item: item["total_score"])
    warning_count = int(artifact.get("grounding_audit", {}).get("warning_count") or 0)
    if warning_count:
        status = "blocked_by_grounding"
    elif overall >= 85:
        status = "ready_for_human_review"
    elif overall >= 70:
        status = "minor_revision"
    else:
        status = "needs_revision"
    next_actions = []
    if warning_count:
        next_actions.append("Resolve grounding warnings before using this channel artifact.")
    next_actions.append("Ask the user to choose a preferred variant and record channel feedback.")
    if status in {"minor_revision", "needs_revision"}:
        next_actions.append("Regenerate or revise low-scoring variants before applying Product Brain learning.")
    return {
        "overall_score": overall,
        "status": status,
        "best_variant": best.get("variant"),
        "next_actions": next_actions,
    }

def _channel_evaluation_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        f"# Channel Evaluation {payload['evaluation_id']}",
        "",
        f"Product: {payload['product_id']}",
        f"Target: {payload['target']}",
        f"Artifact: {payload['artifact_id']}",
        "",
        "## Summary",
        "",
        f"- Overall score: {payload['summary']['overall_score']}",
        f"- Status: {payload['summary']['status']}",
        f"- Best variant: {payload['summary']['best_variant']}",
        "",
        "## Variants",
        "",
    ]
    for item in payload["variants"]:
        lines.extend(
            [
                f"### Variant {item['variant']} - {item.get('style', '')}",
                "",
                f"- Score: {item['total_score']}",
                f"- Recommendation: {item['recommendation']}",
                f"- Issues: {len(item['issues'])}",
                "",
            ]
        )
    lines.extend(["## Next Actions", ""])
    lines.extend(f"- {item}" for item in payload["summary"]["next_actions"])
    lines.append("")
    return "\n".join(lines)

def evaluate_channel_content(product_id: str, artifact: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    artifact_path = _resolve_channel_artifact_path(base, artifact)
    artifact_payload = read_json(artifact_path, {})
    if not artifact_payload:
        raise ValueError(f"artifact '{artifact}' is not valid JSON")
    target = artifact_payload.get("target")
    if target not in CHANNEL_TARGETS:
        raise ValueError("M2.4 only evaluates channel_content artifacts")
    variant_evals = [
        _score_channel_variant(pack, artifact_payload, target)
        for pack in artifact_payload.get("variants", [])
    ]
    summary = _channel_summary(variant_evals, artifact_payload)
    evaluation_id = f"channel-eval-{timestamp()}"
    eval_path = base / "artifacts" / "channel_evaluations" / f"{evaluation_id}.json"
    md_path = base / "artifacts" / "channel_evaluations" / f"{evaluation_id}.md"
    artifact_rel = str(artifact_path.relative_to(base))
    payload = {
        "schema_version": CHANNEL_EVALUATION_SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "product_id": base.name,
        "target": target,
        "artifact_id": artifact_payload.get("artifact_id") or artifact_path.stem,
        "artifact_path": artifact_rel,
        "created_at": now_iso(),
        "evaluation_method": "rule-channel-evaluator-v2.4",
        "summary": summary,
        "grounding_audit": artifact_payload.get("grounding_audit", {}),
        "variants": variant_evals,
        "requires_human_review": True,
    }
    write_json(eval_path, payload)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_channel_evaluation_markdown(payload), encoding="utf-8")
    append_jsonl(
        base / "structured" / "channel_evaluation_index.jsonl",
        {
            "evaluation_id": evaluation_id,
            "artifact_id": payload["artifact_id"],
            "target": target,
            "created_at": payload["created_at"],
            "overall_score": summary["overall_score"],
            "status": summary["status"],
            "json": str(eval_path.relative_to(base)),
            "markdown": str(md_path.relative_to(base)),
        },
    )
    update_index_and_log(
        base,
        "channel-evaluate",
        f"{payload['artifact_id']} {evaluation_id}",
        [str(eval_path.relative_to(base)), f"Status: {summary['status']}"],
    )
    return {
        "success": True,
        "product_id": base.name,
        "target": target,
        "artifact_id": payload["artifact_id"],
        "evaluation_id": evaluation_id,
        "files": {"json": str(eval_path), "markdown": str(md_path)},
        "summary": summary,
    }
