"""Learning proposal and Product Brain writeback rules.

The store layer owns file I/O. This module owns the rules that turn feedback,
evaluations, and visual alignment signals into reviewable Product Brain updates,
then applies confirmed updates to Product State.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


EVOLUTION_PROPOSAL_SCHEMA_VERSION = "product_creative.evolution_proposal.v1"


def note_updates(note: str) -> List[Dict[str, Any]]:
    updates = []
    lower = note.lower()
    if "高级" in note or "质感" in note:
        updates.append({"path": "style_preferences.visual_tone", "value": "高级感、质感更强"})
    if "不要太促销" in note or "不促销" in note or "less promo" in lower:
        updates.append({"path": "style_preferences.promotion_intensity", "value": "低促销感"})
    if "突出" in note:
        updates.append({"path": "learning.feedback_preferences", "value": note})
    return updates


def classify_update(path: str, value: str) -> Dict[str, str]:
    if path == "style_preferences.visual_tone":
        return {
            "update_type": "visual_preference",
            "target_page": "product/visual-identity.md",
            "target_section": "Confirmed Learning",
            "risk_level": "medium",
        }
    if path == "style_preferences.promotion_intensity":
        return {
            "update_type": "promotion_preference",
            "target_page": "channels/ecommerce-main-image.md",
            "target_section": "Confirmed Learning",
            "risk_level": "medium",
        }
    if path == "learning.successful_patterns":
        return {
            "update_type": "successful_pattern",
            "target_page": "content-patterns/proven-patterns.md",
            "target_section": "Confirmed Learning",
            "risk_level": "low",
        }
    if path == "learning.failed_patterns":
        return {
            "update_type": "failed_pattern",
            "target_page": "content-patterns/failed-patterns.md",
            "target_section": "Confirmed Learning",
            "risk_level": "low",
        }
    if path == "learning.image_generation_preferences":
        return {
            "update_type": "image_generation_preference",
            "target_page": "content-patterns/visual-patterns.md",
            "target_section": "Confirmed Learning",
            "risk_level": "medium",
        }
    if path == "learning.video_script_preferences":
        return {
            "update_type": "video_script_preference",
            "target_page": "content-patterns/video-patterns.md",
            "target_section": "Confirmed Learning",
            "risk_level": "medium",
        }
    if path == "learning.channel_preferences":
        return {
            "update_type": "channel_preference",
            "target_page": "content-patterns/proven-patterns.md",
            "target_section": "Confirmed Learning",
            "risk_level": "medium",
        }
    if path == "learning.feedback_preferences":
        risk = "medium" if any(item in value for item in ["一定", "必须", "永远"]) else "low"
        return {
            "update_type": "feedback_preference",
            "target_page": "product/Product.md",
            "target_section": "Confirmed Learning",
            "risk_level": risk,
        }
    if path == "learning.material_preferences":
        return {
            "update_type": "material_preference",
            "target_page": "content-patterns/visual-patterns.md",
            "target_section": "Confirmed Learning",
            "risk_level": "medium",
        }
    return {
        "update_type": "product_state_update",
        "target_page": "product/Product.md",
        "target_section": "Confirmed Learning",
        "risk_level": "high",
    }


def proposal_risk(updates: List[Dict[str, Any]]) -> str:
    rank = {"low": 1, "medium": 2, "high": 3}
    risk = "low"
    for update in updates:
        update_risk = str(update.get("risk_level") or "low")
        if rank.get(update_risk, 1) > rank[risk]:
            risk = update_risk
    return risk


def typed_updates(updates: List[Dict[str, Any]], source_ids: List[str]) -> List[Dict[str, Any]]:
    typed = []
    for update in updates:
        path = str(update.get("path") or "")
        value = str(update.get("value") or "")
        classification = classify_update(path, value)
        typed.append({**classification, **update, "source_ids": source_ids})
    return typed


def proposal_preview(updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "update_type": item.get("update_type"),
            "target_page": item.get("target_page"),
            "target_section": item.get("target_section"),
            "path": item.get("path"),
            "value": item.get("value"),
            "source_ids": item.get("source_ids", []),
        }
        for item in updates
    ]


def dedupe(values: List[str]) -> List[str]:
    items = []
    for value in values:
        if value and value not in items:
            items.append(value)
    return items


def dedupe_updates(updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen = set()
    for update in updates:
        key = (str(update.get("path") or ""), str(update.get("value") or ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(update)
    return result


def _base_proposal(
    product_id: str,
    proposal_id: str,
    created_at: str,
    updates: List[Dict[str, Any]],
    source_ids: List[str],
    reason: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    updates = dedupe_updates(updates)
    payload = {
        "schema_version": EVOLUTION_PROPOSAL_SCHEMA_VERSION,
        "proposal_id": proposal_id,
        "product_id": product_id,
        "created_at": created_at,
        "source_ids": source_ids,
        "reason": reason,
        "risk_level": proposal_risk(updates),
        "target_pages": dedupe([str(item.get("target_page")) for item in updates]),
        "target_state_paths": [item.get("path") for item in updates if item.get("path")],
        "preview": proposal_preview(updates),
        "updates": updates,
        "requires_human_review": True,
        "status": "proposed",
    }
    if extra:
        payload.update(extra)
    return payload


def channel_target_page(target: str, kind: str) -> str:
    if target == "ecommerce-main-image-copy":
        return "channels/ecommerce-main-image.md" if kind == "preference" else "content-patterns/proven-patterns.md"
    if target == "xiaohongshu-seeding-note":
        return "product/brand-voice.md" if kind == "preference" else "content-patterns/proven-patterns.md"
    if target == "douyin-short-video-script":
        return "channels/douyin.md" if kind == "preference" else "content-patterns/proven-patterns.md"
    return "content-patterns/proven-patterns.md"


def proposal_from_result_feedback(
    product_id: str,
    feedback: Dict[str, Any],
    evaluation: Dict[str, Any],
    source_ids: List[str],
    proposal_id: str,
    created_at: str,
) -> Dict[str, Any]:
    note = feedback.get("note", "")
    rating = feedback.get("rating")
    result_id = feedback.get("source_result_id") or feedback.get("result_id") or ""
    brief_type = feedback.get("brief_type") or "generation"
    quality_scores = feedback.get("quality_scores") or {}
    average_quality_score = feedback.get("average_quality_score")
    updates = note_updates(note)
    if evaluation:
        for item in evaluation.get("proposed_updates") or []:
            if isinstance(item, dict) and item.get("path") and item.get("value"):
                updates.append({**item, "source_evaluation_id": evaluation.get("result_evaluation_id") or evaluation.get("evaluation_id")})

    selected_note = f"用户选择 {brief_type} result {result_id}".strip()
    if rating:
        selected_note = f"{selected_note}，评分 {rating}/5"
    if note:
        selected_note = f"{selected_note}：{note}"
    updates.append({"path": "learning.feedback_preferences", "value": selected_note})
    generation_preference = selected_note
    if quality_scores:
        score_bits = [f"{key}={value}/5" for key, value in quality_scores.items()]
        generation_preference = f"{generation_preference}；quality: {', '.join(score_bits)}"
    preference_path = "learning.video_script_preferences" if brief_type == "video" else "learning.image_generation_preferences"
    updates.append({"path": preference_path, "value": generation_preference})

    positive_enough = bool(rating and int(rating) >= 4)
    if average_quality_score is not None:
        positive_enough = positive_enough and float(average_quality_score) >= 4
    if feedback.get("selected") and positive_enough:
        updates.append({"path": "learning.successful_patterns", "value": selected_note})
    for key, value in quality_scores.items():
        if int(value) <= 2:
            updates.append(
                {
                    "path": "learning.failed_patterns",
                    "value": f"{brief_type} result {result_id} low {key}: {value}/5",
                }
            )
    for item in feedback.get("issues") or []:
        updates.append({"path": "learning.failed_patterns", "value": f"{brief_type} result issue: {item}"})
    for item in feedback.get("dislike_reasons") or []:
        updates.append({"path": "learning.failed_patterns", "value": f"{brief_type} result dislike: {item}"})

    updates = typed_updates(updates, source_ids)
    return _base_proposal(
        product_id,
        proposal_id,
        created_at,
        updates,
        source_ids,
        "Convert latest selected result feedback into reviewable Product Brain updates.",
        {
            "source_feedback_id": feedback.get("feedback_id"),
            "source_result_id": result_id,
        },
    )


def proposal_from_channel_feedback(
    product_id: str,
    feedback: Dict[str, Any],
    source_ids: List[str],
    proposal_id: str,
    created_at: str,
) -> Dict[str, Any]:
    target = str(feedback.get("target") or "channel")
    note = feedback.get("note", "")
    rating = feedback.get("rating")
    variant = feedback.get("variant")
    artifact_id = feedback.get("source_artifact_id") or ""
    quality_scores = feedback.get("quality_scores") or {}
    average_quality_score = feedback.get("average_quality_score")
    performance_metrics = feedback.get("performance_metrics") or {}
    updates = note_updates(note)

    selected_note = f"用户选择 {target} artifact {artifact_id}"
    if variant:
        selected_note = f"{selected_note} Variant {variant}"
    if rating:
        selected_note = f"{selected_note}，评分 {rating}/5"
    if note:
        selected_note = f"{selected_note}：{note}"
    updates.append(
        {
            "path": "learning.channel_preferences",
            "value": selected_note,
            "update_type": "channel_preference",
            "target_page": channel_target_page(target, "preference"),
            "target_section": "Confirmed Learning",
            "risk_level": "medium",
        }
    )

    if performance_metrics:
        metric_summary = ", ".join(f"{key}={value}" for key, value in sorted(performance_metrics.items()))
        updates.append(
            {
                "path": "learning.channel_preferences",
                "value": f"{target} performance for artifact {artifact_id}: {metric_summary}",
                "update_type": "channel_performance_pattern",
                "target_page": channel_target_page(target, "preference"),
                "target_section": "Confirmed Learning",
                "risk_level": "medium",
            }
        )
        sample_size = float(performance_metrics.get("views") or performance_metrics.get("impressions") or 0)
        engagement_rate = performance_metrics.get("engagement_rate")
        conversion_rate = performance_metrics.get("conversion_rate")
        if sample_size >= 100 and engagement_rate is not None:
            successful = float(engagement_rate) >= 0.05
            updates.append(
                {
                    "path": "learning.successful_patterns" if successful else "learning.failed_patterns",
                    "value": f"{target} {'high' if successful else 'low'} engagement pattern ({engagement_rate:.2%}) from artifact {artifact_id}",
                    "update_type": "successful_pattern" if successful else "failed_pattern",
                    "target_page": channel_target_page(target, "pattern") if successful else "content-patterns/failed-patterns.md",
                    "target_section": "Confirmed Learning",
                    "risk_level": "low",
                }
            )
        if sample_size >= 100 and conversion_rate is not None and float(conversion_rate) >= 0.03:
            updates.append(
                {
                    "path": "learning.successful_patterns",
                    "value": f"{target} conversion pattern ({float(conversion_rate):.2%}) from artifact {artifact_id}",
                    "update_type": "successful_pattern",
                    "target_page": channel_target_page(target, "pattern"),
                    "target_section": "Confirmed Learning",
                    "risk_level": "low",
                }
            )

    for item in feedback.get("like_reasons") or []:
        updates.append(
            {
                "path": "learning.successful_patterns",
                "value": f"{target} liked pattern: {item}",
                "update_type": "successful_pattern",
                "target_page": channel_target_page(target, "pattern"),
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    for item in feedback.get("dislike_reasons") or []:
        updates.append(
            {
                "path": "learning.failed_patterns",
                "value": f"{target} disliked pattern: {item}",
                "update_type": "failed_pattern",
                "target_page": "content-patterns/failed-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    for item in feedback.get("issues") or []:
        updates.append(
            {
                "path": "learning.failed_patterns",
                "value": f"{target} issue: {item}",
                "update_type": "failed_pattern",
                "target_page": "content-patterns/failed-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    positive_enough = bool(rating and int(rating) >= 4)
    if average_quality_score is not None:
        positive_enough = positive_enough and float(average_quality_score) >= 4
    if feedback.get("selected") and positive_enough:
        updates.append(
            {
                "path": "learning.successful_patterns",
                "value": selected_note,
                "update_type": "successful_pattern",
                "target_page": channel_target_page(target, "pattern"),
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    for key, value in quality_scores.items():
        if int(value) <= 2:
            updates.append(
                {
                    "path": "learning.failed_patterns",
                    "value": f"{target} low {key}: {value}/5",
                    "update_type": "failed_pattern",
                    "target_page": "content-patterns/failed-patterns.md",
                    "target_section": "Confirmed Learning",
                    "risk_level": "low",
                }
            )

    updates = typed_updates(updates, source_ids)
    return _base_proposal(
        product_id,
        proposal_id,
        created_at,
        updates,
        source_ids,
        "Convert latest selected channel feedback into reviewable Product Brain updates.",
        {
            "source_feedback_id": feedback.get("feedback_id"),
            "source_artifact_id": artifact_id,
        },
    )


def proposal_from_video_brief_feedback(
    product_id: str,
    feedback: Dict[str, Any],
    source_ids: List[str],
    proposal_id: str,
    created_at: str,
) -> Dict[str, Any]:
    target = str(feedback.get("target") or "video")
    note = feedback.get("note", "")
    rating = feedback.get("rating")
    brief_id = feedback.get("source_brief_id") or ""
    quality_scores = feedback.get("quality_scores") or {}
    average_quality_score = feedback.get("average_quality_score")
    updates = note_updates(note)

    selected_note = f"用户确认 video brief {brief_id}"
    if target:
        selected_note = f"{selected_note}（{target}）"
    if rating:
        selected_note = f"{selected_note}，评分 {rating}/5"
    if note:
        selected_note = f"{selected_note}：{note}"
    if quality_scores:
        score_bits = [f"{key}={value}/5" for key, value in quality_scores.items()]
        selected_note = f"{selected_note}；script quality: {', '.join(score_bits)}"
    updates.append(
        {
            "path": "learning.video_script_preferences",
            "value": selected_note,
            "update_type": "video_script_preference",
            "target_page": "content-patterns/video-patterns.md",
            "target_section": "Confirmed Learning",
            "risk_level": "medium",
        }
    )
    updates.append({"path": "learning.feedback_preferences", "value": selected_note})

    for item in feedback.get("like_reasons") or []:
        updates.append(
            {
                "path": "learning.successful_patterns",
                "value": f"video brief liked pattern: {item}",
                "update_type": "successful_pattern",
                "target_page": "content-patterns/video-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    for item in feedback.get("dislike_reasons") or []:
        updates.append(
            {
                "path": "learning.failed_patterns",
                "value": f"video brief disliked pattern: {item}",
                "update_type": "failed_pattern",
                "target_page": "content-patterns/failed-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    for item in feedback.get("issues") or []:
        updates.append(
            {
                "path": "learning.failed_patterns",
                "value": f"video brief issue: {item}",
                "update_type": "failed_pattern",
                "target_page": "content-patterns/failed-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    positive_enough = bool(rating and int(rating) >= 4)
    if average_quality_score is not None:
        positive_enough = positive_enough and float(average_quality_score) >= 4
    if feedback.get("selected") and positive_enough:
        updates.append(
            {
                "path": "learning.successful_patterns",
                "value": selected_note,
                "update_type": "successful_pattern",
                "target_page": "content-patterns/video-patterns.md",
                "target_section": "Confirmed Learning",
                "risk_level": "low",
            }
        )
    for key, value in quality_scores.items():
        if int(value) <= 2:
            updates.append(
                {
                    "path": "learning.failed_patterns",
                    "value": f"video brief low {key}: {value}/5",
                    "update_type": "failed_pattern",
                    "target_page": "content-patterns/failed-patterns.md",
                    "target_section": "Confirmed Learning",
                    "risk_level": "low",
                }
            )

    updates = typed_updates(updates, source_ids)
    return _base_proposal(
        product_id,
        proposal_id,
        created_at,
        updates,
        source_ids,
        "Convert latest selected video brief feedback into reviewable video script learning.",
        {
            "source_feedback_id": feedback.get("feedback_id"),
            "source_brief_id": brief_id,
        },
    )


def proposal_from_visual_alignment(
    product_id: str,
    alignment: Dict[str, Any],
    source_ids: List[str],
    proposal_id: str,
    created_at: str,
) -> Dict[str, Any]:
    updates = []
    for item in alignment.get("proposed_learning") or []:
        path = str(item.get("path") or "")
        value = str(item.get("value") or "")
        if path and value:
            updates.append({"path": path, "value": value})
    if not updates:
        updates.append(
            {
                "path": "learning.image_generation_preferences",
                "value": f"视觉对齐 {alignment.get('alignment_id')} 需要更多人工确认后再进入生成策略。",
            }
        )

    updates = typed_updates(updates, source_ids)
    return _base_proposal(
        product_id,
        proposal_id,
        created_at,
        updates,
        source_ids,
        "Convert latest eligible visual alignment into reviewable Product Brain visual learning.",
        {
            "source_alignment_id": alignment.get("alignment_id"),
            "source_analysis_id": alignment.get("source_analysis_id"),
            "source_material_id": alignment.get("material_id"),
        },
    )


def proposal_from_material_feedback(
    product_id: str,
    feedback: Dict[str, Any],
    source_ids: List[str],
    proposal_id: str,
    created_at: str,
) -> Dict[str, Any]:
    material_id = str(feedback.get("material_id") or "")
    task = str(feedback.get("task") or "generation")
    channel = str(feedback.get("channel") or "")
    note = str(feedback.get("note") or "")
    selected = bool(feedback.get("selected"))
    rejected = bool(feedback.get("rejected"))
    rating = feedback.get("rating")
    verdict = "优先使用" if selected and not rejected else "避免使用" if rejected else "谨慎使用"
    value = f"{verdict}素材 {material_id}，任务={task}"
    if channel:
        value += f"，渠道={channel}"
    if rating:
        value += f"，评分={rating}/5"
    if note:
        value += f"：{note}"
    updates = typed_updates(
        [{"path": "learning.material_preferences", "value": value}],
        source_ids,
    )
    if selected and rating and int(rating) >= 4:
        updates.extend(
            typed_updates(
                [{"path": "learning.successful_patterns", "value": f"material pattern: {value}"}],
                source_ids,
            )
        )
    if rejected or (rating and int(rating) <= 2):
        updates.extend(
            typed_updates(
                [{"path": "learning.failed_patterns", "value": f"material pattern: {value}"}],
                source_ids,
            )
        )
    return _base_proposal(
        product_id,
        proposal_id,
        created_at,
        updates,
        source_ids,
        "Convert material selection feedback into reviewable material preferences.",
        {
            "source_feedback_id": feedback.get("feedback_id"),
            "source_material_id": material_id,
        },
    )


def proposal_from_regular_feedback(
    product_id: str,
    feedback: Dict[str, Any],
    source_ids: List[str],
    proposal_id: str,
    created_at: str,
) -> Dict[str, Any]:
    note = feedback.get("note", "")
    variant = feedback.get("variant")
    rating = feedback.get("rating")
    updates = note_updates(note)
    if feedback.get("selected") and variant:
        selected_note = f"用户选择 Variant {variant}"
        if rating:
            selected_note = f"{selected_note}，评分 {rating}/5"
        if note:
            selected_note = f"{selected_note}：{note}"
        updates.append({"path": "learning.feedback_preferences", "value": selected_note})
    if not updates and note:
        updates.append({"path": "learning.feedback_preferences", "value": note})
    if not updates:
        updates.append({"path": "learning.feedback_preferences", "value": "等待更多反馈后再更新生成策略"})

    updates = typed_updates(updates, source_ids)
    return _base_proposal(
        product_id,
        proposal_id,
        created_at,
        updates,
        source_ids,
        "Convert latest user feedback into reviewable Product Brain updates.",
        {
            "source_feedback_id": feedback.get("feedback_id"),
        },
    )


def page_for_update(path: str) -> str:
    if path.startswith("style_preferences."):
        return "product/visual-identity.md"
    if path == "learning.successful_patterns":
        return "content-patterns/proven-patterns.md"
    if path == "learning.failed_patterns":
        return "content-patterns/failed-patterns.md"
    if path == "learning.image_generation_preferences":
        return "content-patterns/visual-patterns.md"
    if path == "learning.video_script_preferences":
        return "content-patterns/video-patterns.md"
    if path == "learning.channel_preferences":
        return "content-patterns/proven-patterns.md"
    if path == "learning.feedback_preferences":
        return "product/Product.md"
    if path == "learning.material_preferences":
        return "content-patterns/visual-patterns.md"
    return "product/Product.md"


def apply_learning_updates(state: Dict[str, Any], proposal: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    state.setdefault("style_preferences", {})
    state.setdefault("learning", {}).setdefault("feedback_preferences", [])
    state.setdefault("learning", {}).setdefault("successful_patterns", [])
    state.setdefault("learning", {}).setdefault("failed_patterns", [])
    state.setdefault("learning", {}).setdefault("image_generation_preferences", [])
    state.setdefault("learning", {}).setdefault("video_script_preferences", [])
    state.setdefault("learning", {}).setdefault("channel_preferences", [])
    state.setdefault("learning", {}).setdefault("material_preferences", [])
    applied = []
    for update in proposal.get("updates", []):
        path = update.get("path")
        value = update.get("value")
        if path == "style_preferences.visual_tone":
            state["style_preferences"]["visual_tone"] = value
        elif path == "style_preferences.promotion_intensity":
            state["style_preferences"]["promotion_intensity"] = value
        elif path == "learning.feedback_preferences":
            if value and value not in state["learning"]["feedback_preferences"]:
                state["learning"]["feedback_preferences"].append(value)
        elif path == "learning.successful_patterns":
            if value and value not in state["learning"]["successful_patterns"]:
                state["learning"]["successful_patterns"].append(value)
        elif path == "learning.failed_patterns":
            if value and value not in state["learning"]["failed_patterns"]:
                state["learning"]["failed_patterns"].append(value)
        elif path == "learning.image_generation_preferences":
            if value and value not in state["learning"]["image_generation_preferences"]:
                state["learning"]["image_generation_preferences"].append(value)
        elif path == "learning.video_script_preferences":
            if value and value not in state["learning"]["video_script_preferences"]:
                state["learning"]["video_script_preferences"].append(value)
        elif path == "learning.channel_preferences":
            if value and value not in state["learning"]["channel_preferences"]:
                state["learning"]["channel_preferences"].append(value)
        elif path == "learning.material_preferences":
            if value and value not in state["learning"]["material_preferences"]:
                state["learning"]["material_preferences"].append(value)
        else:
            continue
        applied.append(update)
    return state, applied


def confirmed_learning_lines(proposal: Dict[str, Any], applied: List[Dict[str, Any]], today_value: str) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = {}
    for update in applied:
        path = str(update.get("path") or "")
        value = str(update.get("value") or "").strip()
        if not path or not value:
            continue
        page = str(update.get("target_page") or page_for_update(path))
        update_type = str(update.get("update_type") or path)
        source_ids = update.get("source_ids") or proposal.get("source_ids") or []
        source_note = f" | source={','.join(source_ids)}" if source_ids else ""
        grouped.setdefault(page, []).append(
            f"- {today_value} | {proposal.get('proposal_id')} | {update_type} | {path}: {value}{source_note}"
        )
    return grouped
