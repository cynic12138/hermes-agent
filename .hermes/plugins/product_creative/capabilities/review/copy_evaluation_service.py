"""Copy-pack evaluation service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, today, update_index_and_log, write_json

from .evaluation_shared import _clip_score, _list, _resolve_artifact_path, _score_text_length, _text, _variant_grounding_issues

def _score_variant(pack: Dict[str, Any], artifact: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    variant = int(pack.get("variant") or 0)
    product_name = _text(state.get("name")) or _text(state.get("product_id"))
    issues: List[str] = []
    strengths: List[str] = []
    scores = {
        "structure": 0,
        "grounding": 0,
        "ecommerce_main_image": 0,
        "image_prompt": 0,
        "video_storyboard": 0,
        "actionability": 0,
    }

    main_copy = pack.get("ecommerce_main_image_copy") or {}
    shots = _list(pack.get("short_video_storyboard"))
    points = _list(pack.get("core_selling_points"))

    required = [
        ("style", _text(pack.get("style"))),
        ("product_one_liner", _text(pack.get("product_one_liner"))),
        ("core_selling_points", points),
        ("ecommerce_main_image_copy.headline", _text(main_copy.get("headline"))),
        ("ecommerce_main_image_copy.subheadline", _text(main_copy.get("subheadline"))),
        ("ecommerce_main_image_copy.visual_direction", _text(main_copy.get("visual_direction"))),
        ("image_generation_prompt", _text(pack.get("image_generation_prompt"))),
        ("short_video_storyboard", shots),
    ]
    present = sum(1 for _name, value in required if bool(value))
    scores["structure"] = round(present / len(required) * 20)
    for name, value in required:
        if not value:
            issues.append(f"Missing required field: {name}")

    grounding_issues = _variant_grounding_issues(artifact, variant)
    repairs = artifact.get("grounding_audit", {}).get("repairs") or []
    variant_repairs = [item for item in repairs if item.get("variant") in {variant, str(variant)}]
    if grounding_issues:
        scores["grounding"] = max(0, 25 - len(grounding_issues) * 10)
        issues.extend(f"Grounding warning: {item.get('term')}" for item in grounding_issues)
    else:
        scores["grounding"] = 25
        strengths.append("No grounding warnings after lite audit.")
    if variant_repairs:
        scores["grounding"] = max(0, scores["grounding"] - min(8, len(variant_repairs) * 2))
        issues.append(f"Grounding repairs applied: {len(variant_repairs)}")

    headline = _text(main_copy.get("headline"))
    subheadline = _text(main_copy.get("subheadline"))
    labels = _list(main_copy.get("supporting_labels"))
    visual_direction = _text(main_copy.get("visual_direction"))
    ecommerce_score = 0
    score, reason = _score_text_length(headline, 4, 28, 5)
    ecommerce_score += score
    if reason:
        issues.append(f"Headline {reason}")
    score, reason = _score_text_length(subheadline, 8, 48, 4)
    ecommerce_score += score
    if reason:
        issues.append(f"Subheadline {reason}")
    ecommerce_score += 3 if 2 <= len(labels) <= 5 else 1
    ecommerce_score += 3 if len(visual_direction) >= 20 else 1
    scores["ecommerce_main_image"] = ecommerce_score

    prompt = _text(pack.get("image_generation_prompt"))
    image_score = 0
    score, reason = _score_text_length(prompt, 30, 240, 7)
    image_score += score
    if reason:
        issues.append(f"Image prompt {reason}")
    image_score += 3 if product_name and product_name in prompt else 1
    image_score += 3 if any(word in prompt for word in ["光", "背景", "构图", "风格"]) else 1
    image_score += 2 if any(word in prompt for word in ["无", "避免", "不出现", "禁止"]) else 0
    scores["image_prompt"] = image_score

    video_score = 0
    if 4 <= len(shots) <= 6:
        video_score += 6
    else:
        video_score += 2
        issues.append(f"Storyboard shot count {len(shots)} outside 4-6")
    complete_shots = 0
    for shot in shots:
        if all(_text(shot.get(key)) for key in ["duration", "description", "caption"]):
            complete_shots += 1
    video_score += round((complete_shots / max(1, len(shots))) * 6)
    video_score += 3 if len({shot.get("caption") for shot in shots}) >= min(3, len(shots)) else 1
    scores["video_storyboard"] = video_score

    notes = pack.get("generation_notes") or {}
    action_score = 0
    action_score += 3 if _text(pack.get("style")) else 0
    action_score += 3 if _text(pack.get("product_one_liner")) else 0
    action_score += 2 if bool(notes.get("requires_human_review", True)) else 0
    action_score += 2 if _text(notes.get("basis")) else 0
    scores["actionability"] = action_score

    total = _clip_score(sum(scores.values()))
    if total >= 85:
        recommendation = "ready_for_human_review"
    elif total >= 70:
        recommendation = "minor_revision"
    else:
        recommendation = "needs_revision"

    if len(points) >= 3:
        strengths.append("Has at least three selling points.")
    if 4 <= len(shots) <= 6:
        strengths.append("Storyboard shot count is usable.")

    return {
        "variant": variant,
        "style": pack.get("style", ""),
        "total_score": total,
        "scores": scores,
        "recommendation": recommendation,
        "strengths": strengths,
        "issues": issues,
    }

def _summary_from_variants(variant_evals: List[Dict[str, Any]], artifact: Dict[str, Any]) -> Dict[str, Any]:
    if not variant_evals:
        return {
            "overall_score": 0,
            "status": "needs_revision",
            "best_variant": None,
            "next_actions": ["Generate at least one variant before evaluation."],
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
        next_actions.append("Resolve grounding warnings before using this artifact.")
    if status in {"minor_revision", "needs_revision"}:
        next_actions.append("Revise low-scoring variants or regenerate with clearer Product State evidence.")
    next_actions.append("Ask the user to choose a preferred variant before Product Brain evolution.")

    return {
        "overall_score": overall,
        "status": status,
        "best_variant": best.get("variant"),
        "next_actions": next_actions,
    }

def _evaluation_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        f"# Product Evaluation {payload['evaluation_id']}",
        "",
        f"Product: {payload['product_id']}",
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

def _create_eval_page(base: Path, payload: Dict[str, Any]) -> None:
    date = today()
    page = base / "wiki" / "eval" / f"{date}-{payload['evaluation_id']}.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        f"""---
