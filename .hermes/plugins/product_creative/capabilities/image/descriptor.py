from __future__ import annotations

from ..models import CapabilityDescriptor, WorkflowFragment, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        name="image",
        actions=(
            action_descriptor(runtime("resolve_image_intent"), tool="product_image_intent", domain="image", requires_user_input=True),
            action_descriptor(runtime("create_image_brief"), tool="product_image_brief", domain="image"),
            action_descriptor(runtime("review_image_brief"), tool="product_image_brief_review_package", domain="image"),
            action_descriptor(runtime("revise_image_brief"), tool="product_image_brief_revise", domain="image", requires_user_input=True, requires_explicit_confirmation=True),
            action_descriptor(runtime("create_batch_generation_policy"), tool="product_batch_generation_policy", domain="image", requires_user_input=True, requires_explicit_confirmation=True),
            action_descriptor(runtime("build_image_provider_payload"), tool="product_image_provider_payload", domain="image"),
            action_descriptor(runtime("check_image_live_readiness"), tool="product_live_readiness", domain="image"),
            action_descriptor(runtime("submit_image_generation_job"), tool="product_image_generation_run", domain="image", side_effect="provider"),
        ),
        workflows=(
            WorkflowFragment(
                "image_creation_learning", "2.0",
                (
                    "resolve_image_intent", "create_image_brief", "review_image_brief", "revise_image_brief",
                    "create_batch_generation_policy", "build_image_provider_payload", "check_image_live_readiness",
                    "submit_image_generation_job", "review_generated_result", "record_image_result_feedback",
                    "evaluate_generated_result", "create_evolution_proposal", "apply_evolution_proposal",
                    "register_selected_image_asset",
                ),
            ),
        ),
        artifact_types=("image_intent", "image_brief", "provider_payload", "generated_image"),
    )
