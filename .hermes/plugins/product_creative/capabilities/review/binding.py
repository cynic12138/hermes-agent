from __future__ import annotations

import re
from typing import Any, Dict

from ..binding_helpers import bind_fields, text


def _result_from_message(context: Dict[str, Any]) -> bool:
    message = text(context.get("message"))
    match = re.search(r"(image-result-[\w-]+|video-result-[\w-]+)", message)
    if match:
        context["args"]["result_id"] = match.group(1)
    return True


def _overview_conversation(context: Dict[str, Any]) -> bool:
    _result_from_message(context)
    if text(context.get("message")):
        context["args"]["title"] = "用户请求的本次任务总览"
    return True


EXECUTION_BINDERS = {
    "review_generated_result": lambda context: bind_fields(context, {"asset": "result_id", "provider": "provider"}),
    "evaluate_generated_result": lambda context: bind_fields(context, {"asset": "result_id", "provider": "provider"}),
    "create_task_overview_package": lambda context: bind_fields(context, {"asset": "result_id", "note": "title"}),
}

CONVERSATION_BINDERS = {
    "review_generated_result": _result_from_message,
    "evaluate_generated_result": _result_from_message,
    "create_task_overview_package": _overview_conversation,
}
