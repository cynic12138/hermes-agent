from __future__ import annotations

from ..models import CapabilityDescriptor, WorkflowFragment, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        name="product",
        actions=(
            action_descriptor(runtime("create_product"), tool="product_create", domain="product_brain", requires_user_input=True, requires_existing_product=False),
            action_descriptor(runtime("ingest_product_source"), tool="product_ingest", domain="product_brain", requires_user_input=True),
        ),
        workflows=(
            WorkflowFragment(
                "product_onboarding",
                "2.0",
                (
                    "create_product", "ingest_product_source", "register_material_asset",
                    "analyze_material_image", "align_visual_analysis", "rebuild_material_cards",
                    "prepare_task_material_pack",
                ),
            ),
        ),
        event_types=("product.created", "product.ingested", "product_brain.proposal_created", "product_brain.version_applied"),
    )
