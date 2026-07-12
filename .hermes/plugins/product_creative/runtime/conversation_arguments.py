"""Registry-driven conversation argument binding for workflow plans."""

from __future__ import annotations

from typing import Any, Dict

from .action_registry import bind_action_conversation_args
from .decision import (
    duration_from_message,
    exact_video_template_from_message,
    external_mode_from_message,
    external_provider_from_message,
    fps_from_message,
    message_allows_evolution,
    message_indicates_rejected,
    message_indicates_selected,
    rating_from_message,
    target_from_message,
    url_from_message,
    variant_from_message,
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _remove_missing_input(plan: Dict[str, Any], key: str) -> None:
    step = (plan.get("steps") or [{}])[0]
    missing = [item for item in step.get("missing_inputs", []) if item != key]
    step["missing_inputs"] = missing
    step["requires_user_input"] = bool(missing and "explicit_confirmation" not in missing)
    if plan.get("guard_result", {}).get("allowed") and not missing:
        step["status"] = "ready_to_execute"
        plan["status"] = "ready_to_execute"
        plan["ready_to_execute"] = True
        plan["requires_user_input"] = False


def _apply_conversation_args(plan: Dict[str, Any], message: str, confirmed: bool = False) -> None:
    step = (plan.get("steps") or [{}])[0]
    args = step.get("args_template") if isinstance(step.get("args_template"), dict) else {}
    action = _text(step.get("action"))
    bind_action_conversation_args(
        action,
        {
            "action": action,
            "plan": plan,
            "step": step,
            "args": args,
            "message": message,
            "confirmed": confirmed,
            "variant": variant_from_message(message),
            "rating": rating_from_message(message),
            "selected": message_indicates_selected(message),
            "rejected": message_indicates_rejected(message),
            "allow_evolve": message_allows_evolution(message),
            "duration": duration_from_message(message),
            "fps": fps_from_message(message),
            "url": url_from_message(message),
            "target": target_from_message(message),
            "external_provider": external_provider_from_message(message),
            "external_mode": external_mode_from_message(message),
            "exact_video_template": exact_video_template_from_message(message),
            "remove_missing_input": lambda key: _remove_missing_input(plan, key),
        },
    )
