"""Hermes adapters for M9 recovery; all execution is delegated to CommandBus."""

from __future__ import annotations

from typing import Any, Dict

from ...application.command_bus import command_bus
from ...common import json_text
from ..models import CommandDescriptor
from . import schemas


def _handler(name: str):
    def invoke(args: Dict[str, Any], **_kw: Any) -> str:
        return json_text(command_bus().invoke(name, args))
    return invoke


def command_descriptors() -> tuple[CommandDescriptor, ...]:
    definitions = (
        ("product_proposal_decide", schemas.PRODUCT_PROPOSAL_DECIDE_SCHEMA),
        ("product_brain_rollback", schemas.PRODUCT_BRAIN_ROLLBACK_SCHEMA),
        ("product_workflow_retry", schemas.PRODUCT_WORKFLOW_RETRY_SCHEMA),
        ("product_workflow_cancel", schemas.PRODUCT_WORKFLOW_CANCEL_SCHEMA),
        ("product_provider_task_refresh", schemas.PRODUCT_PROVIDER_TASK_REFRESH_SCHEMA),
        ("product_rule_revoke", schemas.PRODUCT_RULE_REVOKE_SCHEMA),
    )
    return tuple(CommandDescriptor(name, schema, _handler(name), "recovery", f"_handle_{name}") for name, schema in definitions)
