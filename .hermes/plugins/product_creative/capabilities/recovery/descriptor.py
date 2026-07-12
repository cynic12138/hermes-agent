from __future__ import annotations

from ..models import CapabilityDescriptor, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    actions = tuple(
        action_descriptor(runtime(name), tool=name, domain="recovery", requires_explicit_confirmation=True,
                          mutates_product_brain=name in {"product_proposal_decide", "product_brain_rollback"},
                          side_effect="product_brain" if name in {"product_proposal_decide", "product_brain_rollback"} else "recovery",
                          modality="brain" if "brain" in name or "proposal" in name else "review")
        for name in (
            "product_proposal_decide", "product_brain_rollback", "product_workflow_retry",
            "product_workflow_cancel", "product_provider_task_refresh", "product_rule_revoke",
        )
    )
    return CapabilityDescriptor(
        name="recovery", actions=actions,
        event_types=("proposal.decided", "product_brain.rolled_back", "rule.revoked", "workflow.retry_requested", "workflow.cancelled", "provider_task.refreshed"),
    )
