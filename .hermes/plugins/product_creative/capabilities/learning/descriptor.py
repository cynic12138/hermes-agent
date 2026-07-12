from __future__ import annotations

from ..models import CapabilityDescriptor, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        name="learning",
        actions=(
            action_descriptor(runtime("record_image_result_feedback"), tool="product_result_feedback", domain="learning", requires_user_input=True, modality="feedback"),
            action_descriptor(runtime("record_video_result_feedback"), tool="product_result_feedback", domain="learning", requires_user_input=True, modality="feedback"),
            action_descriptor(runtime("record_video_brief_feedback"), tool="product_video_brief_feedback", domain="learning", requires_user_input=True, modality="feedback"),
            action_descriptor(runtime("record_channel_feedback"), tool="product_channel_feedback", domain="learning", requires_user_input=True, modality="feedback"),
            action_descriptor(runtime("create_evolution_proposal"), tool="product_evolve", domain="learning", modality="learning"),
            action_descriptor(runtime("apply_evolution_proposal"), tool="product_evolve", domain="learning", requires_explicit_confirmation=True, mutates_product_brain=True, side_effect="product_brain", modality="brain"),
        ),
        event_types=("rule.candidate_created", "proposal.created", "product_brain.version_applied"),
    )
