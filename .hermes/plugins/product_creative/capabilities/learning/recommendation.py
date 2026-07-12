from __future__ import annotations

from typing import Any, Dict

PRIORITY = 5

_STATUS_ACTIONS = {
    "channel_run_ready_for_review": "record_channel_feedback",
}


def recommend_action(context: Dict[str, Any]) -> str:
    return _STATUS_ACTIONS.get(str(context["status"].get("status") or ""), "")
