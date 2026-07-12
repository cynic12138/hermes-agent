"""Registry of executable Product Creative actions."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from ..capabilities.models import ActionRuntimeDefinition
from ..capabilities.registry import action_descriptors, conversation_binders, execution_binders
from ..contracts.models import ActionCommand, ActionResult
from ..application.action_executor import capability_executor


@lru_cache(maxsize=1)
def action_runtime_registry() -> Dict[str, ActionRuntimeDefinition]:
    return {name: descriptor.runtime for name, descriptor in action_descriptors().items()}


def get_action_runtime(action: str) -> ActionRuntimeDefinition:
    definition = action_runtime_registry().get(action)
    if definition is None:
        raise KeyError(f"unknown Product Creative action '{action}'")
    return definition


def execute_action(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    product_id = str(args.get("product_id") or "")
    return capability_executor().execute(
        ActionCommand(action=action, product_id=product_id, args=dict(args))
    ).output


def execute_command(command: ActionCommand) -> ActionResult:
    return capability_executor().execute(command)


def action_auto_advance(action: str) -> bool:
    definition = action_runtime_registry().get(action)
    return bool(definition and definition.auto_advance)


def action_plan_override(action: str, context: Dict[str, Any]) -> Dict[str, Any] | None:
    definition = action_runtime_registry().get(action)
    return definition.plan_policy(dict(context)) if definition and definition.plan_policy else None


def action_guard_override(action: str, context: Dict[str, Any]) -> Dict[str, Any] | None:
    definition = action_runtime_registry().get(action)
    return definition.guard_policy(dict(context)) if definition and definition.guard_policy else None


def bind_action_execution_args(action: str, context: Dict[str, Any]) -> bool:
    definition = action_runtime_registry().get(action)
    binder = definition.execution_binder if definition and definition.execution_binder else execution_binders().get(action)
    return bool(binder and binder(context))


def bind_action_conversation_args(action: str, context: Dict[str, Any]) -> bool:
    definition = action_runtime_registry().get(action)
    binder = definition.conversation_binder if definition and definition.conversation_binder else conversation_binders().get(action)
    return bool(binder and binder(context))


def action_missing_inputs(action: str, context: Dict[str, Any]) -> list[str]:
    definition = action_runtime_registry().get(action)
    if not definition or not definition.missing_input_policy:
        return []
    return [str(item) for item in definition.missing_input_policy(dict(context)) if str(item)]
