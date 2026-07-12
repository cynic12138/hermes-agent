"""Capability-owned Hermes command adapters for content."""

from __future__ import annotations
from typing import Any, Dict
from ..review.api import (
    create_channel_review_package,
    create_comparison_package,
)
from .brief_export_service import export_briefs
from ...common import TOOLSET, json_text
from ..review.evaluation_service import evaluate_channel_content, evaluate_product
from .api import generate_product, list_generation_targets
from .run_service import create_channel_review_run, create_creative_run
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

def _handle_product_target_list(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda _a: list_generation_targets(), args)

def _handle_product_generate(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: generate_product(
            a.get("product_id") or a.get("id"),
            a.get("target") or "product-copy-pack",
            int(a.get("variants") or 3),
        ),
        args,
    )

def _handle_product_channel_evaluate(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: evaluate_channel_content(
            a.get("product_id") or a.get("id"),
            a.get("artifact_id") or a.get("artifact"),
        ),
        args,
    )

def _handle_product_channel_review_package(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_channel_review_package(
            a.get("product_id") or a.get("id"),
            a.get("artifact_id") or a.get("artifact"),
            a.get("evaluation_id") or a.get("evaluation") or "",
        ),
        args,
    )

def _handle_product_channel_review_run(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_channel_review_run(
            a.get("product_id") or a.get("id"),
            a.get("target") or "",
            int(a.get("variants") or 3),
        ),
        args,
    )

def _handle_product_brief(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: export_briefs(
            a.get("product_id") or a.get("id"),
            a.get("artifact_id") or a.get("artifact"),
            a.get("variant"),
            a.get("kind") or "all",
            a.get("preset") or "default",
            a.get("assets") or [],
        ),
        args,
    )

def _handle_product_creative_run(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_creative_run(
            a.get("product_id") or a.get("id"),
            a.get("artifact_id") or a.get("artifact"),
            int(a.get("variant") or 1),
            a.get("preset") or "xiaohongshu-cover",
            a.get("provider") or "generic",
            a.get("mode") or "mock",
            int(a.get("count") or 1),
        ),
        args,
    )

def _handle_product_comparison_package(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_comparison_package(
            a.get("product_id") or a.get("id"),
            a.get("job_ids") or a.get("jobs") or [],
        ),
        args,
    )

def command_descriptors() -> tuple[CommandDescriptor, ...]:
    return (
        CommandDescriptor("product_target_list", schemas.PRODUCT_TARGET_LIST_SCHEMA, _handle_product_target_list, "content", "_handle_product_target_list"),
        CommandDescriptor("product_generate", schemas.PRODUCT_GENERATE_SCHEMA, _handle_product_generate, "content", "_handle_product_generate"),
        CommandDescriptor("product_channel_evaluate", schemas.PRODUCT_CHANNEL_EVALUATE_SCHEMA, _handle_product_channel_evaluate, "content", "_handle_product_channel_evaluate"),
        CommandDescriptor("product_channel_review_package", schemas.PRODUCT_CHANNEL_REVIEW_PACKAGE_SCHEMA, _handle_product_channel_review_package, "content", "_handle_product_channel_review_package"),
        CommandDescriptor("product_channel_review_run", schemas.PRODUCT_CHANNEL_REVIEW_RUN_SCHEMA, _handle_product_channel_review_run, "content", "_handle_product_channel_review_run"),
        CommandDescriptor("product_brief", schemas.PRODUCT_BRIEF_SCHEMA, _handle_product_brief, "content", "_handle_product_brief"),
        CommandDescriptor("product_creative_run", schemas.PRODUCT_CREATIVE_RUN_SCHEMA, _handle_product_creative_run, "content", "_handle_product_creative_run"),
        CommandDescriptor("product_comparison_package", schemas.PRODUCT_COMPARISON_PACKAGE_SCHEMA, _handle_product_comparison_package, "content", "_handle_product_comparison_package"),
    )
