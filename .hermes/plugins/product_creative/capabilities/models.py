"""Capability descriptors and execution extension contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Tuple


ActionExecutor = Callable[[Dict[str, Any]], Dict[str, Any]]
ActionPolicy = Callable[[Dict[str, Any]], Dict[str, Any] | None]
ActionBinder = Callable[[Dict[str, Any]], bool]
MissingInputPolicy = Callable[[Dict[str, Any]], Iterable[str]]
CommandAdapter = Callable[[Dict[str, Any]], str]
IntentMatcher = Callable[[str], bool]


@dataclass(frozen=True)
class CommandDescriptor:
    name: str
    schema: Dict[str, Any]
    handler: CommandAdapter
    capability: str
    compatibility_handler_name: str


@dataclass(frozen=True)
class ActionRuntimeDefinition:
    name: str
    execute: ActionExecutor
    auto_advance: bool = False
    idempotency_fields: tuple[str, ...] = ()
    plan_policy: ActionPolicy | None = None
    guard_policy: ActionPolicy | None = None
    execution_binder: ActionBinder | None = None
    conversation_binder: ActionBinder | None = None
    missing_input_policy: MissingInputPolicy | None = None


@dataclass(frozen=True)
class ActionDescriptor:
    name: str
    tool: str
    domain: str
    runtime: ActionRuntimeDefinition
    requires_user_input: bool = False
    requires_explicit_confirmation: bool = False
    writes_product_workspace: bool = True
    mutates_confirmed_product_brain: bool = False
    side_effect: str = "workspace"
    requires_existing_product: bool = True
    modality: str = ""
    captures_creative_brief: bool = False

    def contract(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "domain": self.domain,
            "requires_user_input": self.requires_user_input,
            "requires_explicit_confirmation": self.requires_explicit_confirmation,
            "writes_product_workspace": self.writes_product_workspace,
            "mutates_confirmed_product_brain": self.mutates_confirmed_product_brain,
            "modality": self.modality,
            "captures_creative_brief": self.captures_creative_brief,
        }


@dataclass(frozen=True)
class WorkflowFragment:
    name: str
    version: str
    actions: Tuple[str, ...]


@dataclass(frozen=True)
class CapabilityDescriptor:
    name: str
    actions: Tuple[ActionDescriptor, ...]
    workflows: Tuple[WorkflowFragment, ...] = ()
    artifact_types: Tuple[str, ...] = ()
    event_types: Tuple[str, ...] = ()


@dataclass(frozen=True)
class IntentRule:
    action: str
    priority: int
    matcher: IntentMatcher


def action_descriptor(
    runtime: ActionRuntimeDefinition,
    *,
    tool: str,
    domain: str,
    requires_user_input: bool = False,
    requires_explicit_confirmation: bool = False,
    mutates_product_brain: bool = False,
    side_effect: str = "workspace",
    requires_existing_product: bool = True,
    modality: str = "",
    captures_creative_brief: bool = False,
) -> ActionDescriptor:
    return ActionDescriptor(
        name=runtime.name,
        tool=tool,
        domain=domain,
        runtime=runtime,
        requires_user_input=requires_user_input,
        requires_explicit_confirmation=requires_explicit_confirmation,
        mutates_confirmed_product_brain=mutates_product_brain,
        side_effect=side_effect,
        requires_existing_product=requires_existing_product,
        modality=modality,
        captures_creative_brief=captures_creative_brief,
    )
