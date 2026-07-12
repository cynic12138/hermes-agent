"""Capability-owned Hermes command adapters for material."""

from __future__ import annotations
from typing import Any, Dict
from ...common import TOOLSET, json_text
from .api import analyze_image_asset, align_visual_analysis, bind_material_remote_url, check_m2_material_compatibility, list_material_assets, prepare_task_material_pack, provider_capability_matrix, rebuild_material_cards, rebuild_material_library_map, rebuild_material_manifest, record_material_feedback, record_material_usage, register_material_asset, resolve_material_execution_input
from ...runtime.errors import classify_exception, error_result, record_runtime_error
from ..models import CommandDescriptor
from . import schemas

def _tool_ok(fn, args: Dict[str, Any]) -> str:
    try:
        return json_text(fn(args))
    except Exception as exc:
        error = classify_exception(
            exc,
            "hermes_tool_adapter",
            str(args.get("product_id") or args.get("id") or ""),
            str(args.get("action") or ""),
        )
        error["diagnostic_path"] = record_runtime_error(error)
        return json_text(error_result(error) | {"diagnostic_path": error["diagnostic_path"]})

def _ids(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []

def _handle_product_asset_register(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: register_material_asset(
            a.get("product_id") or a.get("id"),
            a.get("path") or "",
            a.get("role") or "product_photo",
            a.get("description") or "",
            a.get("usage") or [],
        ),
        args,
    )

def _handle_product_asset_bind_url(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: bind_material_remote_url(
            a.get("product_id") or a.get("id"),
            a.get("asset") or a.get("material_id") or "",
            a.get("url") or "",
            a.get("usage") or "video_reference",
            a.get("note") or "",
        ),
        args,
    )

def _handle_product_asset_list(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: list_material_assets(a.get("product_id") or a.get("id"), a.get("role") or ""),
        args,
    )

def _handle_product_provider_capability_matrix(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: provider_capability_matrix(a.get("provider") or ""), args)

def _handle_product_material_resolve(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: resolve_material_execution_input(
            a.get("product_id") or a.get("id"),
            a.get("material_id") or a.get("material") or a.get("asset") or "",
            a.get("provider") or "volcengine-ark-image",
            a.get("role") or "reference_image",
            a.get("usage") or "provider_payload",
        ),
        args,
    )

def _handle_product_material_manifest(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: rebuild_material_manifest(a.get("product_id") or a.get("id")), args)

def _handle_product_material_compat(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: check_m2_material_compatibility(a.get("product_id") or a.get("id")), args)

def _handle_product_material_card_rebuild(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: rebuild_material_cards(a.get("product_id") or a.get("id")), args)

def _handle_product_material_library_map(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: rebuild_material_library_map(a.get("product_id") or a.get("id")), args)

def _handle_product_material_usage(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: record_material_usage(
            a.get("product_id") or a.get("id"),
            a.get("task") or "",
            a.get("channel") or "",
            a.get("task_material_pack_id") or a.get("pack") or "",
            a.get("artifact_id") or a.get("artifact") or "",
            _ids(a.get("material_ids") or a.get("material_id") or a.get("material") or []),
        ),
        args,
    )

def _handle_product_task_material_pack(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: prepare_task_material_pack(
            a.get("product_id") or a.get("id"),
            a.get("task") or "channel_content",
            a.get("channel") or "",
            int(a.get("limit") or 3),
        ),
        args,
    )

def _handle_product_material_feedback(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: record_material_feedback(
            a.get("product_id") or a.get("id"),
            a.get("material_id") or a.get("material") or "",
            a.get("note") or "",
            a.get("task") or "",
            a.get("channel") or "",
            bool(a.get("selected")),
            bool(a.get("rejected")),
            a.get("rating"),
        ),
        args,
    )

def _handle_product_image_analyze(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: analyze_image_asset(
            a.get("product_id") or a.get("id"),
            a.get("asset") or a.get("material_id") or "",
            a.get("provider") or "mock-vision",
        ),
        args,
    )

def _handle_product_visual_align(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: align_visual_analysis(
            a.get("product_id") or a.get("id"),
            a.get("analysis") or a.get("analysis_id") or "",
            a.get("note") or "",
        ),
        args,
    )

def command_descriptors() -> tuple[CommandDescriptor, ...]:
    return (
        CommandDescriptor("product_asset_register", schemas.PRODUCT_ASSET_REGISTER_SCHEMA, _handle_product_asset_register, "material", "_handle_product_asset_register"),
        CommandDescriptor("product_asset_bind_url", schemas.PRODUCT_ASSET_BIND_URL_SCHEMA, _handle_product_asset_bind_url, "material", "_handle_product_asset_bind_url"),
        CommandDescriptor("product_asset_list", schemas.PRODUCT_ASSET_LIST_SCHEMA, _handle_product_asset_list, "material", "_handle_product_asset_list"),
        CommandDescriptor("product_provider_capability_matrix", schemas.PRODUCT_PROVIDER_CAPABILITY_MATRIX_SCHEMA, _handle_product_provider_capability_matrix, "material", "_handle_product_provider_capability_matrix"),
        CommandDescriptor("product_material_resolve", schemas.PRODUCT_MATERIAL_RESOLVE_SCHEMA, _handle_product_material_resolve, "material", "_handle_product_material_resolve"),
        CommandDescriptor("product_material_manifest", schemas.PRODUCT_MATERIAL_MANIFEST_SCHEMA, _handle_product_material_manifest, "material", "_handle_product_material_manifest"),
        CommandDescriptor("product_material_compat", schemas.PRODUCT_MATERIAL_COMPAT_SCHEMA, _handle_product_material_compat, "material", "_handle_product_material_compat"),
        CommandDescriptor("product_material_card_rebuild", schemas.PRODUCT_MATERIAL_CARD_REBUILD_SCHEMA, _handle_product_material_card_rebuild, "material", "_handle_product_material_card_rebuild"),
        CommandDescriptor("product_material_library_map", schemas.PRODUCT_MATERIAL_LIBRARY_MAP_SCHEMA, _handle_product_material_library_map, "material", "_handle_product_material_library_map"),
        CommandDescriptor("product_material_usage", schemas.PRODUCT_MATERIAL_USAGE_SCHEMA, _handle_product_material_usage, "material", "_handle_product_material_usage"),
        CommandDescriptor("product_task_material_pack", schemas.PRODUCT_TASK_MATERIAL_PACK_SCHEMA, _handle_product_task_material_pack, "material", "_handle_product_task_material_pack"),
        CommandDescriptor("product_material_feedback", schemas.PRODUCT_MATERIAL_FEEDBACK_SCHEMA, _handle_product_material_feedback, "material", "_handle_product_material_feedback"),
        CommandDescriptor("product_image_analyze", schemas.PRODUCT_IMAGE_ANALYZE_SCHEMA, _handle_product_image_analyze, "material", "_handle_product_image_analyze"),
        CommandDescriptor("product_visual_align", schemas.PRODUCT_VISUAL_ALIGN_SCHEMA, _handle_product_visual_align, "material", "_handle_product_visual_align"),
    )
