from __future__ import annotations

from ..models import CapabilityDescriptor, WorkflowFragment, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        name="content",
        actions=(
            action_descriptor(runtime("run_channel_review"), tool="product_channel_review_run", domain="channel_content", requires_user_input=True, modality="text", captures_creative_brief=True),
        ),
        workflows=(
            WorkflowFragment(
                "channel_content_learning", "2.0",
                ("run_channel_review", "record_channel_feedback", "create_evolution_proposal", "apply_evolution_proposal"),
            ),
        ),
        artifact_types=("channel_content", "channel_review_run", "channel_feedback"),
    )
