"""Capability-owned Hermes command adapters for video."""

from __future__ import annotations
from typing import Any, Dict
from ..learning.feedback_service import record_video_brief_feedback
from ...common import TOOLSET, json_text
from .exact_video_service import create_exact_main_image_video
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
from .api import create_video_brief_from_intent, create_video_brief_review_package, resolve_video_intent, revise_video_brief
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

def _handle_product_video_intent(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: resolve_video_intent(
            a.get("product_id") or a.get("id"),
            a.get("message") or "",
            a.get("asset") or "",
            a.get("platform") or "",
            a.get("theme") or "",
        ),
        args,
    )

def _handle_product_video_brief(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_video_brief_from_intent(
            a.get("product_id") or a.get("id"),
            a.get("intent_id") or a.get("intent") or "",
        ),
        args,
    )

def _handle_product_video_generate(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: prepare_provider_payload(
            a.get("product_id") or a.get("id"),
            a.get("brief_id") or a.get("brief"),
            a.get("provider") or "volcengine-ark-video",
            "video",
        ),
        args,
    )

def _handle_product_video_reference_readiness(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: check_video_reference_readiness(
            a.get("product_id") or a.get("id"),
            a.get("payload_id") or a.get("payload"),
        ),
        args,
    )

def _handle_product_video_execution_policy(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_video_execution_policy(
            a.get("product_id") or a.get("id"),
            a.get("payload_id") or a.get("payload"),
            a.get("provider") or "volcengine-ark-video",
            a.get("mode") or "live",
            bool(a.get("confirmed")),
            a.get("note") or "",
        ),
        args,
    )

def _handle_product_provider_list(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(lambda a: list_providers(a.get("kind")), args)

def _handle_product_provider_validate(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: validate_provider_payload(
            a.get("product_id") or a.get("id"),
            a.get("payload_id") or a.get("payload"),
            a.get("provider") or "generic",
        ),
        args,
    )

def _handle_product_generation_job(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_generation_job(
            a.get("product_id") or a.get("id"),
            a.get("payload_id") or a.get("payload"),
            a.get("provider") or "generic",
            a.get("mode") or "mock",
            a.get("execution_policy_id") or a.get("execution_policy") or "",
        ),
        args,
    )

def _handle_product_video_task_status(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: check_video_task_status(
            a.get("product_id") or a.get("id"),
            a.get("task_id") or a.get("task"),
            a.get("provider") or "",
            bool(a.get("download", True)),
        ),
        args,
    )

def _handle_product_video_result_import(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: import_video_result(
            a.get("product_id") or a.get("id"),
            a.get("task_id") or a.get("task"),
            a.get("url") or "",
            a.get("provider") or "",
            a.get("note") or "",
            bool(a.get("download", True)),
        ),
        args,
    )

def _handle_product_video_brief_review_package(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_video_brief_review_package(
            a.get("product_id") or a.get("id"),
            a.get("brief_id") or a.get("brief") or "",
        ),
        args,
    )

def _handle_product_video_brief_revise(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: revise_video_brief(
            a.get("product_id") or a.get("id"),
            a.get("brief_id") or a.get("brief") or "",
            a.get("patch_id") or a.get("patch") or "",
            a.get("note") or "",
            bool(a.get("confirmed")),
        ),
        args,
    )

def _handle_product_exact_main_video(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_exact_main_image_video(
            a.get("product_id") or a.get("id"),
            a.get("asset_id") or a.get("asset") or "",
            a.get("theme") or "",
            a.get("template") or "anime_story",
            int(a.get("duration") or 10),
            int(a.get("fps") or 24),
        ),
        args,
    )

def _handle_product_video_brief_feedback(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: record_video_brief_feedback(
            a.get("product_id") or a.get("id"),
            a.get("brief_id") or a.get("brief") or "",
            a.get("note") or "",
            bool(a.get("selected")),
            a.get("rating"),
            a.get("issues") or [],
            a.get("like_reasons") or [],
            a.get("dislike_reasons") or [],
            bool(a.get("allow_evolve")),
            {
                "hook_strength": a.get("hook_strength"),
                "storyboard_clarity": a.get("storyboard_clarity"),
                "product_grounding": a.get("product_grounding"),
                "prompt_specificity": a.get("prompt_specificity"),
                "channel_fit": a.get("channel_fit"),
                "factuality": a.get("factuality"),
            },
        ),
        args,
    )

def command_descriptors() -> tuple[CommandDescriptor, ...]:
    return (
        CommandDescriptor("product_video_intent", schemas.PRODUCT_VIDEO_INTENT_SCHEMA, _handle_product_video_intent, "video", "_handle_product_video_intent"),
        CommandDescriptor("product_video_brief", schemas.PRODUCT_VIDEO_BRIEF_SCHEMA, _handle_product_video_brief, "video", "_handle_product_video_brief"),
        CommandDescriptor("product_video_generate", schemas.PRODUCT_VIDEO_GENERATE_SCHEMA, _handle_product_video_generate, "video", "_handle_product_video_generate"),
        CommandDescriptor("product_video_reference_readiness", schemas.PRODUCT_VIDEO_REFERENCE_READINESS_SCHEMA, _handle_product_video_reference_readiness, "video", "_handle_product_video_reference_readiness"),
        CommandDescriptor("product_video_execution_policy", schemas.PRODUCT_VIDEO_EXECUTION_POLICY_SCHEMA, _handle_product_video_execution_policy, "video", "_handle_product_video_execution_policy"),
        CommandDescriptor("product_provider_list", schemas.PRODUCT_PROVIDER_LIST_SCHEMA, _handle_product_provider_list, "video", "_handle_product_provider_list"),
        CommandDescriptor("product_provider_validate", schemas.PRODUCT_PROVIDER_VALIDATE_SCHEMA, _handle_product_provider_validate, "video", "_handle_product_provider_validate"),
        CommandDescriptor("product_generation_job", schemas.PRODUCT_GENERATION_JOB_SCHEMA, _handle_product_generation_job, "video", "_handle_product_generation_job"),
        CommandDescriptor("product_video_task_status", schemas.PRODUCT_VIDEO_TASK_STATUS_SCHEMA, _handle_product_video_task_status, "video", "_handle_product_video_task_status"),
        CommandDescriptor("product_video_result_import", schemas.PRODUCT_VIDEO_RESULT_IMPORT_SCHEMA, _handle_product_video_result_import, "video", "_handle_product_video_result_import"),
        CommandDescriptor("product_video_brief_review_package", schemas.PRODUCT_VIDEO_BRIEF_REVIEW_PACKAGE_SCHEMA, _handle_product_video_brief_review_package, "video", "_handle_product_video_brief_review_package"),
        CommandDescriptor("product_video_brief_revise", schemas.PRODUCT_VIDEO_BRIEF_REVISE_SCHEMA, _handle_product_video_brief_revise, "video", "_handle_product_video_brief_revise"),
        CommandDescriptor("product_exact_main_video", schemas.PRODUCT_EXACT_MAIN_VIDEO_SCHEMA, _handle_product_exact_main_video, "video", "_handle_product_exact_main_video"),
        CommandDescriptor("product_video_brief_feedback", schemas.PRODUCT_VIDEO_BRIEF_FEEDBACK_SCHEMA, _handle_product_video_brief_feedback, "video", "_handle_product_video_brief_feedback"),
    )
