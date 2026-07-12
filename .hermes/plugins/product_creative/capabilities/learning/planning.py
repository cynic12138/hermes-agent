"""Capability-owned workflow argument templates for learning."""
from __future__ import annotations

from typing import Any, Dict

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''

def plan_record_image_result_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_run = evidence.get("latest_image_generation_run") or {}
    return {
                "product_id": product_id,
                "result_id": latest_run.get("first_result_id") or "<image-result-id>",
                "selected": True,
                "rating": 5,
                "note": "<image result review note>",
                "allow_evolve": True,
                "issues": [],
                "subject_clarity": 5,
                "product_recognizability": 5,
                "composition": 5,
                "style_fit": 5,
                "copy_fit": 5,
            }

def plan_record_video_result_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_result = evidence.get("latest_video_result") or {}
    return {
                "product_id": product_id,
                "result_id": latest_result.get("id") or "<video-result-id>",
                "selected": True,
                "rating": 5,
                "note": "<video result review note>",
                "allow_evolve": True,
                "issues": [],
                "subject_clarity": 5,
                "product_recognizability": 5,
                "composition": 5,
                "style_fit": 5,
                "copy_fit": 5,
            }

def plan_record_video_brief_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_brief = evidence.get("latest_video_brief") or {}
    return {
                "product_id": product_id,
                "brief_id": latest_brief.get("id") or "<video-brief-id>",
                "selected": True,
                "rating": 5,
                "note": "<video brief review note>",
                "allow_evolve": True,
                "like_reasons": [],
                "dislike_reasons": [],
                "issues": [],
                "hook_strength": 5,
                "storyboard_clarity": 5,
                "product_grounding": 5,
                "prompt_specificity": 5,
                "channel_fit": 5,
                "factuality": 5,
            }

def plan_record_channel_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {
                "product_id": product_id,
                "artifact_id": latest_run.get("channel_content_id") or "<channel-artifact-id>",
                "variant": latest_run.get("best_variant") or "<variant>",
                "selected": True,
                "rating": 5,
                "note": "<user review note>",
                "allow_evolve": True,
                "like_reasons": [],
                "dislike_reasons": [],
                "issues": [],
                "channel_fit": 5,
                "factuality": 5,
                "tone_fit": 5,
                "actionability": 5,
            }

def plan_create_evolution_proposal(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {"product_id": product_id}

PLAN_TEMPLATES = {
    "record_image_result_feedback": plan_record_image_result_feedback,
    "record_video_result_feedback": plan_record_video_result_feedback,
    "record_video_brief_feedback": plan_record_video_brief_feedback,
    "record_channel_feedback": plan_record_channel_feedback,
    "create_evolution_proposal": plan_create_evolution_proposal,
}
