"""Registry-driven argument binding for workflow execution adapters."""

from __future__ import annotations

from typing import Any, Dict, List

from .action_registry import bind_action_execution_args
from .decision import url_from_message
from .planning import missing_inputs, plan_status


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _refresh_plan_status(plan: Dict[str, Any]) -> None:
    step = (plan.get("steps") or [{}])[0]
    action = _text(step.get("action"))
    args = step.get("args_template") if isinstance(step.get("args_template"), dict) else {}
    confirmed = bool(step.get("confirmed") or (plan.get("guard_result") or {}).get("confirmed"))
    missing = missing_inputs(action, args, confirmed)
    status = plan_status(plan.get("guard_result") or {}, missing)
    step["missing_inputs"] = missing
    step["status"] = status
    step["requires_user_input"] = bool(missing and "explicit_confirmation" not in missing)
    plan["status"] = status
    plan["ready_to_execute"] = status == "ready_to_execute"
    plan["requires_user_input"] = bool(step["requires_user_input"])
    plan["requires_explicit_confirmation"] = "explicit_confirmation" in missing


def _apply_execution_args(
    plan: Dict[str, Any],
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
) -> None:
    step = (plan.get("steps") or [{}])[0]
    args = step.get("args_template") if isinstance(step.get("args_template"), dict) else {}
    action = _text(step.get("action"))
    confirmed = bool(step.get("confirmed") or (plan.get("guard_result") or {}).get("confirmed"))
    bind_action_execution_args(
        action,
        {
            "action": action,
            "plan": plan,
            "step": step,
            "args": args,
            "confirmed": confirmed,
            "name": name,
            "text": text,
            "images": images or [],
            "note": note,
            "path": path,
            "role": role,
            "description": description,
            "usage": usage or [],
            "asset": asset,
            "provider": provider,
            "analysis": analysis,
            "url_from_note": url_from_message(note),
        },
    )
    _refresh_plan_status(plan)
