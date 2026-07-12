from __future__ import annotations

from typing import Iterable

from ..models import ActionRuntimeDefinition
from .service import brain_rollback, proposal_decide, provider_refresh, rule_revoke, workflow_recover


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (
        ActionRuntimeDefinition("product_proposal_decide", proposal_decide, idempotency_fields=("proposal_id", "decision", "expected_version")),
        ActionRuntimeDefinition("product_brain_rollback", brain_rollback, idempotency_fields=("target_version", "expected_version")),
        ActionRuntimeDefinition("product_workflow_retry", lambda args: workflow_recover(args, "retry"), idempotency_fields=("workflow_id", "expected_version")),
        ActionRuntimeDefinition("product_workflow_cancel", lambda args: workflow_recover(args, "cancel"), idempotency_fields=("workflow_id", "expected_version")),
        ActionRuntimeDefinition("product_provider_task_refresh", provider_refresh, idempotency_fields=("provider_task_id",)),
        ActionRuntimeDefinition("product_rule_revoke", rule_revoke, idempotency_fields=("rule_id",)),
    )


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
