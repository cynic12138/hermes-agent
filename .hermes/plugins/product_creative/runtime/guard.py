"""Compatibility projection of capability-owned action guard policies."""

from __future__ import annotations

from typing import Any, Dict

from ..capabilities.policy_helpers import block
from ..capabilities.registry import action_descriptors, guard_policies
from ..contracts.actions import action_metadata as contract_action_metadata
from .action_registry import action_guard_override
from .action_surface import command_for_action
from .state import safety_contract, workflow_status


ACTION_GUARD_SCHEMA_VERSION = "product_creative.action_guard.v2.10"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _guard_base(product_id: str, action: str, status: Dict[str, Any], confirmed: bool, proposal_id: str) -> Dict[str, Any]:
    metadata = contract_action_metadata(action)
    return {
        "success": True,
        "schema_version": ACTION_GUARD_SCHEMA_VERSION,
        "product_id": status.get("product_id", product_id),
        "action": action,
        "workflow_status": _text(status.get("status")),
        "allowed": False,
        "reason": "",
        "command": command_for_action(product_id, action, status),
        "requires_user_input": bool(metadata.get("requires_user_input")),
        "requires_explicit_confirmation": bool(metadata.get("requires_explicit_confirmation")),
        "confirmed": bool(confirmed),
        "proposal_id": proposal_id,
        "writes_product_workspace": bool(metadata.get("writes_product_workspace")),
        "mutates_confirmed_product_brain": bool(metadata.get("mutates_confirmed_product_brain")),
        "mutates_product_brain": bool(metadata.get("mutates_confirmed_product_brain")),
        "evidence": status.get("evidence", {}),
        "safety": status.get("safety", safety_contract()),
    }


def action_guard(product_id: str, action: str, confirmed: bool = False, proposal_id: str = "") -> Dict[str, Any]:
    status = workflow_status(product_id)
    action, proposal_id = _text(action), _text(proposal_id)
    result = _guard_base(product_id, action, status, confirmed, proposal_id)
    descriptor = action_descriptors().get(action)
    if descriptor is None:
        return block(result, f"Unknown action '{action}'.")
    override = action_guard_override(
        action,
        {"product_id": product_id, "status": status, "confirmed": confirmed, "proposal_id": proposal_id, "guard": dict(result)},
    )
    if override is not None:
        result.update(override)
        return result
    current = _text(status.get("status"))
    if descriptor.requires_existing_product and current == "no_product":
        return block(result, "Product workspace does not exist; create_product must run first.")
    policy = guard_policies().get(action)
    if policy is None:
        return block(result, f"No guard policy is registered for '{action}'.")
    return policy(
        {
            "result": result, "product_id": product_id, "status": status, "current": current,
            "evidence": status.get("evidence") or {}, "confirmed": bool(confirmed), "proposal_id": proposal_id,
        }
    )
