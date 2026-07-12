"""Capability-driven workflow recommendation and planning contracts."""

from __future__ import annotations

from typing import Any, Dict, List

from ..capabilities.registry import action_descriptors, plan_templates, recommendation_policies
from ..common import timestamp
from .action_registry import action_missing_inputs, action_plan_override
from .action_surface import action_descriptor as _action
from .action_surface import user_next_message_for_action as _user_next_message
from .evidence import is_newer, is_strictly_newer
from .guard import action_guard
from .state import safety_contract as _safety_contract
from .state import workflow_status


WORKFLOW_NEXT_SCHEMA_VERSION = "product_creative.workflow_next.v4.9"
WORKFLOW_SUMMARY_SCHEMA_VERSION = "product_creative.workflow_summary.v2.9"
WORKFLOW_PLAN_SCHEMA_VERSION = "product_creative.workflow_plan.v2.11"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _surface(product_id: str, name: str, status: Dict[str, Any]) -> Dict[str, Any]:
    descriptor = action_descriptors()[name]
    return _action(
        product_id,
        name,
        status,
        descriptor.requires_user_input,
        descriptor.requires_explicit_confirmation,
        descriptor.mutates_confirmed_product_brain,
        f"Execute the registered {descriptor.domain} capability through {descriptor.tool}.",
    )


def workflow_next(product_id: str) -> Dict[str, Any]:
    status = workflow_status(product_id)
    evidence = status.get("evidence") or {}
    context = {
        "status": status,
        "evidence": evidence,
        "is_newer": is_newer,
        "is_strictly_newer": is_strictly_newer,
    }
    recommended_name = ""
    for _, policy in recommendation_policies():
        recommended_name = _text(policy(context))
        if recommended_name:
            break
    descriptors = action_descriptors()
    if recommended_name not in descriptors:
        raise RuntimeError(f"recommendation selected unknown action '{recommended_name}'")
    allowed_actions = [_surface(product_id, name, status) for name in descriptors]
    blocked_actions = [
        {
            "action": name,
            "blocked_unless": "registered policy and explicit confirmation allow execution",
            "mutates_product_brain": descriptor.mutates_confirmed_product_brain,
        }
        for name, descriptor in descriptors.items()
        if descriptor.requires_explicit_confirmation or descriptor.mutates_confirmed_product_brain
    ]
    return {
        "success": True,
        "schema_version": WORKFLOW_NEXT_SCHEMA_VERSION,
        "product_id": status.get("product_id", product_id),
        "status": status.get("status"),
        "recommended_action": _surface(product_id, recommended_name, status),
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "safety": status.get("safety", _safety_contract()),
    }


def workflow_summary(product_id: str) -> Dict[str, Any]:
    status = workflow_status(product_id)
    next_step = workflow_next(product_id)
    evidence = status.get("evidence") or {}
    latest_run = evidence.get("latest_channel_review_run") or {}
    proposal = evidence.get("latest_proposed_proposal") or {}
    lines = [
        f"Product: {status.get('product_id', product_id)}",
        f"Workflow status: {status.get('status')}",
    ]
    if latest_run:
        lines.append(
            f"Latest channel run: {latest_run.get('id')} | target={latest_run.get('target')} | best_variant={latest_run.get('best_variant')}"
        )
    if evidence.get("latest_feedback"):
        feedback = evidence["latest_feedback"]
        lines.append(
            f"Latest feedback: {feedback.get('id')} | selected={feedback.get('selected')} | eligible={feedback.get('eligible_for_evolution_proposal')}"
        )
    if proposal:
        lines.append(f"Pending proposal: {proposal.get('id')} | risk={proposal.get('risk_level')}")
    action = next_step.get("recommended_action") or {}
    lines.append(f"Recommended next action: {action.get('action')}")
    lines.append(f"User next message: {action.get('user_next_message')}")
    lines.append(f"Mutates Product Brain: {action.get('mutates_product_brain')}")
    return {
        "success": True,
        "schema_version": WORKFLOW_SUMMARY_SCHEMA_VERSION,
        "product_id": status.get("product_id", product_id),
        "status": status.get("status"),
        "summary": "\n".join(lines),
        "recommended_action": action,
        "safety": status.get("safety", _safety_contract()),
    }


