"""Capability-owned workflow argument templates for image."""
from __future__ import annotations

from typing import Any, Dict

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''

def plan_resolve_image_intent(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {
                "product_id": product_id,
                "message": "<image request>",
                "target": target or "",
                "count": max(1, min(int(variants or 3), 5)),
                "style": "",
                "provider": "volcengine-ark-image",
            }

def plan_create_image_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_intent = evidence.get("latest_image_intent") or {}
    return {
                "product_id": product_id,
                "intent_id": latest_intent.get("id") or "<image-intent-id>",
                "artifact_id": "",
                "variant": None,
            }

def plan_review_image_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_brief = evidence.get("latest_image_brief") or {}
    return {"product_id": product_id, "brief_id": latest_brief.get("id") or "<image-brief-id>"}

def plan_revise_image_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_brief = evidence.get("latest_image_brief") or {}
    latest_review = evidence.get("latest_image_brief_review") or {}
    latest_patch = evidence.get("latest_image_brief_patch") or {}
    return {
                "product_id": product_id,
                "brief_id": latest_brief.get("id") or "<image-brief-id>",
                "patch_id": latest_review.get("patch_id") or latest_patch.get("id") or "",
                "note": "",
                "confirmed": True,
            }

def plan_create_batch_generation_policy(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_intent = evidence.get("latest_image_intent") or {}
    latest_brief = evidence.get("latest_image_brief") or {}
    return {
                "product_id": product_id,
                "intent_id": latest_intent.get("id") or "",
                "brief_id": latest_brief.get("id") or "",
                "provider": "volcengine-ark-image",
                "mode": "mock",
                "count": max(1, min(int(variants or latest_intent.get("count_limit") or 3), 5)),
                "note": "",
                "confirmed": True,
            }

def plan_build_image_provider_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_brief = evidence.get("latest_image_brief") or {}
    latest_policy = evidence.get("latest_batch_generation_policy") or {}
    return {
                "product_id": product_id,
                "brief_id": latest_brief.get("id") or "<image-brief-id>",
                "provider": "volcengine-ark-image",
                "batch_policy_id": latest_policy.get("id") or "",
            }

def plan_check_image_live_readiness(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_payload = evidence.get("latest_image_provider_payload") or {}
    return {
                "product_id": product_id,
                "payload_id": latest_payload.get("id") or "<image-provider-payload-id>",
                "provider": "volcengine-ark-image",
                "kind": "image",
            }

def plan_submit_image_generation_job(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_payload = evidence.get("latest_image_provider_payload") or {}
    latest_policy = evidence.get("latest_batch_generation_policy") or {}
    return {
                "product_id": product_id,
                "payload_id": latest_payload.get("id") or "<image-provider-payload-id>",
                "provider": "generic",
                "mode": "mock",
                "count": max(1, min(int(latest_policy.get("count_limit") or variants or 3), 5)),
            }

PLAN_TEMPLATES = {
    "resolve_image_intent": plan_resolve_image_intent,
    "create_image_brief": plan_create_image_brief,
    "review_image_brief": plan_review_image_brief,
    "revise_image_brief": plan_revise_image_brief,
    "create_batch_generation_policy": plan_create_batch_generation_policy,
    "build_image_provider_payload": plan_build_image_provider_payload,
    "check_image_live_readiness": plan_check_image_live_readiness,
    "submit_image_generation_job": plan_submit_image_generation_job,
}
