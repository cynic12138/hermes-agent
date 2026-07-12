"""Capability-owned workflow argument templates for video."""
from __future__ import annotations

from typing import Any, Dict

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''

def plan_resolve_video_intent(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {"product_id": product_id, "message": "<video request>", "asset": "", "platform": "", "theme": ""}

def plan_create_video_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_intent = evidence.get("latest_video_intent") or {}
    return {"product_id": product_id, "intent_id": latest_intent.get("id") or "<video-intent-id>"}

def plan_review_video_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_brief = evidence.get("latest_video_brief") or {}
    return {"product_id": product_id, "brief_id": latest_brief.get("id") or "<video-brief-id>"}

def plan_revise_video_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_brief = evidence.get("latest_video_brief") or {}
    latest_patch = evidence.get("latest_video_brief_patch") or {}
    return {
                "product_id": product_id,
                "brief_id": latest_brief.get("id") or "<video-brief-id>",
                "patch_id": latest_patch.get("id") or "",
                "note": "",
                "confirmed": True,
            }

def plan_build_video_provider_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_brief = evidence.get("latest_video_brief") or {}
    return {"product_id": product_id, "brief_id": latest_brief.get("id") or "<video-brief-id>", "provider": "volcengine-ark-video"}

def plan_check_video_reference_readiness(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_payload = evidence.get("latest_video_provider_payload") or {}
    return {"product_id": product_id, "payload_id": latest_payload.get("id") or "<video-provider-payload-id>"}

def plan_check_video_live_readiness(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_payload = evidence.get("latest_video_provider_payload") or {}
    return {"product_id": product_id, "payload_id": latest_payload.get("id") or "<video-provider-payload-id>", "provider": "volcengine-ark-video", "kind": "video"}

def plan_create_video_execution_policy(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_payload = evidence.get("latest_video_provider_payload") or {}
    return {
                "product_id": product_id,
                "payload_id": latest_payload.get("id") or "<video-provider-payload-id>",
                "provider": "volcengine-ark-video",
                "mode": "live",
                "note": "",
                "confirmed": True,
            }

def plan_submit_video_generation_task(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_payload = evidence.get("latest_video_provider_payload") or {}
    latest_policy = evidence.get("latest_video_execution_policy") or {}
    return {
                "product_id": product_id,
                "payload_id": latest_payload.get("id") or "<video-provider-payload-id>",
                "provider": "volcengine-ark-video",
                "mode": "live",
                "execution_policy_id": latest_policy.get("id") or "<video-execution-policy-id>",
            }

def plan_check_video_task_status(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_task = evidence.get("latest_video_task") or {}
    return {"product_id": product_id, "task_id": latest_task.get("id") or "<video-task-id>", "provider": "", "download": True}

def plan_import_video_result(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_task = evidence.get("latest_video_task") or {}
    return {
                "product_id": product_id,
                "task_id": latest_task.get("id") or "<video-task-id>",
                "url": "<generated-video-url>",
                "provider": "",
                "note": "",
                "download": True,
            }

def plan_compose_exact_main_video(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_material = evidence.get("latest_material_asset") or {}
    return {
                "product_id": product_id,
                "asset_id": latest_material.get("id") or "",
                "theme": "<fixed main image story theme>",
                "template": "anime_story",
                "duration": 10,
                "fps": 24,
            }

PLAN_TEMPLATES = {
    "resolve_video_intent": plan_resolve_video_intent,
    "create_video_brief": plan_create_video_brief,
    "review_video_brief": plan_review_video_brief,
    "revise_video_brief": plan_revise_video_brief,
    "build_video_provider_payload": plan_build_video_provider_payload,
    "check_video_reference_readiness": plan_check_video_reference_readiness,
    "check_video_live_readiness": plan_check_video_live_readiness,
    "create_video_execution_policy": plan_create_video_execution_policy,
    "submit_video_generation_task": plan_submit_video_generation_task,
    "check_video_task_status": plan_check_video_task_status,
    "import_video_result": plan_import_video_result,
    "compose_exact_main_video": plan_compose_exact_main_video,
}
