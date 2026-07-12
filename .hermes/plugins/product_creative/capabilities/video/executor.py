"""Video-generation and exact-composer action adapters."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from ...provider_gateway import generation_provider_gateway
from .api import create_exact_main_image_video, create_video_brief_from_intent, create_video_brief_review_package, resolve_video_intent, revise_video_brief
from ..models import ActionRuntimeDefinition
from ..execution_helpers import text


def _resolve_intent(args: Dict[str, Any]) -> Dict[str, Any]:
    return resolve_video_intent(
        text(args.get("product_id")),
        text(args.get("message")),
        text(args.get("asset")),
        text(args.get("platform")),
        text(args.get("theme")),
    )


def _create_brief(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_video_brief_from_intent(text(args.get("product_id")), text(args.get("intent_id")))


def _review_brief(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_video_brief_review_package(text(args.get("product_id")), text(args.get("brief_id")))


def _revise_brief(args: Dict[str, Any]) -> Dict[str, Any]:
    return revise_video_brief(
        text(args.get("product_id")),
        text(args.get("brief_id")),
        text(args.get("patch_id")),
        text(args.get("note")),
        bool(args.get("confirmed")),
    )


def _build_payload(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().prepare_payload(
        text(args.get("product_id")),
        text(args.get("brief_id")),
        text(args.get("provider")) or "volcengine-ark-video",
        "video",
    )


def _reference_readiness(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().check_video_reference_readiness(text(args.get("product_id")), text(args.get("payload_id")))


def _live_readiness(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().check_live_readiness(
        text(args.get("product_id")),
        text(args.get("provider")) or "volcengine-ark-video",
        text(args.get("kind")) or "video",
        text(args.get("payload_id")),
    )


def _execution_policy(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().create_video_execution_policy(
        text(args.get("product_id")),
        text(args.get("payload_id")),
        text(args.get("provider")) or "volcengine-ark-video",
        text(args.get("mode")) or "live",
        bool(args.get("confirmed")),
        text(args.get("note")),
    )


def _submit(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().submit_video(
        text(args.get("product_id")),
        text(args.get("payload_id")),
        text(args.get("provider")) or "volcengine-ark-video",
        text(args.get("mode")) or "live",
        text(args.get("execution_policy_id")),
    )


def _task_status(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().check_video_task(
        text(args.get("product_id")),
        text(args.get("task_id")),
        text(args.get("provider")),
        bool(args.get("download", True)),
    )


def _import_result(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().import_video_result(
        text(args.get("product_id")),
        text(args.get("task_id")),
        text(args.get("url")),
        text(args.get("provider")),
        text(args.get("note")),
        bool(args.get("download", True)),
    )


def _compose_exact(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_exact_main_image_video(
        text(args.get("product_id")),
        text(args.get("asset_id")),
        text(args.get("theme")),
        text(args.get("template")) or "anime_story",
        int(args.get("duration") or 10),
        int(args.get("fps") or 24),
    )


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (
        ActionRuntimeDefinition("resolve_video_intent", _resolve_intent),
        ActionRuntimeDefinition("create_video_brief", _create_brief, auto_advance=True),
        ActionRuntimeDefinition("review_video_brief", _review_brief, auto_advance=True),
        ActionRuntimeDefinition("revise_video_brief", _revise_brief, missing_input_policy=lambda context: () if context.get("confirmed") else ("explicit_confirmation",)),
        ActionRuntimeDefinition("build_video_provider_payload", _build_payload, auto_advance=True),
        ActionRuntimeDefinition("check_video_reference_readiness", _reference_readiness, auto_advance=True),
        ActionRuntimeDefinition("check_video_live_readiness", _live_readiness, auto_advance=True),
        ActionRuntimeDefinition("create_video_execution_policy", _execution_policy, missing_input_policy=lambda context: () if context.get("confirmed") else ("explicit_confirmation",)),
        ActionRuntimeDefinition(
            "submit_video_generation_task",
            _submit,
            idempotency_fields=("payload_id", "execution_policy_id", "provider", "mode"),
            missing_input_policy=lambda context: () if context.get("confirmed") else ("explicit_confirmation",),
        ),
        ActionRuntimeDefinition(
            "check_video_task_status",
            _task_status,
            auto_advance=True,
            idempotency_fields=("task_id", "provider"),
        ),
        ActionRuntimeDefinition("import_video_result", _import_result),
        ActionRuntimeDefinition("compose_exact_main_video", _compose_exact),
    )


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
