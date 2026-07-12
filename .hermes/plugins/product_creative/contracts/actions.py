"""Compatibility action contract aggregated from capability descriptors."""

from __future__ import annotations

from typing import Any, Dict

from ..capabilities.registry import action_descriptors


ACTION_CONTRACTS: Dict[str, Dict[str, Any]] = {
    name: descriptor.contract()
    for name, descriptor in action_descriptors().items()
}
ACTION_NAMES = frozenset(ACTION_CONTRACTS)
ACTION_TOOL_NAMES = {
    name: contract["tool"]
    for name, contract in ACTION_CONTRACTS.items()
}
ACTION_METADATA = {
    name: {
        "requires_user_input": bool(contract["requires_user_input"]),
        "requires_explicit_confirmation": bool(contract["requires_explicit_confirmation"]),
        "writes_product_workspace": bool(contract["writes_product_workspace"]),
        "mutates_confirmed_product_brain": bool(contract["mutates_confirmed_product_brain"]),
    }
    for name, contract in ACTION_CONTRACTS.items()
}


def action_metadata(action: str) -> Dict[str, Any]:
    metadata = ACTION_METADATA.get(action)
    if metadata is None:
        return {
            "requires_user_input": False,
            "requires_explicit_confirmation": False,
            "writes_product_workspace": False,
            "mutates_confirmed_product_brain": False,
        }
    return dict(metadata)


def get_action_contract(action: str) -> Dict[str, Any]:
    contract = ACTION_CONTRACTS.get(action)
    return dict(contract) if contract else {}
