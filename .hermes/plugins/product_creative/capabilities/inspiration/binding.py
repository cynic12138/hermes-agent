from __future__ import annotations

from typing import Any, Dict

from ..binding_helpers import bind_fields, set_text, text


def _collect_execution(context: Dict[str, Any]) -> bool:
    return bind_fields(context, {"provider": "provider", "note": "query", "asset": "url", "role": "channel"})


def _collect_conversation(context: Dict[str, Any]) -> bool:
    message = text(context.get("message"))
    if not message:
        return True
    args = context["args"]
    args["query"] = message
    args["provider"] = context["external_provider"]
    args["mode"] = context["external_mode"]
    if args["provider"] in {"xiaohongshu-sidecar", "douyin-sidecar"}:
        args["limit"] = min(int(args.get("limit") or 3), 3)
        args["auto_browser_cookie"] = args["provider"] == "xiaohongshu-sidecar"
    set_text(args, "url", context.get("url"))
    context["remove_missing_input"]("query")
    return True


def _pack_conversation(context: Dict[str, Any]) -> bool:
    args = context["args"]
    set_text(args, "goal", context.get("message"))
    set_text(args, "target", context.get("target"))
    return True


def _llm_pack_conversation(context: Dict[str, Any]) -> bool:
    _pack_conversation(context)
    provider = context["external_provider"]
    if provider == "xiaohongshu-sidecar":
        context["args"]["channel"] = "xiaohongshu"
    elif provider == "douyin-sidecar":
        context["args"]["channel"] = "douyin"
    return True


EXECUTION_BINDERS = {
    "collect_external_source_snapshot": _collect_execution,
    "create_inspiration_candidates": lambda context: bind_fields(context, {"asset": "snapshot", "note": "goal"}),
    "create_inspiration_pack": lambda context: bind_fields(context, {"note": "goal", "asset": "target"}),
}

CONVERSATION_BINDERS = {
    "collect_external_source_snapshot": _collect_conversation,
    "create_inspiration_candidates": lambda context: bind_fields(context, {"message": "goal"}),
    "create_inspiration_pack": _pack_conversation,
    "create_llm_inspiration_pack": _llm_pack_conversation,
    "confirm_inspiration_library_entry": lambda context: bind_fields(context, {"message": "note"}),
}
