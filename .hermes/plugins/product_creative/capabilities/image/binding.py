from __future__ import annotations

from typing import Any, Dict

from ..binding_helpers import bind_fields, text


def _intent_conversation(context: Dict[str, Any]) -> bool:
    message = text(context.get("message"))
    if message:
        context["args"]["message"] = message
        context["remove_missing_input"]("message")
    return True


def _policy_or_submit(context: Dict[str, Any]) -> bool:
    args = context["args"]
    bind_fields(context, {"note": "note", "provider": "provider"})
    provider = text(context.get("provider"))
    if provider and context.get("confirmed") and not provider.startswith("mock"):
        args["mode"] = "live"
    return True


EXECUTION_BINDERS = {
    "resolve_image_intent": lambda context: bind_fields(context, {"note": "message", "provider": "provider"}),
    "revise_image_brief": lambda context: bind_fields(context, {"note": "note"}),
    "create_batch_generation_policy": _policy_or_submit,
    "build_image_provider_payload": lambda context: bind_fields(context, {"provider": "provider"}),
    "submit_image_generation_job": _policy_or_submit,
}

CONVERSATION_BINDERS = {
    "resolve_image_intent": _intent_conversation,
    "create_batch_generation_policy": lambda context: bind_fields(context, {"message": "note"}),
    "revise_image_brief": lambda context: bind_fields(context, {"message": "note"}),
}
