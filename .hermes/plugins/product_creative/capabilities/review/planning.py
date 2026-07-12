"""Capability-owned workflow argument templates for review."""
from __future__ import annotations

from typing import Any, Dict

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''

def plan_review_generated_result(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_image = evidence.get("latest_image_result") or {}
    latest_video = evidence.get("latest_video_result") or {}
    return {
                "product_id": product_id,
                "result_id": latest_image.get("id") or latest_video.get("id") or "<result-id>",
            }

def plan_evaluate_generated_result(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_image = evidence.get("latest_image_result") or {}
    latest_video = evidence.get("latest_video_result") or {}
    return {
                "product_id": product_id,
                "result_id": latest_image.get("id") or latest_video.get("id") or "<result-id>",
                "feedback_id": "",
                "provider": "",
                "model": "",
            }

def plan_create_task_overview_package(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_image = evidence.get("latest_image_result") or {}
    latest_video = evidence.get("latest_video_result") or {}
    return {
                "product_id": product_id,
                "result_id": latest_video.get("id") or latest_image.get("id") or "",
                "workflow_run_id": "",
                "title": "",
            }

PLAN_TEMPLATES = {
    "review_generated_result": plan_review_generated_result,
    "evaluate_generated_result": plan_evaluate_generated_result,
    "create_task_overview_package": plan_create_task_overview_package,
}
