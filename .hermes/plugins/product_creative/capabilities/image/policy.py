"""Capability-owned guard policies for image."""
from __future__ import annotations

from typing import Any, Dict

from ..policy_helpers import allow as _allow, block as _block, text as _text

def guard_resolve_image_intent(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    return _allow(result, "Image intent resolution is allowed for existing products and does not mutate confirmed Product Brain learning.")

def guard_create_image_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_intent = evidence.get("latest_image_intent") or {}
    if latest_intent and latest_intent.get("status") == "ready_for_image_brief":
                return _allow(result, "Latest image intent is ready for image brief creation.")
    return _block(result, "No ready image intent is available for image brief creation.")

def guard_review_image_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_brief = evidence.get("latest_image_brief") or {}
    if latest_brief:
                return _allow(result, "Latest image brief can be packaged for human review.")
    return _block(result, "No image brief is available for review packaging.")

def guard_revise_image_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_brief = evidence.get("latest_image_brief") or {}
    latest_review = evidence.get("latest_image_brief_review") or {}
    if not latest_brief:
                return _block(result, "No image brief is available for confirmation or revision.")
    if latest_review.get("source_brief_id") != latest_brief.get("id"):
                return _block(result, "Latest image brief must be reviewed before confirmation or revision.")
    if not confirmed:
                return _block(result, "revise_image_brief requires explicit human confirmation before provider payload generation.")
    return _allow(result, "Latest reviewed image brief can be revised or confirmed without mutating Product Brain.")

def guard_create_batch_generation_policy(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_intent = evidence.get("latest_image_intent") or {}
    latest_brief = evidence.get("latest_image_brief") or {}
    if not latest_intent and not latest_brief:
                return _block(result, "No image intent or image brief is available for batch policy creation.")
    if not confirmed:
                return _block(result, "create_batch_generation_policy approves a batch generation boundary and requires explicit confirmation.")
    return _allow(result, "Batch generation policy can be created as reviewable execution boundary without mutating Product Brain.")

def guard_build_image_provider_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_brief = evidence.get("latest_image_brief") or {}
    latest_policy = evidence.get("latest_batch_generation_policy") or {}
    if not latest_brief:
                return _block(result, "No image brief is available for provider payload generation.")
    covered_by_policy = (
                latest_policy
                and latest_policy.get("status") == "active"
                and (
                    latest_policy.get("source_image_intent_id") == latest_brief.get("source_image_intent_id")
                    or latest_policy.get("source_brief_id") == latest_brief.get("id")
                )
            )
    if latest_brief.get("status") != "confirmed_for_provider_payload" and not covered_by_policy:
                return _block(result, "Latest image brief must be confirmed or covered by an active batch generation policy before provider payload generation.")
    return _allow(result, "Latest image brief can be converted into a provider payload without external execution.")

def guard_check_image_live_readiness(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_payload = evidence.get("latest_image_provider_payload") or {}
    if latest_payload:
                return _allow(result, "Latest image provider payload can be checked for live-readiness without external execution.")
    return _block(result, "No image provider payload is available for live-readiness check.")

def guard_submit_image_generation_job(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_payload = evidence.get("latest_image_provider_payload") or {}
    if latest_payload:
                return _allow(result, "Latest image provider payload can be submitted in mock mode; live mode is blocked by execution args unless confirmed.")
    return _block(result, "No image provider payload is available for image generation.")

GUARD_POLICIES = {
    "resolve_image_intent": guard_resolve_image_intent,
    "create_image_brief": guard_create_image_brief,
    "review_image_brief": guard_review_image_brief,
    "revise_image_brief": guard_revise_image_brief,
    "create_batch_generation_policy": guard_create_batch_generation_policy,
    "build_image_provider_payload": guard_build_image_provider_payload,
    "check_image_live_readiness": guard_check_image_live_readiness,
    "submit_image_generation_job": guard_submit_image_generation_job,
}
