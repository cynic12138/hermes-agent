"""Material-library action adapters."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from .api import analyze_image_asset, align_visual_analysis, prepare_task_material_pack, rebuild_material_cards, rebuild_material_library_map, record_material_feedback, register_material_asset, resolve_material_execution_input
from ..image.asset_service import register_selected_image_asset
from ..models import ActionRuntimeDefinition
from ..execution_helpers import items, text


def _register(args: Dict[str, Any]) -> Dict[str, Any]:
    return register_material_asset(
        text(args.get("product_id")),
        text(args.get("path")),
        text(args.get("role")) or "current_main_image",
        text(args.get("description")),
        items(args.get("usage")),
    )


def _analyze(args: Dict[str, Any]) -> Dict[str, Any]:
    return analyze_image_asset(
        text(args.get("product_id")),
        text(args.get("asset")),
        text(args.get("provider")) or "mock-vision",
    )


def _align(args: Dict[str, Any]) -> Dict[str, Any]:
    return align_visual_analysis(
        text(args.get("product_id")),
        text(args.get("analysis")),
        text(args.get("note")),
    )


def _rebuild_cards(args: Dict[str, Any]) -> Dict[str, Any]:
    product_id = text(args.get("product_id"))
    result = rebuild_material_cards(product_id)
    result["material_library_map"] = rebuild_material_library_map(product_id)
    return result


def _prepare_pack(args: Dict[str, Any]) -> Dict[str, Any]:
    return prepare_task_material_pack(
        text(args.get("product_id")),
        text(args.get("task")) or "channel_content",
        text(args.get("channel")),
        int(args.get("limit") or 3),
    )


def _record_feedback(args: Dict[str, Any]) -> Dict[str, Any]:
    return record_material_feedback(
        text(args.get("product_id")),
        text(args.get("material_id")),
        text(args.get("note")),
        text(args.get("task")),
        text(args.get("channel")),
        bool(args.get("selected")),
        bool(args.get("rejected")),
        args.get("rating"),
    )


def _resolve_execution_input(args: Dict[str, Any]) -> Dict[str, Any]:
    return resolve_material_execution_input(
        text(args.get("product_id")),
        text(args.get("material")),
        text(args.get("provider")) or "volcengine-ark-video",
        text(args.get("role")) or "reference_image",
        text(args.get("usage")) or "provider_payload",
        True,
    )


def _register_selected(args: Dict[str, Any]) -> Dict[str, Any]:
    return register_selected_image_asset(
        text(args.get("product_id")),
        text(args.get("result_id")),
        text(args.get("role")) or "generated_candidate",
        text(args.get("description")),
        bool(args.get("confirmed")),
    )


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (
        ActionRuntimeDefinition("register_material_asset", _register),
        ActionRuntimeDefinition("analyze_material_image", _analyze, auto_advance=True, missing_input_policy=lambda context: ("explicit_confirmation",) if text((context.get("args") or {}).get("provider")) != "mock-vision" and not context.get("confirmed") else ()),
        ActionRuntimeDefinition("align_visual_analysis", _align, auto_advance=True),
        ActionRuntimeDefinition("rebuild_material_cards", _rebuild_cards, auto_advance=True),
        ActionRuntimeDefinition("prepare_task_material_pack", _prepare_pack),
        ActionRuntimeDefinition("register_selected_image_asset", _register_selected, missing_input_policy=lambda context: ("explicit_confirmation",) if text((context.get("args") or {}).get("role")) == "current_main_image" and not context.get("confirmed") else ()),
        ActionRuntimeDefinition("record_material_feedback", _record_feedback),
        ActionRuntimeDefinition("resolve_material_execution_input", _resolve_execution_input),
    )


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
