from __future__ import annotations

from typing import Any, Dict

from ..binding_helpers import bind_fields, text


def _ingest_execution(context: Dict[str, Any]) -> bool:
    args = context["args"]
    bind_fields(context, {"text": "text"})
    args["images"] = [str(item) for item in context.get("images", []) if str(item).strip()]
    return True


def _ingest_conversation(context: Dict[str, Any]) -> bool:
    message = text(context.get("message"))
    if message:
        context["args"]["text"] = message
        context["remove_missing_input"]("text")
    return True


EXECUTION_BINDERS = {
    "create_product": lambda context: bind_fields(context, {"name": "name"}),
    "ingest_product_source": _ingest_execution,
}

CONVERSATION_BINDERS = {"ingest_product_source": _ingest_conversation}
