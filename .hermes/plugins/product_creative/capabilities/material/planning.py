"""Capability-owned workflow argument templates for material."""
from __future__ import annotations

from typing import Any, Dict

def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''

def plan_register_material_asset(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {
                "product_id": product_id,
                "path": "<local image path>",
                "role": "current_main_image",
                "description": "",
                "usage": ["product_reference", "video_first_frame"],
            }

def plan_analyze_material_image(context: Dict[str, Any]) -> Dict[str, Any]:
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
                "asset": latest_material.get("id") or "<material-id>",
                "provider": "mock-vision",
            }

def plan_align_visual_analysis(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_analysis = evidence.get("latest_image_analysis") or {}
    return {
                "product_id": product_id,
                "analysis": latest_analysis.get("id") or "<image-analysis-id>",
                "note": "",
            }

def plan_rebuild_material_cards(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {"product_id": product_id}

def plan_prepare_task_material_pack(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    return {
                "product_id": product_id,
                "task": "channel_content",
                "channel": target or "<channel-target>",
                "limit": 3,
            }

def plan_register_selected_image_asset(context: Dict[str, Any]) -> Dict[str, Any]:
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
                "role": "generated_candidate",
                "description": "",
                "confirmed": False,
            }

def plan_record_material_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    product_id = context['product_id']
    status = context['status']
    proposal_id = context['proposal_id']
    target = context['target']
    variants = context['variants']
    evidence = status.get('evidence') or {}
    latest_run = evidence.get('latest_channel_review_run') or {}
    latest_pack = evidence.get("latest_task_material_pack") or {}
    return {
                "product_id": product_id,
                "material_id": "<material-id>",
                "note": "<material selection note>",
                "task": latest_pack.get("task") or "channel_content",
                "channel": latest_pack.get("channel") or target or "",
                "selected": True,
                "rejected": False,
                "rating": 5,
            }

def plan_resolve_material_execution_input(context: Dict[str, Any]) -> Dict[str, Any]:
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
                "material": latest_material.get("id") or "<material-id>",
                "provider": "volcengine-ark-video",
                "role": "reference_image",
                "usage": "provider_payload",
            }

PLAN_TEMPLATES = {
    "register_material_asset": plan_register_material_asset,
    "analyze_material_image": plan_analyze_material_image,
    "align_visual_analysis": plan_align_visual_analysis,
    "rebuild_material_cards": plan_rebuild_material_cards,
    "prepare_task_material_pack": plan_prepare_task_material_pack,
    "register_selected_image_asset": plan_register_selected_image_asset,
    "record_material_feedback": plan_record_material_feedback,
    "resolve_material_execution_input": plan_resolve_material_execution_input,
}
