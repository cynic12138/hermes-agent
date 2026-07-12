from __future__ import annotations

from typing import Any, Dict

PRIORITY = 20


def recommend_action(context: Dict[str, Any]) -> str:
    evidence = context["evidence"]
    newer = context["is_newer"]
    payload = evidence.get("latest_video_provider_payload") or {}
    brief = evidence.get("latest_video_brief") or {}
    review = evidence.get("latest_review_package") or {}
    intent = evidence.get("latest_video_intent") or {}
    reference = evidence.get("latest_video_reference_readiness") or {}
    live = evidence.get("latest_video_live_readiness") or {}
    policy = evidence.get("latest_video_execution_policy") or {}
    task = evidence.get("latest_video_task") or {}
    result = evidence.get("latest_video_result") or {}
    feedback = evidence.get("latest_feedback") or {}
    payload_id = payload.get("id") or ""
    if result and newer(result, feedback):
        return "record_video_result_feedback"
    if task and (not result or newer(task, result)):
        return "check_video_task_status"
    if policy and policy.get("payload_id") == payload_id and policy.get("status") == "approved" and newer(policy, task):
        return "submit_video_generation_task"
    if live and live.get("payload_id") == payload_id and live.get("ready_for_live") and newer(live, policy):
        return "create_video_execution_policy"
    if reference and reference.get("payload_id") == payload_id and reference.get("ready_for_provider") and newer(reference, live):
        return "check_video_live_readiness"
    if payload and newer(payload, reference):
        return "check_video_reference_readiness"
    if brief:
        if brief.get("status") != "confirmed_for_provider_payload":
            return "review_video_brief" if review.get("source_brief_id") != brief.get("id") else "revise_video_brief"
        return "build_video_provider_payload"
    if intent and intent.get("status") == "ready_for_video_brief":
        return "create_video_brief"
    return ""