title: {payload['evaluation_id']}
type: eval_rubric
product_id: {base.name}
created: {date}
updated: {date}
confidence: medium
status: evaluated
sources:
  - {payload['artifact_path']}
---

{_evaluation_markdown(payload)}
""",
        encoding="utf-8",
    )

def evaluate_product(product_id: str, artifact: str) -> Dict[str, Any]:
    base = ensure_product(product_id)
    artifact_path = _resolve_artifact_path(base, artifact)
    artifact_payload = read_json(artifact_path, {})
    if not artifact_payload:
        raise ValueError(f"artifact '{artifact}' is not valid JSON")
    if artifact_payload.get("target") != "product-copy-pack":
        raise ValueError("M0.3 only evaluates product-copy-pack artifacts")

    state = read_product_state(base)
    variant_evals = [
        _score_variant(pack, artifact_payload, state)
        for pack in artifact_payload.get("variants", [])
    ]
    summary = _summary_from_variants(variant_evals, artifact_payload)
    evaluation_id = f"eval-{timestamp()}"
    eval_path = base / "artifacts" / "evaluations" / f"{evaluation_id}.json"
    md_path = base / "artifacts" / "evaluations" / f"{evaluation_id}.md"
    artifact_rel = str(artifact_path.relative_to(base))
    payload = {
        "evaluation_id": evaluation_id,
        "product_id": base.name,
        "artifact_id": artifact_payload.get("artifact_id") or artifact_path.stem,
        "artifact_path": artifact_rel,
        "created_at": now_iso(),
        "evaluation_method": "rule-evaluator-v0.3",
        "summary": summary,
        "grounding_audit": artifact_payload.get("grounding_audit", {}),
        "variants": variant_evals,
    }
    write_json(eval_path, payload)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_evaluation_markdown(payload), encoding="utf-8")
    append_jsonl(
        base / "structured" / "evaluation_index.jsonl",
        {
            "evaluation_id": evaluation_id,
            "artifact_id": payload["artifact_id"],
            "created_at": payload["created_at"],
            "overall_score": summary["overall_score"],
            "status": summary["status"],
            "json": str(eval_path.relative_to(base)),
            "markdown": str(md_path.relative_to(base)),
        },
    )
    _create_eval_page(base, payload)
    update_index_and_log(
        base,
        "evaluate",
        f"{payload['artifact_id']} {evaluation_id}",
        [str(eval_path.relative_to(base)), f"Status: {summary['status']}"],
    )
    return {
        "success": True,
        "product_id": base.name,
        "artifact_id": payload["artifact_id"],
        "evaluation_id": evaluation_id,
        "evaluation_json": str(eval_path),
        "evaluation_markdown": str(md_path),
        "summary": summary,
    }
