from __future__ import annotations

from typing import Any, Dict

PRIORITY = 1000


def recommend_action(context: Dict[str, Any]) -> str:
    del context
    return "run_channel_review"
