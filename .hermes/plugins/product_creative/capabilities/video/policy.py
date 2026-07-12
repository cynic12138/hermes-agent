"""Capability-owned guard policies for video."""
from __future__ import annotations

from typing import Any, Dict

from ..policy_helpers import allow as _allow, block as _block, text as _text

def guard_resolve_video_intent(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    return _allow(result, "Video intent resolution is allowed for existing products and does not mutate confirmed Product Brain learning.")

def guard_create_video_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_intent = evidence.get("latest_video_intent") or {}
    if latest_intent and latest_intent.get("status") == "ready_for_video_brief":
                return _allow(result, "Latest video intent is ready for image-to-video brief creation.")
    return _block(result, "No ready video intent is available for video brief creation.")

def guard_review_video_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_brief = evidence.get("latest_video_brief") or {}
    if latest_brief:
                return _allow(result, "Latest video brief can be packaged for human review.")
    return _block(result, "No video brief is available for review packaging.")

def guard_revise_video_brief(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_brief = evidence.get("latest_video_brief") or {}
    latest_review = evidence.get("latest_review_package") or {}
    if not latest_brief:
                return _block(result, "No video brief is available for confirmation or revision.")
    if latest_review.get("source_brief_id") != latest_brief.get("id"):
                return _block(result, "Latest video brief must be reviewed before confirmation or revision.")
    if not confirmed:
                return _block(result, "revise_video_brief requires explicit human confirmation before provider payload generation.")
    return _allow(result, "Latest reviewed video brief can be revised or confirmed without mutating Product Brain.")

def guard_build_video_provider_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_brief = evidence.get("latest_video_brief") or {}
    if not latest_brief:
                return _block(result, "No video brief is available for provider payload generation.")
    if latest_brief.get("status") != "confirmed_for_provider_payload":
                return _block(result, "Latest video brief must be confirmed before provider payload generation.")
    return _allow(result, "Latest confirmed video brief can be converted into a provider payload without external execution.")

def guard_check_video_reference_readiness(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_payload = evidence.get("latest_video_provider_payload") or {}
    if latest_payload:
                return _allow(result, "Latest video provider payload can be checked for provider-ready reference handles.")
    return _block(result, "No video provider payload is available for reference readiness check.")

def guard_check_video_live_readiness(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_payload = evidence.get("latest_video_provider_payload") or {}
    latest_reference = evidence.get("latest_video_reference_readiness") or {}
    if not latest_payload:
                return _block(result, "No video provider payload is available for live-readiness check.")
    if latest_reference.get("ready_for_provider") and latest_reference.get("payload_id") == latest_payload.get("id"):
                return _allow(result, "Latest video provider payload can be checked for live-readiness without external execution.")
    return _block(result, "Video reference readiness must pass before live-readiness check.")

def guard_create_video_execution_policy(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_payload = evidence.get("latest_video_provider_payload") or {}
    latest_readiness = evidence.get("latest_video_live_readiness") or {}
    if not latest_payload:
                return _block(result, "No video provider payload is available for execution policy creation.")
    if latest_readiness.get("payload_id") != latest_payload.get("id") or not latest_readiness.get("ready_for_live"):
                return _block(result, "Latest video payload must pass live-readiness before execution policy creation.")
    if not confirmed:
                return _block(result, "create_video_execution_policy requires explicit human confirmation before live video task submission.")
    return _allow(result, "Explicit confirmation was provided and the latest video payload is live-ready.")

def guard_submit_video_generation_task(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_payload = evidence.get("latest_video_provider_payload") or {}
    latest_policy = evidence.get("latest_video_execution_policy") or {}
    if not latest_payload:
                return _block(result, "No video provider payload is available for live task submission.")
    if not latest_payload.get("body_ready_for_live"):
                return _block(result, "Video payload is not live-ready; resolve reference assets into provider-ready handles first.")
    if latest_policy.get("payload_id") != latest_payload.get("id") or latest_policy.get("status") != "approved":
                return _block(result, "An approved video execution policy is required before live task submission.")
    if not confirmed:
                return _block(result, "submit_video_generation_task calls an external provider and requires explicit user confirmation.")
    return _allow(result, "Explicit confirmation was provided and the latest video payload is live-ready.")

def guard_check_video_task_status(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_task = evidence.get("latest_video_task") or {}
    if latest_task:
                return _allow(result, "Latest submitted video task can be queried and imported when the provider result is ready.")
    return _block(result, "No submitted video task is available for status check.")

def guard_import_video_result(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_task = evidence.get("latest_video_task") or {}
    if latest_task:
                return _allow(result, "A generated video result URL can be imported for the latest submitted video task.")
    return _block(result, "No submitted video task is available for manual video result import.")

def guard_compose_exact_main_video(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_material = evidence.get("latest_material_asset") or {}
    if latest_material:
                return _allow(result, "A registered material is available for fixed-main-image local video composition without external model execution.")
    return _block(result, "No registered material asset is available for fixed-main-image video composition.")

GUARD_POLICIES = {
    "resolve_video_intent": guard_resolve_video_intent,
    "create_video_brief": guard_create_video_brief,
    "review_video_brief": guard_review_video_brief,
    "revise_video_brief": guard_revise_video_brief,
    "build_video_provider_payload": guard_build_video_provider_payload,
    "check_video_reference_readiness": guard_check_video_reference_readiness,
    "check_video_live_readiness": guard_check_video_live_readiness,
    "create_video_execution_policy": guard_create_video_execution_policy,
    "submit_video_generation_task": guard_submit_video_generation_task,
    "check_video_task_status": guard_check_video_task_status,
    "import_video_result": guard_import_video_result,
    "compose_exact_main_video": guard_compose_exact_main_video,
}
