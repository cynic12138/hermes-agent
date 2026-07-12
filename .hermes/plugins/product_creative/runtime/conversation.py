"""Conversation adapter for Product Creative runtime."""

from __future__ import annotations

from typing import Any, Dict

from .decision import (
    message_indicates_confirmation as _message_indicates_confirmation,
    target_from_message as _target_from_message,
)
from .conversation_arguments import _apply_conversation_args
from .planning import workflow_next, workflow_plan
from .decision_service import decide_intent
from .state import safety_contract as _safety_contract
from .state import workflow_status


CONVERSATION_ADAPTER_SCHEMA_VERSION = "product_creative.conversation_adapter.v4.9"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _agent_reply(plan: Dict[str, Any], message: str) -> str:
    action = plan.get("requested_action")
    status = plan.get("workflow_status")
    step = (plan.get("steps") or [{}])[0]
    missing = step.get("missing_inputs") or []
    user_next = _text(step.get("user_next_message"))
    if plan.get("status") == "ready_to_execute":
        return f"当前状态是 {status}，我可以继续执行 {action}。{user_next}"
    if plan.get("status") == "blocked_for_confirmation":
        if step.get("mutates_product_brain"):
            return f"当前状态是 {status}，下一步 {action} 会修改 Product Brain，需要你明确确认后才能继续。{user_next}"
        return f"当前状态是 {status}，下一步 {action} 需要你明确确认后才能继续。{user_next}"
    if plan.get("status") == "waiting_for_user_input":
        return f"当前状态是 {status}，下一步 {action} 还需要用户补充：{', '.join(missing)}。{user_next}"
    return f"当前状态是 {status}，动作 {action} 被 guard 阻止：{step.get('guard_reason')}"




def conversation_adapter(
    product_id: str,
    message: str,
    confirmed: bool = False,
    proposal_id: str = "",
    target: str = "",
    variants: int = 3,
) -> Dict[str, Any]:
    status = workflow_status(product_id)
    next_step = workflow_next(product_id)
    fallback_action = (next_step.get("recommended_action") or {}).get("action") or ""
    decision = decide_intent(
        status.get("product_id", product_id),
        message,
        status,
        fallback_action,
        target=_text(target),
    )
    inferred_target = _text(target) or decision.target or _target_from_message(message)
    inferred_confirmed = bool(confirmed or _message_indicates_confirmation(message))
    inferred_action = decision.action
    plan = workflow_plan(product_id, inferred_action, inferred_confirmed, proposal_id, inferred_target, variants)
    _apply_conversation_args(plan, message, inferred_confirmed)
    return {
        "success": True,
        "schema_version": CONVERSATION_ADAPTER_SCHEMA_VERSION,
        "product_id": status.get("product_id", product_id),
        "message": message,
        "workflow_status": status.get("status"),
        "interpreted_intent": {
            **decision.model_dump(mode="json"),
            "target": inferred_target,
            "confirmed": inferred_confirmed,
            "proposal_id": _text(proposal_id),
        },
        "plan": plan,
        "agent_reply": _agent_reply(plan, message),
        "executes_tools": False,
        "mutates_product_brain": False,
        "safety": status.get("safety", _safety_contract()),
    }
