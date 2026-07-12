"""Capability-owned Hermes command adapters for review."""

from __future__ import annotations
from typing import Any, Dict
from .api import (
    create_review_package,
    rebuild_artifact_manifest,
)
from ...common import TOOLSET, json_text
from .evaluation_service import evaluate_channel_content, evaluate_product
from .task_overview_service import create_task_overview_package
from ...providers import (
    check_live_readiness,
    check_video_reference_readiness,
    check_video_task_status,
    create_generation_job,
    create_video_execution_policy,
    import_video_result,
    list_providers,
    prepare_provider_payload,
    validate_provider_payload,
)
from ...runtime.errors import classify_exception, error_result, record_runtime_error
from ..learning.result_evaluation_service import create_result_evaluation
from .result_review_service import create_result_review_package
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

def _handle_product_evaluate(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: evaluate_product(
            a.get("product_id") or a.get("id"),
            a.get("artifact_id") or a.get("artifact"),
        ),
        args,
    )

def _handle_product_artifact_manifest(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: rebuild_artifact_manifest(a.get("product_id") or a.get("id")), args)

def _handle_product_review_package(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_review_package(
            a.get("product_id") or a.get("id"),
            a.get("job_id") or a.get("job"),
        ),
        args,
    )

def _handle_product_result_review_package(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_result_review_package(
            a.get("product_id") or a.get("id"),
            a.get("result_id") or a.get("result"),
        ),
        args,
    )

def _handle_product_task_overview_package(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_task_overview_package(
            a.get("product_id") or a.get("id"),
            a.get("result_id") or a.get("result") or "",
            a.get("workflow_run_id") or a.get("workflow_run") or "",
            a.get("title") or "",
        ),
        args,
    )

def _handle_product_live_readiness(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: check_live_readiness(
            a.get("product_id") or a.get("id"),
            a.get("provider") or "generic",
            a.get("kind"),
            a.get("payload_id") or a.get("payload"),
        ),
        args,
    )

def command_descriptors() -> tuple[CommandDescriptor, ...]:
    return (
        CommandDescriptor("product_evaluate", schemas.PRODUCT_EVALUATE_SCHEMA, _handle_product_evaluate, "review", "_handle_product_evaluate"),
        CommandDescriptor("product_artifact_manifest", schemas.PRODUCT_ARTIFACT_MANIFEST_SCHEMA, _handle_product_artifact_manifest, "review", "_handle_product_artifact_manifest"),
        CommandDescriptor("product_review_package", schemas.PRODUCT_REVIEW_PACKAGE_SCHEMA, _handle_product_review_package, "review", "_handle_product_review_package"),
        CommandDescriptor("product_result_review_package", schemas.PRODUCT_RESULT_REVIEW_PACKAGE_SCHEMA, _handle_product_result_review_package, "review", "_handle_product_result_review_package"),
        CommandDescriptor("product_task_overview_package", schemas.PRODUCT_TASK_OVERVIEW_PACKAGE_SCHEMA, _handle_product_task_overview_package, "review", "_handle_product_task_overview_package"),
        CommandDescriptor("product_live_readiness", schemas.PRODUCT_LIVE_READINESS_SCHEMA, _handle_product_live_readiness, "review", "_handle_product_live_readiness"),
    )
