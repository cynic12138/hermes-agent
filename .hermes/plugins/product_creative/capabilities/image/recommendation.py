from __future__ import annotations

from typing import Any, Dict

PRIORITY = 10


def recommend_action(context: Dict[str, Any]) -> str:
    evidence = context["evidence"]
    newer = context["is_newer"]
    strictly_newer = context["is_strictly_newer"]
    intent = evidence.get("latest_image_intent") or {}
    brief = evidence.get("latest_image_brief") or {}
    review = evidence.get("latest_image_brief_review") or {}
    policy = evidence.get("latest_batch_generation_policy") or {}
    payload = evidence.get("latest_image_provider_payload") or {}
    run = evidence.get("latest_image_generation_run") or {}
    feedback = evidence.get("latest_feedback") or {}
    if run and newer(run, feedback):
        return "record_image_result_feedback"
    if payload and newer(payload, run):
        return "submit_image_generation_job"
    if brief:
        covered = policy and policy.get("status") == "active" and (
            policy.get("source_image_intent_id") == brief.get("source_image_intent_id")
            or policy.get("source_brief_id") == brief.get("id")
        )
        if brief.get("status") == "confirmed_for_provider_payload" or covered:
            return "build_image_provider_payload" if not payload or strictly_newer(brief, payload) else ""
        return "review_image_brief" if review.get("source_brief_id") != brief.get("id") else "revise_image_brief"
    if intent and intent.get("status") == "ready_for_image_brief":
        return "create_image_brief"
    return ""