def _latest_proposal_id(status: Dict[str, Any]) -> str:
    evidence = status.get("evidence") or {}
    proposal = evidence.get("latest_proposed_proposal") or {}
    return _text(proposal.get("id"))


def _args_template(
    product_id: str,
    action: str,
    status: Dict[str, Any],
    proposal_id: str,
    target: str,
    variants: int,
) -> Dict[str, Any]:
    context = {
        "product_id": product_id, "status": status, "proposal_id": proposal_id,
        "target": target, "variants": variants,
    }
    override = action_plan_override(action, context)
    if override is not None:
        return override
    template = plan_templates().get(action)
    return template(context) if template else {"product_id": product_id}


def missing_inputs(action: str, args: Dict[str, Any], confirmed: bool) -> List[str]:
    missing: List[str] = []
    for key, value in args.items():
        if isinstance(value, str) and value.startswith("<") and value.endswith(">"):
            missing.append(key)
    missing.extend(action_missing_inputs(action, {"args": args, "confirmed": confirmed}))
    return list(dict.fromkeys(missing))


def plan_status(guard: Dict[str, Any], missing_inputs: List[str]) -> str:
    if not guard.get("allowed"):
        if guard.get("requires_explicit_confirmation") and not guard.get("confirmed"):
            return "blocked_for_confirmation"
        return "blocked_by_guard"
    if missing_inputs:
        if "explicit_confirmation" in missing_inputs:
            return "blocked_for_confirmation"
        return "waiting_for_user_input"
    return "ready_to_execute"


def workflow_plan(
    product_id: str,
    action: str = "",
    confirmed: bool = False,
    proposal_id: str = "",
    target: str = "",
    variants: int = 3,
) -> Dict[str, Any]:
    status = workflow_status(product_id)
    next_step = workflow_next(product_id)
    recommended_action = (next_step.get("recommended_action") or {}).get("action") or ""
    chosen_action = _text(action) or _text(recommended_action)
    proposal_id = _text(proposal_id)
    guard = action_guard(product_id, chosen_action, confirmed, proposal_id)
    args = _args_template(product_id, chosen_action, status, guard.get("proposal_id") or proposal_id, _text(target), variants)
    missing = missing_inputs(chosen_action, args, confirmed)
    step_status = plan_status(guard, missing)
    descriptor = action_descriptors().get(chosen_action)
    step = {
        "step": 1,
        "action": chosen_action,
        "tool": descriptor.tool if descriptor else "",
        "allowed_by_guard": bool(guard.get("allowed")),
        "status": step_status,
        "args_template": args,
        "command": guard.get("command", ""),
        "developer_command": guard.get("command", ""),
        "user_next_message": _user_next_message(status.get("product_id", product_id), chosen_action, status),
        "missing_inputs": missing,
        "requires_user_input": bool(missing and "explicit_confirmation" not in missing),
        "requires_explicit_confirmation": bool(guard.get("requires_explicit_confirmation")),
        "confirmed": bool(confirmed),
        "writes_product_workspace": bool(guard.get("writes_product_workspace")),
        "mutates_product_brain": bool(guard.get("mutates_product_brain")),
        "guard_reason": guard.get("reason", ""),
    }
    return {
        "success": True,
        "schema_version": WORKFLOW_PLAN_SCHEMA_VERSION,
        "plan_id": f"workflow-plan-{timestamp()}",
        "product_id": status.get("product_id", product_id),
        "workflow_status": status.get("status"),
        "recommended_action": recommended_action,
        "requested_action": chosen_action,
        "status": step_status,
        "ready_to_execute": step_status == "ready_to_execute",
        "requires_user_input": bool(step["requires_user_input"]),
        "requires_explicit_confirmation": bool(step["requires_explicit_confirmation"] and not confirmed),
        "mutates_product_brain": bool(step["mutates_product_brain"]),
        "guard_result": guard,
        "steps": [step],
        "safety": status.get("safety", _safety_contract()),
    }
