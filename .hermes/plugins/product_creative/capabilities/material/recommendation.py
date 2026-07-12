from __future__ import annotations

from typing import Any, Dict

PRIORITY = 40


def recommend_action(context: Dict[str, Any]) -> str:
    evidence = context["evidence"]
    newer = context["is_strictly_newer"]
    material = evidence.get("latest_material_asset") or {}
    analysis = evidence.get("latest_image_analysis") or {}
    alignment = evidence.get("latest_visual_alignment") or {}
    card = evidence.get("latest_material_card") or {}
    pack = evidence.get("latest_task_material_pack") or {}
    if material and analysis.get("material_id") != material.get("id"):
        return "analyze_material_image"
    if analysis and alignment.get("source_analysis_id") != analysis.get("id"):
        return "align_visual_analysis"
    if alignment and (not card or newer(alignment, card)):
        return "rebuild_material_cards"
    if card and (not pack or newer(card, pack)):
        return "prepare_task_material_pack"
    return ""
