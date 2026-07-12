"""Workflow execution dispatcher and bounded run loop for Product Creative runtime."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from ..common import now_iso, product_dir, timestamp
from ..contracts.models import ActionCommand, CreativeTaskBrief, IntentDecision
from .action_registry import action_auto_advance, execute_command
from ..capabilities.registry import action_descriptors
from .conversation import conversation_adapter
from .errors import classify_exception, error_result, record_runtime_error
from .planning import workflow_next, workflow_plan
from .execution_arguments import _apply_execution_args
from .state import safety_contract as _safety_contract
from .state import workflow_status
from .tracing import write_workflow_run_record
from .workflow_catalog import workflow_definition_for_action
from ..durable_workflow.engine import durable_workflow_engine


WORKFLOW_EXECUTE_SCHEMA_VERSION = "product_creative.workflow_execute.v4.9"
WORKFLOW_RUN_SCHEMA_VERSION = "product_creative.workflow_run.v4.9"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []




def _execute_ready_step(
    step: Dict[str, Any],
    product_id: str,
    trace_id: str,
    execution_id: str,
    workflow_id: str,
    workflow_step_id: str,
    idempotency_key: str,
) -> Dict[str, Any]:
    action = _text(step.get("action"))
    args = step.get("args_template") if isinstance(step.get("args_template"), dict) else {}
    command = ActionCommand(
        action=action,
        product_id=product_id,
        workflow_id=workflow_id,
        step_id=workflow_step_id,
        trace_id=trace_id,
        idempotency_key=idempotency_key,
        confirmed=bool(step.get("confirmed")),
        args=args,
    )
    return execute_command(command).output


def _intent_for_plan(product_id: str, message: str, adapter: Dict[str, Any], plan: Dict[str, Any]) -> IntentDecision:
    step = (plan.get("steps") or [{}])[0]
    raw = adapter.get("interpreted_intent") if isinstance(adapter.get("interpreted_intent"), dict) else {}
    allowed = {name: value for name, value in raw.items() if name in IntentDecision.model_fields}
    allowed["product_id"] = product_id
    allowed["action"] = _text(plan.get("requested_action") or step.get("action"))
    allowed.setdefault("goal", _text(message))
    allowed.setdefault("confidence", 1.0 if not message else 0.65)
    allowed.setdefault("source", "explicit_action" if not message else "rule_fallback")
    return IntentDecision.model_validate(allowed)


def workflow_execute(
    product_id: str,
    action: str = "",
    message: str = "",
    confirmed: bool = False,
    proposal_id: str = "",
    target: str = "",
    variants: int = 3,
    name: str = "",
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
    trace_id: str = "",
) -> Dict[str, Any]:
    product_id = _text(product_id)
    execution_id = f"workflow-exec-{uuid.uuid4().hex}"
    trace_id = _text(trace_id) or f"trace-{uuid.uuid4().hex}"
    if _text(message):
        adapter = conversation_adapter(product_id, message, confirmed, proposal_id, target, variants)
        plan = adapter["plan"]
        plan_source = "conversation_adapter"
    else:
        adapter = {}
        plan = workflow_plan(product_id, action, confirmed, proposal_id, target, variants)
        plan_source = "workflow_plan"

    _apply_execution_args(plan, name, text, images, note, path, role, description, usage, asset, provider, analysis)
    step = (plan.get("steps") or [{}])[0]
    intent = _intent_for_plan(product_id, message, adapter, plan)
    descriptor = action_descriptors().get(intent.action)
    if descriptor and descriptor.captures_creative_brief and _text(message):
        args = step.get("args_template") if isinstance(step.get("args_template"), dict) else {}
        args["creative_brief"] = CreativeTaskBrief(
            goal=_text(intent.goal) or _text(message),
            raw_message=_text(message),
            channel=_text(intent.channel),
            target=_text(intent.target) or _text(args.get("target")),
            constraints=list(intent.constraints),
            requested_outputs=list(intent.requested_outputs),
            source=intent.source,
        ).model_dump(mode="json")
    definition = workflow_definition_for_action(intent.action)
    handle = durable_workflow_engine().begin_step(
        product_id=product_id,
        definition=definition,
        decision=intent,
        args=step.get("args_template") if isinstance(step.get("args_template"), dict) else {},
        trace_id=trace_id,
        runnable=bool(plan.get("ready_to_execute")),
        pause_reason=_text(plan.get("status")),
    )
    trace_id = handle.trace_id
    durable_summary = durable_workflow_engine().summary_for(handle.workflow_id)
    if not plan.get("ready_to_execute"):
        return {
            "success": True,
            "schema_version": WORKFLOW_EXECUTE_SCHEMA_VERSION,
            "execution_id": execution_id,
            "trace_id": trace_id,
            "product_id": plan.get("product_id", product_id),
            "plan_source": plan_source,
            "message": message,
            "executed": False,
            "execution_status": "not_executed",
            "reason": step.get("guard_reason") or f"Plan is {plan.get('status')}.",
            "plan": plan,
            "conversation": adapter,
            "result": {},
            "post_status": workflow_status(product_id),
            "safety": plan.get("safety", _safety_contract()),
            "workflow_instance": durable_summary,
        }

    try:
        result = _execute_ready_step(
            step,
            product_id,
            trace_id,
            execution_id,
            handle.workflow_id,
            handle.step_id,
            handle.idempotency_key,
        )
    except Exception as exc:
        error = classify_exception(
            exc,
            "workflow_action_execution",
            product_id,
            _text(step.get("action")),
            trace_id,
        )
        record_runtime_error(error)
        result = error_result(error)
    error_payload = result.get("error") if isinstance(result.get("error"), dict) else {}
    durable_summary = durable_workflow_engine().complete_step(
        handle,
        result,
        bool(result.get("success", False)),
        str(error_payload.get("error_code") or result.get("error_code") or ""),
        str(error_payload.get("error_message") or result.get("error_message") or ""),
    )
    return {
        "success": bool(result.get("success", False)),
        "schema_version": WORKFLOW_EXECUTE_SCHEMA_VERSION,
        "execution_id": execution_id,
        "trace_id": trace_id,
        "product_id": plan.get("product_id", product_id),
        "plan_source": plan_source,
        "message": message,
        "executed": bool(result.get("success", False)),
        "execution_status": "executed" if result.get("success", False) else "failed",
        "reason": step.get("guard_reason", ""),
        "plan": plan,
        "conversation": adapter,
        "result": result,
        "post_status": workflow_status(product_id),
        "safety": plan.get("safety", _safety_contract()),
        "workflow_instance": durable_summary,
    }


def _run_stop_reason(execution: Dict[str, Any], auto_step: bool) -> str:
    if execution.get("execution_status") == "failed":
        return "step_failed"
    plan = execution.get("plan") if isinstance(execution.get("plan"), dict) else {}
    step = (plan.get("steps") or [{}])[0]
    if execution.get("executed"):
        return ""
    if plan.get("requires_explicit_confirmation") or step.get("requires_explicit_confirmation"):
        return "requires_explicit_confirmation"
    if plan.get("requires_user_input") or step.get("requires_user_input"):
        return "requires_user_input"
    if not auto_step:
        return "initial_step_not_executed"
    return "blocked_by_guard"


def _auto_step_allowed(plan: Dict[str, Any]) -> bool:
    step = (plan.get("steps") or [{}])[0]
    action = _text(step.get("action"))
    if not plan.get("ready_to_execute"):
        return False
    if step.get("requires_explicit_confirmation") or plan.get("requires_explicit_confirmation"):
        return False
    if step.get("requires_user_input") or plan.get("requires_user_input"):
        return False
    if step.get("mutates_product_brain") or plan.get("mutates_product_brain"):
        return False
    descriptor = action_descriptors().get(action)
    if descriptor and descriptor.side_effect == "provider":
        args = step.get("args_template") if isinstance(step.get("args_template"), dict) else {}
        provider = _text(args.get("provider") or "mock")
        mode = _text(args.get("mode"))
        if not provider.startswith("mock") and mode != "mock":
            return False
    return action_auto_advance(action)


def _execution_action(execution: Dict[str, Any]) -> str:
    plan = execution.get("plan") if isinstance(execution.get("plan"), dict) else {}
    step = (plan.get("steps") or [{}])[0]
    return _text(plan.get("requested_action") or step.get("action"))


def _execution_summary(execution: Dict[str, Any]) -> Dict[str, Any]:
    plan = execution.get("plan") if isinstance(execution.get("plan"), dict) else {}
    step = (plan.get("steps") or [{}])[0]
    result = execution.get("result") if isinstance(execution.get("result"), dict) else {}
    return {
        "execution_id": _text(execution.get("execution_id")),
        "action": _text(plan.get("requested_action") or step.get("action")),
        "executed": bool(execution.get("executed")),
        "execution_status": _text(execution.get("execution_status")),
        "plan_status": _text(plan.get("status")),
        "tool": _text(step.get("tool")),
        "result_id": _text(
            result.get("material_id")
            or result.get("analysis_id")
            or result.get("alignment_id")
            or result.get("material_card_id")
            or result.get("task_material_pack_id")
            or result.get("feedback_id")
            or result.get("intent_id")
            or result.get("brief_id")
            or result.get("review_package_id")
            or result.get("review_id")
            or result.get("policy_id")
            or result.get("payload_id")
            or result.get("reference_readiness_id")
            or result.get("readiness_id")
            or result.get("video_task_id")
            or result.get("video_task_status_id")
            or result.get("image_run_id")
            or result.get("result_id")
            or result.get("proposal_id")
        ),
    }


def workflow_run(
    product_id: str,
    action: str = "",
    message: str = "",
    confirmed: bool = False,
    proposal_id: str = "",
    target: str = "",
    variants: int = 3,
    name: str = "",
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
    product_id = _text(product_id)
    max_steps = max(1, min(int(max_steps or 5), 10))
    trace_id = f"trace-{uuid.uuid4().hex}"
    executions: List[Dict[str, Any]] = []
    stop_reason = ""

    first = workflow_execute(
        product_id,
        action,
        message,
        confirmed,
        proposal_id,
        target,
        variants,
        name,
        text,
        images,
        note,
        path,
        role,
        description,
        usage,
        asset,
        provider,
        analysis,
        trace_id,
    )
    executions.append(first)
    first_conversation = first.get("conversation") if isinstance(first.get("conversation"), dict) else {}
    initial_intent = (
        first_conversation.get("interpreted_intent")
        if isinstance(first_conversation.get("interpreted_intent"), dict)
        else {}
    )
    if not first.get("executed"):
        stop_reason = _run_stop_reason(first, False)
    elif first.get("execution_status") == "failed":
        stop_reason = "step_failed"

    initial_action = _execution_action(first)
    workflow_definition = workflow_definition_for_action(initial_action)
    workflow_actions = list(workflow_definition.actions_from(initial_action))

    while not stop_reason and len(executions) < max_steps:
        previous_action = _execution_action(executions[-1])
        try:
            previous_index = workflow_actions.index(previous_action)
        except ValueError:
            stop_reason = "workflow_definition_mismatch"
            break
        if previous_index + 1 >= len(workflow_actions):
            stop_reason = "workflow_definition_completed"
            break
        next_action = workflow_actions[previous_index + 1]
        plan = workflow_plan(product_id, next_action, False, "", "", variants)
        if not _auto_step_allowed(plan):
            stop_reason = _run_stop_reason(
                {
                    "executed": False,
                    "execution_status": "not_executed",
                    "plan": plan,
                },
                True,
            )
            break
        next_execution = workflow_execute(
            product_id,
            action=_text(plan.get("requested_action")),
            variants=variants,
            trace_id=trace_id,
        )
        executions.append(next_execution)
        if not next_execution.get("executed"):
            stop_reason = _run_stop_reason(next_execution, True)
            break
        if next_execution.get("execution_status") == "failed":
            stop_reason = "step_failed"
            break

    if not stop_reason and len(executions) >= max_steps:
        stop_reason = "max_steps_reached"

    post_status = workflow_status(product_id)
    next_step = workflow_next(product_id)
    run_id = f"workflow-run-{timestamp()}"
    run = {
        "success": all(item.get("success", False) for item in executions),
        "schema_version": WORKFLOW_RUN_SCHEMA_VERSION,
        "workflow_run_id": run_id,
        "trace_id": trace_id,
        "run_id": run_id,
        "product_id": post_status.get("product_id", product_id),
        "created_at": now_iso(),
        "executed_count": len([item for item in executions if item.get("executed")]),
        "attempted_count": len(executions),
        "max_steps": max_steps,
        "workflow_definition": workflow_definition.name,
        "workflow_definition_version": workflow_definition.version,
        "stop_reason": stop_reason,
        "initial_message": message,
        "initial_intent": initial_intent,
        "executions": [_execution_summary(item) for item in executions],
        "last_execution": executions[-1] if executions else {},
        "workflow_instance": (executions[-1].get("workflow_instance") if executions else {}),
        "post_status": post_status,
        "recommended_next_action": next_step.get("recommended_action", {}),
        "safety": post_status.get("safety", _safety_contract()),
    }
    files: Dict[str, str] = {}
    if post_status.get("exists"):
        files = write_workflow_run_record(product_dir(product_id), run)
    run["files"] = files
    return run
