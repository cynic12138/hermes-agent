"""Image-generation action adapters."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from .api import (
    build_image_provider_payload,
    create_batch_generation_policy,
    create_image_brief_from_intent,
    create_image_brief_review_package,
    resolve_image_intent,
    revise_image_brief,
)
from ...provider_gateway import generation_provider_gateway
from ..models import ActionRuntimeDefinition
from ..execution_helpers import text


def _resolve_intent(args: Dict[str, Any]) -> Dict[str, Any]:
    return resolve_image_intent(
        text(args.get("product_id")),
        text(args.get("message")),
        text(args.get("target")),
        int(args.get("count") or 3),
        text(args.get("style")),
        text(args.get("provider")) or "volcengine-ark-image",
    )


def _create_brief(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_image_brief_from_intent(
        text(args.get("product_id")),
        text(args.get("intent_id")),
        text(args.get("artifact_id")),
        args.get("variant"),
    )


def _review_brief(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_image_brief_review_package(text(args.get("product_id")), text(args.get("brief_id")))


def _revise_brief(args: Dict[str, Any]) -> Dict[str, Any]:
    return revise_image_brief(
        text(args.get("product_id")),
        text(args.get("brief_id")),
        text(args.get("patch_id")),
        text(args.get("note")),
        bool(args.get("confirmed")),
    )


def _batch_policy(args: Dict[str, Any]) -> Dict[str, Any]:
    return create_batch_generation_policy(
        text(args.get("product_id")),
        text(args.get("intent_id")),
        text(args.get("brief_id")),
        text(args.get("provider")) or "volcengine-ark-image",
        text(args.get("mode")) or "mock",
        int(args.get("count") or 3),
        text(args.get("note")),
        bool(args.get("confirmed")),
    )


def _build_payload(args: Dict[str, Any]) -> Dict[str, Any]:
    return build_image_provider_payload(
        text(args.get("product_id")),
        text(args.get("brief_id")),
        text(args.get("provider")) or "volcengine-ark-image",
        text(args.get("batch_policy_id")),
    )


def _check_readiness(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().check_live_readiness(
        text(args.get("product_id")),
        text(args.get("provider")) or "volcengine-ark-image",
        text(args.get("kind")) or "image",
        text(args.get("payload_id")),
    )


def _submit(args: Dict[str, Any]) -> Dict[str, Any]:
    return generation_provider_gateway().submit_image(
        text(args.get("product_id")),
        text(args.get("payload_id")),
        text(args.get("provider")) or "generic",
        text(args.get("mode")) or "mock",
        int(args.get("count") or 1),
    )


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (
        ActionRuntimeDefinition("resolve_image_intent", _resolve_intent),
        ActionRuntimeDefinition("create_image_brief", _create_brief, auto_advance=True),
        ActionRuntimeDefinition("review_image_brief", _review_brief, auto_advance=True),
        ActionRuntimeDefinition("revise_image_brief", _revise_brief, missing_input_policy=lambda context: () if context.get("confirmed") else ("explicit_confirmation",)),
        ActionRuntimeDefinition("create_batch_generation_policy", _batch_policy, missing_input_policy=lambda context: () if context.get("confirmed") else ("explicit_confirmation",)),
        ActionRuntimeDefinition("build_image_provider_payload", _build_payload, auto_advance=True),
        ActionRuntimeDefinition("check_image_live_readiness", _check_readiness, auto_advance=True),
        ActionRuntimeDefinition(
            "submit_image_generation_job",
            _submit,
            auto_advance=True,
            idempotency_fields=("payload_id", "provider", "mode", "count"),
            missing_input_policy=lambda context: ("explicit_confirmation",) if text((context.get("args") or {}).get("mode")) == "live" and not context.get("confirmed") else (),
        ),
    )


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
