from __future__ import annotations

from typing import Any, Dict

PRIORITY = 0

_STATUS_ACTIONS = {
    "no_product": "create_product",
    "product_initialized": "ingest_product_source",
    "feedback_recorded": "create_evolution_proposal",
    "proposal_ready_for_confirmation": "apply_evolution_proposal",
}


def recommend_action(context: Dict[str, Any]) -> str:
    return _STATUS_ACTIONS.get(str(context["status"].get("status") or ""), "")
