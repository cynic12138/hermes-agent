"""Capability-owned guard policies for material."""
from __future__ import annotations

from typing import Any, Dict

from ..policy_helpers import allow as _allow, block as _block, text as _text

def guard_register_material_asset(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    return _allow(result, "Registering a product material asset is allowed for existing products and does not mutate confirmed Product Brain learning.")

def guard_analyze_material_image(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_material = evidence.get("latest_material_asset") or {}
    if latest_material:
                return _allow(result, "Latest registered material can be analyzed into an image analysis artifact without mutating Product Brain.")
    return _block(result, "No registered material asset is available for image analysis.")

def guard_align_visual_analysis(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_analysis = evidence.get("latest_image_analysis") or {}
    if latest_analysis:
                return _allow(result, "Latest image analysis can be aligned into a reviewable visual learning candidate.")
    return _block(result, "No image analysis artifact is available for visual alignment.")

def guard_rebuild_material_cards(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_material = evidence.get("latest_material_asset") or {}
    if latest_material:
                return _allow(result, "Registered materials can be converted into AI-readable material cards without mutating Product Brain.")
    return _block(result, "No registered material asset is available for material card rebuild.")

def guard_prepare_task_material_pack(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_card = evidence.get("latest_material_card") or {}
    if latest_card:
                return _allow(result, "Material cards are available for task-specific material pack preparation.")
    return _block(result, "No material card is available; rebuild material cards first.")

def guard_register_selected_image_asset(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_image_run = evidence.get("latest_image_generation_run") or {}
    if latest_image_run.get("first_result_id"):
                return _allow(result, "Latest generated image can be registered as a material candidate without mutating Product Brain.")
    return _block(result, "No generated image result is available for material registration.")

def guard_record_material_feedback(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_pack = evidence.get("latest_task_material_pack") or {}
    if latest_pack:
                return _allow(result, "Latest task material pack can receive lightweight material selection feedback.")
    return _block(result, "No task material pack is available for material feedback.")

def guard_resolve_material_execution_input(context: Dict[str, Any]) -> Dict[str, Any]:
    result = context['result']
    status = context['status']
    current = context['current']
    evidence = context['evidence']
    confirmed = context['confirmed']
    proposal_id = context['proposal_id']
    latest_material = evidence.get("latest_material_asset") or {}
    if latest_material:
                return _allow(result, "Latest material can be resolved into provider-ready execution input without mutating Product Brain.")
    return _block(result, "No registered material asset is available for MaterialResolver.")

GUARD_POLICIES = {
    "register_material_asset": guard_register_material_asset,
    "analyze_material_image": guard_analyze_material_image,
    "align_visual_analysis": guard_align_visual_analysis,
    "rebuild_material_cards": guard_rebuild_material_cards,
    "prepare_task_material_pack": guard_prepare_task_material_pack,
    "register_selected_image_asset": guard_register_selected_image_asset,
    "record_material_feedback": guard_record_material_feedback,
    "resolve_material_execution_input": guard_resolve_material_execution_input,
}
