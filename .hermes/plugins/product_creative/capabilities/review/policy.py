"""Capability-owned guard policies for review."""
from __future__ import annotations

from typing import Any, Dict

from ..policy_helpers import allow as _allow, block as _block, text as _text

def guard_review_generated_result(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    if (evidence.get("latest_image_result") or {}).get("id") or (evidence.get("latest_video_result") or {}).get("id"):
                return _allow(result, "Latest generated image/video result can be packaged for human review.")
    return _block(result, "No generated image/video result is available for review.")

def guard_evaluate_generated_result(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    if (evidence.get("latest_image_result") or {}).get("id") or (evidence.get("latest_video_result") or {}).get("id"):
                return _allow(result, "Latest generated image/video result can be evaluated into reviewable learning candidates.")
    return _block(result, "No generated image/video result is available for evaluation.")

def guard_create_task_overview_package(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    if (evidence.get("latest_image_result") or {}).get("id") or (evidence.get("latest_video_result") or {}).get("id"):
                return _allow(result, "Latest creative task/result can be packaged into a user-facing M8 overview without mutating Product Brain.")
    return _block(result, "No generated result is available for a task overview package.")

GUARD_POLICIES = {
    "review_generated_result": guard_review_generated_result,
    "evaluate_generated_result": guard_evaluate_generated_result,
    "create_task_overview_package": guard_create_task_overview_package,
}
