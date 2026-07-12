"""Capability-owned Hermes command adapters for image."""

from __future__ import annotations
from typing import Any, Dict
from ..review.api import (
    qa_image_result,
)
from ...common import TOOLSET, json_text
from .api import (
    build_image_provider_payload,
    create_batch_generation_policy,
    create_image_brief_from_intent,
    create_image_brief_review_package,
    create_image_generation_run,
    register_selected_image_asset,
    resolve_image_intent,
    revise_image_brief,
)
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

def _handle_product_image_generate(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: prepare_provider_payload(
            a.get("product_id") or a.get("id"),
            a.get("brief_id") or a.get("brief"),
            a.get("provider") or "generic",
            "image",
        ),
        args,
    )

def _handle_product_image_intent(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: resolve_image_intent(
            a.get("product_id") or a.get("id"),
            a.get("message") or "",
            a.get("target") or "",
            int(a.get("count") or 3),
            a.get("style") or "",
            a.get("provider") or "volcengine-ark-image",
        ),
        args,
    )

def _handle_product_image_brief_from_intent(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_image_brief_from_intent(
            a.get("product_id") or a.get("id"),
            a.get("intent_id") or a.get("intent") or "",
            a.get("artifact_id") or a.get("artifact") or "",
            a.get("variant"),
        ),
        args,
    )

def _handle_product_image_brief_review_package(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_image_brief_review_package(
            a.get("product_id") or a.get("id"),
            a.get("brief_id") or a.get("brief") or "",
        ),
        args,
    )

def _handle_product_image_brief_revise(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: revise_image_brief(
            a.get("product_id") or a.get("id"),
            a.get("brief_id") or a.get("brief") or "",
            a.get("patch_id") or a.get("patch") or "",
            a.get("note") or "",
            bool(a.get("confirmed")),
        ),
        args,
    )

def _handle_product_batch_generation_policy(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_batch_generation_policy(
            a.get("product_id") or a.get("id"),
            a.get("intent_id") or a.get("intent") or "",
            a.get("brief_id") or a.get("brief") or "",
            a.get("provider") or "volcengine-ark-image",
            a.get("mode") or "mock",
            int(a.get("count") or 3),
            a.get("note") or "",
            bool(a.get("confirmed")),
        ),
        args,
    )

def _handle_product_image_provider_payload(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: build_image_provider_payload(
            a.get("product_id") or a.get("id"),
            a.get("brief_id") or a.get("brief") or "",
            a.get("provider") or "volcengine-ark-image",
            a.get("batch_policy_id") or a.get("batch_policy") or "",
        ),
        args,
    )

def _handle_product_image_generation_run(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_image_generation_run(
            a.get("product_id") or a.get("id"),
            a.get("payload_id") or a.get("payload") or "",
            a.get("provider") or "generic",
            a.get("mode") or "mock",
            int(a.get("count") or 1),
        ),
        args,
    )

def _handle_product_selected_image_asset(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: register_selected_image_asset(
            a.get("product_id") or a.get("id"),
            a.get("result_id") or a.get("result") or "",
            a.get("role") or "generated_candidate",
            a.get("description") or "",
            bool(a.get("confirmed")),
        ),
        args,
    )

def _handle_product_image_qa(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: qa_image_result(
            a.get("product_id") or a.get("id"),
            a.get("result_id") or a.get("result"),
        ),
        args,
    )

def command_descriptors() -> tuple[CommandDescriptor, ...]:
    return (
        CommandDescriptor("product_image_generate", schemas.PRODUCT_IMAGE_GENERATE_SCHEMA, _handle_product_image_generate, "image", "_handle_product_image_generate"),
        CommandDescriptor("product_image_intent", schemas.PRODUCT_IMAGE_INTENT_SCHEMA, _handle_product_image_intent, "image", "_handle_product_image_intent"),
        CommandDescriptor("product_image_brief", schemas.PRODUCT_IMAGE_BRIEF_FROM_INTENT_SCHEMA, _handle_product_image_brief_from_intent, "image", "_handle_product_image_brief_from_intent"),
        CommandDescriptor("product_image_brief_review_package", schemas.PRODUCT_IMAGE_BRIEF_REVIEW_PACKAGE_SCHEMA, _handle_product_image_brief_review_package, "image", "_handle_product_image_brief_review_package"),
        CommandDescriptor("product_image_brief_revise", schemas.PRODUCT_IMAGE_BRIEF_REVISE_SCHEMA, _handle_product_image_brief_revise, "image", "_handle_product_image_brief_revise"),
        CommandDescriptor("product_batch_generation_policy", schemas.PRODUCT_BATCH_GENERATION_POLICY_SCHEMA, _handle_product_batch_generation_policy, "image", "_handle_product_batch_generation_policy"),
        CommandDescriptor("product_image_provider_payload", schemas.PRODUCT_IMAGE_PROVIDER_PAYLOAD_SCHEMA, _handle_product_image_provider_payload, "image", "_handle_product_image_provider_payload"),
        CommandDescriptor("product_image_generation_run", schemas.PRODUCT_IMAGE_GENERATION_RUN_SCHEMA, _handle_product_image_generation_run, "image", "_handle_product_image_generation_run"),
        CommandDescriptor("product_selected_image_asset", schemas.PRODUCT_SELECTED_IMAGE_ASSET_SCHEMA, _handle_product_selected_image_asset, "image", "_handle_product_selected_image_asset"),
        CommandDescriptor("product_image_qa", schemas.PRODUCT_IMAGE_QA_SCHEMA, _handle_product_image_qa, "image", "_handle_product_image_qa"),
    )
