from __future__ import annotations

from ..models import CapabilityDescriptor, WorkflowFragment, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        name="material",
        actions=(
            action_descriptor(runtime("register_material_asset"), tool="product_asset_register", domain="material", requires_user_input=True),
            action_descriptor(runtime("analyze_material_image"), tool="product_image_analyze", domain="material", side_effect="provider"),
            action_descriptor(runtime("align_visual_analysis"), tool="product_visual_align", domain="material"),
            action_descriptor(runtime("rebuild_material_cards"), tool="product_material_card_rebuild", domain="material"),
            action_descriptor(runtime("prepare_task_material_pack"), tool="product_task_material_pack", domain="material", requires_user_input=True),
            action_descriptor(runtime("register_selected_image_asset"), tool="product_selected_image_asset", domain="material", requires_user_input=True),
            action_descriptor(runtime("resolve_material_execution_input"), tool="product_material_resolve", domain="material", requires_user_input=True),
            action_descriptor(runtime("record_material_feedback"), tool="product_material_feedback", domain="material", requires_user_input=True),
        ),
        workflows=(
            WorkflowFragment(
                "material_preference_learning", "2.0",
                ("resolve_material_execution_input", "record_material_feedback", "create_evolution_proposal", "apply_evolution_proposal"),
            ),
        ),
        artifact_types=("material_asset", "material_card", "task_material_pack", "material_feedback"),
    )
