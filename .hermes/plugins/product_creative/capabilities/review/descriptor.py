from __future__ import annotations

from ..models import CapabilityDescriptor, WorkflowFragment, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        name="review",
        actions=(
            action_descriptor(runtime("review_generated_result"), tool="product_result_review_package", domain="review"),
            action_descriptor(runtime("evaluate_generated_result"), tool="product_result_evaluate", domain="review", modality="learning"),
            action_descriptor(runtime("create_task_overview_package"), tool="product_task_overview_package", domain="review"),
        ),
        workflows=(
            WorkflowFragment(
                "result_review_learning", "2.0",
                ("create_task_overview_package", "review_generated_result", "evaluate_generated_result", "create_evolution_proposal", "apply_evolution_proposal"),
            ),
        ),
        artifact_types=("review_package", "result_feedback", "result_evaluation", "task_overview"),
    )
