from __future__ import annotations

from ..models import CapabilityDescriptor, WorkflowFragment, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        name="inspiration",
        actions=(
            action_descriptor(runtime("collect_external_source_snapshot"), tool="product_external_source_collect", domain="inspiration", requires_user_input=True),
            action_descriptor(runtime("create_inspiration_candidates"), tool="product_inspiration_candidates", domain="inspiration"),
            action_descriptor(runtime("create_inspiration_pack"), tool="product_inspiration_pack", domain="inspiration"),
            action_descriptor(runtime("create_llm_inspiration_pack"), tool="product_llm_inspiration_pack", domain="inspiration", requires_user_input=True),
            action_descriptor(runtime("confirm_inspiration_library_entry"), tool="product_inspiration_library_confirm", domain="inspiration", requires_user_input=True, requires_explicit_confirmation=True),
        ),
        workflows=(
            WorkflowFragment(
                "inspiration_to_generation", "2.0",
                ("collect_external_source_snapshot", "create_inspiration_candidates", "create_inspiration_pack", "create_llm_inspiration_pack", "confirm_inspiration_library_entry"),
            ),
        ),
        artifact_types=("external_source_snapshot", "inspiration_candidate", "inspiration_pack"),
    )
