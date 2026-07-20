"""Capability-owned Hermes command adapters for inspiration."""

from __future__ import annotations
from typing import Any, Dict
from ...common import TOOLSET, json_text
from .api import (
    collect_external_source_snapshot,
    confirm_llm_inspiration_pack,
    create_inspiration_candidates,
    create_inspiration_pack,
    create_llm_inspiration_pack,
)
from ...runtime.errors import classify_exception, error_result, record_runtime_error
from ..models import CommandDescriptor
from . import schemas


def _int_with_default(args: Dict[str, Any], key: str, default: int) -> int:
    value = args.get(key)
    return default if value is None or value == "" else int(value)


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

def _handle_product_external_source_collect(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: collect_external_source_snapshot(
            a.get("product_id") or a.get("id"),
            a.get("provider") or "manual",
            a.get("query") or "",
            a.get("channel") or "",
            a.get("mode") or "dry_run",
            int(a.get("limit") or 5),
            a.get("import_path") or "",
            a.get("text") or "",
            a.get("url") or "",
            a.get("sidecar_url") or "",
            int(a.get("wait_seconds") or 90),
            _int_with_default(a, "transcribe_limit", 1),
            bool(a.get("auto_browser_cookie")),
            _int_with_default(a, "analyze_first5_limit", 1),
        ),
        args,
    )

def _handle_product_inspiration_candidates(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_inspiration_candidates(
            a.get("product_id") or a.get("id"),
            a.get("snapshot_id") or a.get("snapshot") or "",
            a.get("goal") or "",
            int(a.get("max_candidates") or 5),
        ),
        args,
    )

def _handle_product_inspiration_pack(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_inspiration_pack(
            a.get("product_id") or a.get("id"),
            a.get("candidate_ids") or a.get("candidates") or [],
            a.get("goal") or "",
            a.get("target") or "",
            int(a.get("limit") or 3),
        ),
        args,
    )

def _handle_product_llm_inspiration_pack(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_llm_inspiration_pack(
            a.get("product_id") or a.get("id"),
            a.get("snapshot_ids") or a.get("snapshots") or [],
            a.get("goal") or "",
            a.get("target") or "",
            a.get("channel") or "",
            int(a.get("max_items") or 8),
            a.get("provider") or "",
            a.get("model") or "",
        ),
        args,
    )

def _handle_product_inspiration_library_confirm(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: confirm_llm_inspiration_pack(
            a.get("product_id") or a.get("id"),
            a.get("pack_id") or a.get("pack") or "",
            a.get("note") or "",
            bool(a.get("confirmed")),
        ),
        args,
    )

def command_descriptors() -> tuple[CommandDescriptor, ...]:
    return (
        CommandDescriptor("product_external_source_collect", schemas.PRODUCT_EXTERNAL_SOURCE_COLLECT_SCHEMA, _handle_product_external_source_collect, "inspiration", "_handle_product_external_source_collect"),
        CommandDescriptor("product_inspiration_candidates", schemas.PRODUCT_INSPIRATION_CANDIDATES_SCHEMA, _handle_product_inspiration_candidates, "inspiration", "_handle_product_inspiration_candidates"),
        CommandDescriptor("product_inspiration_pack", schemas.PRODUCT_INSPIRATION_PACK_SCHEMA, _handle_product_inspiration_pack, "inspiration", "_handle_product_inspiration_pack"),
        CommandDescriptor("product_llm_inspiration_pack", schemas.PRODUCT_LLM_INSPIRATION_PACK_SCHEMA, _handle_product_llm_inspiration_pack, "inspiration", "_handle_product_llm_inspiration_pack"),
        CommandDescriptor("product_inspiration_library_confirm", schemas.PRODUCT_INSPIRATION_LIBRARY_CONFIRM_SCHEMA, _handle_product_inspiration_library_confirm, "inspiration", "_handle_product_inspiration_library_confirm"),
    )
