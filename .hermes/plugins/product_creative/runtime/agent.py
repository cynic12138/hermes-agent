"""Long-running Product Creative agent turn orchestration."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from ..store import resolve_product_workspace
from .execution import workflow_run


AGENT_TURN_SCHEMA_VERSION = "product_creative.agent_turn.v1"


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_step(plan: Dict[str, Any]) -> Dict[str, Any]:
    step = (plan.get("steps") or [{}])[0]
    return step if isinstance(step, dict) else {}


def _proposal_id_from_text(*values: Any) -> str:
    for value in values:
        match = re.search(r"proposal-\d{8}-\d{6}", _text(value))
        if match:
            return match.group(0)
    return ""


def interpreted_intent(run: Dict[str, Any]) -> Dict[str, Any]:
    initial_intent = run.get("initial_intent") if isinstance(run.get("initial_intent"), dict) else {}
    last_execution = run.get("last_execution") if isinstance(run.get("last_execution"), dict) else {}
    conversation = last_execution.get("conversation") if isinstance(last_execution.get("conversation"), dict) else {}
    intent = initial_intent or (conversation.get("interpreted_intent") if isinstance(conversation.get("interpreted_intent"), dict) else {})
    plan = last_execution.get("plan") if isinstance(last_execution.get("plan"), dict) else {}
    step = _first_step(plan)
    return {
        "source": _text(intent.get("source")) or ("conversation_adapter" if intent else "workflow_plan"),
        "action": _text(intent.get("action") or plan.get("requested_action") or step.get("action")),
        "target": _text(intent.get("target") or (step.get("args_template") or {}).get("target")),
        "confirmed": bool(intent.get("confirmed") or step.get("confirmed") or (plan.get("guard_result") or {}).get("confirmed")),
        "proposal_id": _text(intent.get("proposal_id") or (plan.get("guard_result") or {}).get("proposal_id")),
    }


def execution_contract(run: Dict[str, Any]) -> Dict[str, Any]:
    last_execution = run.get("last_execution") if isinstance(run.get("last_execution"), dict) else {}
    plan = last_execution.get("plan") if isinstance(last_execution.get("plan"), dict) else {}
    step = _first_step(plan)
    guard = plan.get("guard_result") if isinstance(plan.get("guard_result"), dict) else {}
    return {
        "executed": bool(last_execution.get("executed")),
        "execution_status": _text(last_execution.get("execution_status")),
        "plan_status": _text(plan.get("status")),
        "stop_reason": _text(run.get("stop_reason")),
        "guard_reason": _text(step.get("guard_reason") or last_execution.get("reason")),
        "confirmed": bool(step.get("confirmed") or guard.get("confirmed")),
        "requires_user_input": bool(plan.get("requires_user_input") or step.get("requires_user_input")),
        "requires_explicit_confirmation": bool(plan.get("requires_explicit_confirmation")),
        "action_requires_explicit_confirmation": bool(step.get("requires_explicit_confirmation")),
        "mutates_product_brain": bool(plan.get("mutates_product_brain") or step.get("mutates_product_brain")),
        "tool": _text(step.get("tool")),
    }


def learning_writeback_state(run: Dict[str, Any]) -> Dict[str, Any]:
    last_execution = run.get("last_execution") if isinstance(run.get("last_execution"), dict) else {}
    result = last_execution.get("result") if isinstance(last_execution.get("result"), dict) else {}
    next_action = run.get("recommended_next_action") if isinstance(run.get("recommended_next_action"), dict) else {}
    applied_updates = result.get("applied_updates") if isinstance(result.get("applied_updates"), list) else []
    proposal_id = _text(result.get("proposal_id")) or _proposal_id_from_text(
        next_action.get("command"),
        next_action.get("developer_command"),
        next_action.get("user_next_message"),
    )
    if applied_updates:
        status = "applied"
    elif _text(result.get("proposal_id")):
        status = "proposal_created"
    elif next_action.get("action") == "apply_evolution_proposal":
        status = "awaiting_user_confirmation"
    else:
        status = "not_applicable"
    return {
        "status": status,
        "proposal_id": proposal_id,
        "requires_explicit_confirmation": bool(next_action.get("requires_explicit_confirmation")),
        "mutates_product_brain": bool(next_action.get("mutates_product_brain")),
        "applied_update_count": len(applied_updates),
    }


def compact_workflow_run_result(run: Dict[str, Any]) -> Dict[str, Any]:
    last_execution = run.get("last_execution") if isinstance(run.get("last_execution"), dict) else {}
    result = last_execution.get("result") if isinstance(last_execution.get("result"), dict) else {}
    post_status = run.get("post_status") if isinstance(run.get("post_status"), dict) else {}
    next_action = run.get("recommended_next_action") or {}
    return {
        "success": run.get("success"),
        "schema_version": run.get("schema_version"),
        "agent_turn_schema_version": AGENT_TURN_SCHEMA_VERSION,
        "workflow_run_id": run.get("workflow_run_id") or run.get("run_id"),
        "product_id": run.get("product_id"),
        "executed_count": run.get("executed_count"),
        "attempted_count": run.get("attempted_count"),
        "stop_reason": run.get("stop_reason"),
        "initial_message": run.get("initial_message"),
        "interpreted_intent": interpreted_intent(run),
        "execution_contract": execution_contract(run),
        "learning_writeback": learning_writeback_state(run),
        "executions": run.get("executions") or [],
        "post_status": {
            "status": post_status.get("status"),
            "product_name": (
                post_status.get("product_state", {}).get("name")
                if isinstance(post_status.get("product_state"), dict)
                else ""
            ),
        },
        "recommended_next_action": next_action,
        "user_next_message": next_action.get("user_next_message") or "",
        "files": run.get("files") or {},
        "created_artifacts": result.get("artifacts") if isinstance(result.get("artifacts"), dict) else {},
        "result_summary": {
            "status": result.get("status"),
            "target": result.get("target"),
            "best_variant": result.get("best_variant"),
            "channel_review_run_id": result.get("channel_review_run_id"),
            "intent_id": result.get("intent_id"),
            "brief_id": result.get("brief_id"),
            "payload_id": result.get("payload_id"),
            "job_id": result.get("job_id"),
            "reference_readiness_id": result.get("reference_readiness_id"),
            "policy_id": result.get("policy_id"),
            "video_task_id": result.get("video_task_id"),
            "video_task_status_id": result.get("video_task_status_id"),
            "result_id": result.get("result_id"),
        },
        "safety": run.get("safety") or {},
        "response_guidance": "Answer the user in natural language. Prefer user_next_message over developer_command; do not present scripts as the normal product flow.",
        "full_result_note": "Full nested workflow result is written to files.json; use the file path in files.json for audit details.",
    }


def product_agent_turn(
    product_id: str = "",
    product_query: str = "",
    create_if_missing: bool = False,
    suggested_id: str = "",
    name: str = "",
    action: str = "",
    message: str = "",
    confirmed: bool = False,
    proposal_id: str = "",
    target: str = "",
    variants: int = 3,
    text: str = "",
    images: List[str] | None = None,
    note: str = "",
    path: str = "",
    role: str = "",
    description: str = "",
    usage: List[str] | None = None,
    asset: str = "",
    provider: str = "",
    analysis: str = "",
    max_steps: int = 5,
) -> Dict[str, Any]:
    resolution: Dict[str, Any] = {}
    resolved_product_id = product_id or ""
    if not resolved_product_id and product_query:
        resolution = resolve_product_workspace(
            product_query,
            bool(create_if_missing),
            suggested_id,
            name,
            5,
        )
        resolved_product_id = resolution.get("selected_product_id") or ""
    if not resolved_product_id:
        return {
            "success": False,
            "schema_version": AGENT_TURN_SCHEMA_VERSION,
            "error": "product_id is required. Use product_workspace_resolve first, or pass product_query with a unique match.",
            "workspace_resolution": resolution,
            "response_guidance": "Ask the user which product workspace to use, or ask for confirmation to create one.",
        }

    run_message = message or ""
    if resolution.get("created") and not action:
        run_message = ""

    run = workflow_run(
        resolved_product_id,
        action,
        run_message,
        bool(confirmed),
        proposal_id,
        target,
        int(variants or 3),
        name,
        text,
        _list(images),
        note,
        path,
        role,
        description,
        _list(usage),
        asset,
        provider,
        analysis,
        int(max_steps or 5),
    )
    workflow_instance = run.get("workflow_instance") if isinstance(run.get("workflow_instance"), dict) else {}
    compact = compact_workflow_run_result(run)
    compact["workflow_instance"] = workflow_instance
    if resolution:
        compact["workspace_resolution"] = resolution
    return compact
