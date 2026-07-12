"""Capability-owned guard policies for learning."""
from __future__ import annotations

from typing import Any, Dict

from ..policy_helpers import allow as _allow, block as _block, text as _text

def guard_record_image_result_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_image_run = evidence.get("latest_image_generation_run") or {}
    if latest_image_run.get("first_result_id"):
                return _allow(result, "Latest image generation run has a result ready for human feedback.")
    return _block(result, "No generated image result is available for feedback.")

def guard_record_video_result_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_result = evidence.get("latest_video_result") or {}
    if latest_result:
                return _allow(result, "Latest generated video result is available for human feedback.")
    return _block(result, "No generated video result is available for feedback.")

def guard_record_video_brief_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_brief = evidence.get("latest_video_brief") or {}
    if latest_brief:
                return _allow(result, "Latest video brief is available for human script/storyboard feedback.")
    return _block(result, "No video brief is available for script feedback.")

def guard_record_channel_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_run = evidence.get("latest_channel_review_run") or {}
    if current == "channel_run_ready_for_review" and latest_run:
                return _allow(result, "Latest channel review run is ready for human feedback.")
    return _block(result, "No channel review run is waiting for feedback.")

def guard_create_evolution_proposal(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_feedback = evidence.get("latest_feedback") or {}
    if current == "feedback_recorded" and latest_feedback.get("eligible_for_evolution_proposal"):
                return _allow(result, "Eligible feedback exists; proposal creation is allowed and does not mutate Product Brain.")
    return _block(result, "No eligible feedback is ready for proposal creation.")

GUARD_POLICIES = {
    "record_image_result_feedback": guard_record_image_result_feedback,
    "record_video_result_feedback": guard_record_video_result_feedback,
    "record_video_brief_feedback": guard_record_video_brief_feedback,
    "record_channel_feedback": guard_record_channel_feedback,
    "create_evolution_proposal": guard_create_evolution_proposal,
}
