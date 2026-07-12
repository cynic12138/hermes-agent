from __future__ import annotations

from typing import Any, Dict

from ..binding_helpers import bind_fields, set_text, text


def _intent_conversation(context: Dict[str, Any]) -> bool:
    message = text(context.get("message"))
    if message:
        context["args"]["message"] = message
        context["remove_missing_input"]("message")
    return True


def _provider_task_execution(context: Dict[str, Any]) -> bool:
    args = context["args"]
    action = context["action"]
    set_text(args, "provider", context.get("provider"))
    asset = text(context.get("asset"))
    if asset:
        target = {
            "check_video_live_readiness": "payload_id",
            "create_video_execution_policy": "payload_id",
            "submit_video_generation_task": "payload_id",
            "check_video_task_status": "task_id",
            "import_video_result": "url",
        }[action]
        args[target] = asset
    note = text(context.get("note"))
    if note:
        args["note"] = note
        if action == "import_video_result" and context.get("url_from_note"):
            args["url"] = context["url_from_note"]
    return True


def _execution_policy_conversation(context: Dict[str, Any]) -> bool:
    message = text(context.get("message"))
    if message:
        context["args"]["note"] = message
        context["remove_missing_input"]("note")
    return True


def _import_conversation(context: Dict[str, Any]) -> bool:
    message = text(context.get("message"))
    if message:
        set_text(context["args"], "url", context.get("url"))
        if context.get("url"):
            context["remove_missing_input"]("url")
        context["args"]["note"] = message
    return True


def _exact_conversation(context: Dict[str, Any]) -> bool:
    message = text(context.get("message"))
    if not message:
        return True
    args = context["args"]
    args["theme"] = message
    args["template"] = context["exact_video_template"]
    if context.get("duration") is not None:
        args["duration"] = context["duration"]
    if context.get("fps") is not None:
        args["fps"] = context["fps"]
    context["remove_missing_input"]("theme")
    return True


EXECUTION_BINDERS = {
    "resolve_video_intent": lambda context: bind_fields(context, {"note": "message", "asset": "asset", "role": "platform", "description": "theme"}),
    "check_video_live_readiness": _provider_task_execution,
    "create_video_execution_policy": _provider_task_execution,
    "submit_video_generation_task": _provider_task_execution,
    "check_video_task_status": _provider_task_execution,
    "import_video_result": _provider_task_execution,
    "compose_exact_main_video": lambda context: bind_fields(context, {"asset": "asset_id", "note": "theme"}),
}

CONVERSATION_BINDERS = {
    "resolve_video_intent": _intent_conversation,
    "create_video_execution_policy": _execution_policy_conversation,
    "import_video_result": _import_conversation,
    "compose_exact_main_video": _exact_conversation,
    "revise_video_brief": lambda context: bind_fields(context, {"message": "note"}),
}
