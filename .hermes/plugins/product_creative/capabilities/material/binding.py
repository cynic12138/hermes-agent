from __future__ import annotations

from typing import Any, Dict

from ..binding_helpers import bind_fields, feedback, set_text, text


def _register(context: Dict[str, Any]) -> bool:
    args = context["args"]
    images = [str(item) for item in context.get("images", []) if str(item).strip()]
    path = text(context.get("path"))
    if path or images:
        args["path"] = path or images[0]
    bind_fields(context, {"role": "role", "description": "description"})
    usage = [str(item) for item in context.get("usage", []) if str(item).strip()]
    if usage:
        args["usage"] = usage
    return True


def _prepare_pack(context: Dict[str, Any]) -> bool:
    role = text(context.get("role"))
    if role in {"video_brief", "image_brief", "channel_content", "provider_payload"}:
        context["args"]["task"] = role
    set_text(context["args"], "channel", context.get("asset"))
    return True


def _register_conversation(context: Dict[str, Any]) -> bool:
    set_text(context["args"], "description", context.get("message"))
    return True


EXECUTION_BINDERS = {
    "register_material_asset": _register,
    "analyze_material_image": lambda context: bind_fields(context, {"asset": "asset", "provider": "provider"}),
    "align_visual_analysis": lambda context: bind_fields(context, {"analysis": "analysis", "note": "note"}),
    "prepare_task_material_pack": _prepare_pack,
    "register_selected_image_asset": lambda context: bind_fields(context, {"asset": "result_id", "role": "role", "description": "description"}),
    "record_material_feedback": lambda context: bind_fields(context, {"asset": "material_id", "note": "note"}),
    "resolve_material_execution_input": lambda context: bind_fields(context, {"asset": "material", "provider": "provider", "role": "role"}),
}

CONVERSATION_BINDERS = {
    "register_material_asset": _register_conversation,
    "record_material_feedback": lambda context: feedback(context, rejected=True),
}
