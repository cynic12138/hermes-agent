"""Discoverable workflow-definition registry for Product Creative."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

from ..capabilities.registry import workflow_fragments


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    version: str
    actions: Tuple[str, ...]

    def actions_from(self, action: str) -> Tuple[str, ...]:
        try:
            return self.actions[self.actions.index(action):]
        except ValueError:
            return (action,)


@lru_cache(maxsize=1)
def workflow_definitions() -> Tuple[WorkflowDefinition, ...]:
    definitions = tuple(
        WorkflowDefinition(fragment.name, fragment.version, fragment.actions)
        for fragment in workflow_fragments()
    )
    names = [definition.name for definition in definitions]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise RuntimeError(f"duplicate Product Creative workflow definitions: {duplicates}")
    return definitions


def _action_index() -> Dict[str, WorkflowDefinition]:
    index: Dict[str, WorkflowDefinition] = {}
    for definition in workflow_definitions():
        for action in definition.actions:
            index.setdefault(action, definition)
    return index


def workflow_definition_for_action(action: str) -> WorkflowDefinition:
    return _action_index().get(action) or WorkflowDefinition(f"single_action.{action}", "1.0", (action,))


# Compatibility export for callers that enumerate the catalog.
WORKFLOW_DEFINITIONS = workflow_definitions()
