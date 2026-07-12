"""Descriptor-driven action surfaces for the Product Creative runtime."""

from __future__ import annotations

from typing import Any, Dict

from ..capabilities.registry import action_descriptors


def _descriptor(action: str):
    return action_descriptors().get(action)


def command_for_action(product_id: str, action: str, status: Dict[str, Any]) -> str:
    del status
    descriptor = _descriptor(action)
    if descriptor is None:
        return ""
    confirmation = " --confirmed" if descriptor.requires_explicit_confirmation else ""
    return (
        rf".\.hermes\plugins\product_creative\scripts\product_creative.ps1 "
        rf"workflow-execute --id {product_id} --action {action}{confirmation}"
    )


def user_next_message_for_action(product_id: str, action: str, status: Dict[str, Any]) -> str:
    descriptor = _descriptor(action)
    if descriptor is None:
        return "你可以继续用自然语言说明下一步目标。"
    product_state = status.get("product_state") or {}
    product_name = str(product_state.get("name") or product_id).strip()
    confirmation = "，执行前需要你的明确确认" if descriptor.requires_explicit_confirmation else ""
    user_input = "，并补充本步骤所需信息" if descriptor.requires_user_input else ""
    return (
        f"你可以继续用自然语言说明 {product_name} 的目标；"
        f"Runtime 将通过 {descriptor.tool} 执行 {descriptor.domain} 能力{user_input}{confirmation}。"
    )


def action_descriptor(
    product_id: str,
    name: str,
    status: Dict[str, Any],
    requires_user_input: bool,
    requires_confirmation: bool,
    mutates_product_brain: bool,
    reason: str,
) -> Dict[str, Any]:
    command = command_for_action(product_id, name, status)
    return {
        "action": name,
        "command": command,
        "developer_command": command,
        "user_next_message": user_next_message_for_action(product_id, name, status),
        "requires_user_input": requires_user_input,
        "requires_explicit_confirmation": requires_confirmation,
        "mutates_product_brain": mutates_product_brain,
        "reason": reason,
    }
