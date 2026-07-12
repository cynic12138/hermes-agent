"""Dynamic registry assembled from capability-owned descriptors."""

from __future__ import annotations

from functools import lru_cache
import importlib
import pkgutil
from typing import Any, Callable, Dict, Tuple

from .models import ActionDescriptor, CapabilityDescriptor, CommandDescriptor, IntentRule, WorkflowFragment


@lru_cache(maxsize=1)
def capability_registry() -> Dict[str, CapabilityDescriptor]:
    package = importlib.import_module(__package__ or "product_creative.capabilities")

    registry: Dict[str, CapabilityDescriptor] = {}
    for module_info in sorted(pkgutil.iter_modules(package.__path__), key=lambda item: item.name):
        if not module_info.ispkg or module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{package.__name__}.{module_info.name}.descriptor")
        factory = getattr(module, "capability_descriptor", None)
        if not callable(factory):
            raise RuntimeError(f"capability '{module_info.name}' has no capability_descriptor()")
        descriptor = factory()
        if descriptor.name in registry:
            raise RuntimeError(f"duplicate capability '{descriptor.name}'")
        registry[descriptor.name] = descriptor
    action_names: set[str] = set()
    workflow_names: set[str] = set()
    for descriptor in registry.values():
        for action in descriptor.actions:
            if action.name in action_names:
                raise RuntimeError(f"duplicate capability action '{action.name}'")
            action_names.add(action.name)
        for workflow in descriptor.workflows:
            if workflow.name in workflow_names:
                raise RuntimeError(f"duplicate capability workflow '{workflow.name}'")
            workflow_names.add(workflow.name)
    return registry


def action_descriptors() -> Dict[str, ActionDescriptor]:
    return {
        action.name: action
        for capability in capability_registry().values()
        for action in capability.actions
    }


def workflow_fragments() -> Tuple[WorkflowFragment, ...]:
    return tuple(
        workflow
        for capability in capability_registry().values()
        for workflow in capability.workflows
    )


@lru_cache(maxsize=1)
def command_descriptors() -> Dict[str, CommandDescriptor]:
    package = importlib.import_module(__package__ or "product_creative.capabilities")
    commands: Dict[str, CommandDescriptor] = {}
    for module_info in sorted(pkgutil.iter_modules(package.__path__), key=lambda item: item.name):
        if not module_info.ispkg or module_info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{package.__name__}.{module_info.name}.commands")
        except ModuleNotFoundError as exc:
            if exc.name == f"{package.__name__}.{module_info.name}.commands":
                continue
            raise
        factory = getattr(module, "command_descriptors", None)
        if not callable(factory):
            raise RuntimeError(f"capability '{module_info.name}' has no command_descriptors()")
        for descriptor in factory():
            if descriptor.name in commands:
                raise RuntimeError(f"duplicate capability command '{descriptor.name}'")
            commands[descriptor.name] = descriptor
    return commands


@lru_cache(maxsize=1)
def guard_policies() -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:
    package = importlib.import_module(__package__ or "product_creative.capabilities")
    policies: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
    for capability in capability_registry():
        try:
            module = importlib.import_module(f"{package.__name__}.{capability}.policy")
        except ModuleNotFoundError as exc:
            if exc.name == f"{package.__name__}.{capability}.policy":
                continue
            raise
        for action, policy in getattr(module, "GUARD_POLICIES", {}).items():
            if action in policies:
                raise RuntimeError(f"duplicate guard policy '{action}'")
            policies[action] = policy
    return policies


@lru_cache(maxsize=1)
def plan_templates() -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:
    package = importlib.import_module(__package__ or "product_creative.capabilities")
    templates: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
    for capability in capability_registry():
        try:
            module = importlib.import_module(f"{package.__name__}.{capability}.planning")
        except ModuleNotFoundError as exc:
            if exc.name == f"{package.__name__}.{capability}.planning":
                continue
            raise
        for action, template in getattr(module, "PLAN_TEMPLATES", {}).items():
            if action in templates:
                raise RuntimeError(f"duplicate plan template '{action}'")
            templates[action] = template
    return templates


def _binding_registry(attribute: str) -> Dict[str, Callable[[Dict[str, Any]], bool]]:
    package = importlib.import_module(__package__ or "product_creative.capabilities")
    binders: Dict[str, Callable[[Dict[str, Any]], bool]] = {}
    for capability in capability_registry():
        try:
            module = importlib.import_module(f"{package.__name__}.{capability}.binding")
        except ModuleNotFoundError as exc:
            if exc.name == f"{package.__name__}.{capability}.binding":
                continue
            raise
        for action, binder in getattr(module, attribute, {}).items():
            if action in binders:
                raise RuntimeError(f"duplicate {attribute.lower()} '{action}'")
            binders[action] = binder
    return binders


@lru_cache(maxsize=1)
def execution_binders() -> Dict[str, Callable[[Dict[str, Any]], bool]]:
    return _binding_registry("EXECUTION_BINDERS")


@lru_cache(maxsize=1)
def conversation_binders() -> Dict[str, Callable[[Dict[str, Any]], bool]]:
    return _binding_registry("CONVERSATION_BINDERS")


@lru_cache(maxsize=1)
def intent_rules() -> Tuple[IntentRule, ...]:
    package = importlib.import_module(__package__ or "product_creative.capabilities")
    rules: list[IntentRule] = []
    known_actions = action_descriptors()
    for capability in capability_registry():
        try:
            module = importlib.import_module(f"{package.__name__}.{capability}.intent")
        except ModuleNotFoundError as exc:
            if exc.name == f"{package.__name__}.{capability}.intent":
                continue
            raise
        for rule in getattr(module, "INTENT_RULES", ()):
            if rule.action not in known_actions:
                raise RuntimeError(f"intent rule references unknown action '{rule.action}'")
            rules.append(rule)
    return tuple(sorted(rules, key=lambda rule: (rule.priority, rule.action)))


@lru_cache(maxsize=1)
def recommendation_policies() -> Tuple[Tuple[int, Callable[[Dict[str, Any]], str]], ...]:
    package = importlib.import_module(__package__ or "product_creative.capabilities")
    policies: list[Tuple[int, Callable[[Dict[str, Any]], str]]] = []
    for capability in capability_registry():
        try:
            module = importlib.import_module(f"{package.__name__}.{capability}.recommendation")
        except ModuleNotFoundError as exc:
            if exc.name == f"{package.__name__}.{capability}.recommendation":
                continue
            raise
        policy = getattr(module, "recommend_action", None)
        if callable(policy):
            policies.append((int(getattr(module, "PRIORITY", 100)), policy))
    return tuple(sorted(policies, key=lambda item: item[0]))
