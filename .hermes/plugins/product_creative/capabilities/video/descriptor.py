from __future__ import annotations

from ..models import CapabilityDescriptor, WorkflowFragment, action_descriptor
from .executor import runtime


def capability_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        name="video",
        actions=(
            action_descriptor(runtime("resolve_video_intent"), tool="product_video_intent", domain="video", requires_user_input=True),
            action_descriptor(runtime("create_video_brief"), tool="product_video_brief", domain="video"),
            action_descriptor(runtime("review_video_brief"), tool="product_video_brief_review_package", domain="video"),
            action_descriptor(runtime("revise_video_brief"), tool="product_video_brief_revise", domain="video", requires_user_input=True, requires_explicit_confirmation=True),
            action_descriptor(runtime("build_video_provider_payload"), tool="product_video_generate", domain="video"),
            action_descriptor(runtime("check_video_reference_readiness"), tool="product_video_reference_readiness", domain="video"),
            action_descriptor(runtime("check_video_live_readiness"), tool="product_live_readiness", domain="video"),
            action_descriptor(runtime("create_video_execution_policy"), tool="product_video_execution_policy", domain="video", requires_user_input=True, requires_explicit_confirmation=True),
            action_descriptor(runtime("submit_video_generation_task"), tool="product_generation_job", domain="video", requires_explicit_confirmation=True, side_effect="provider"),
            action_descriptor(runtime("check_video_task_status"), tool="product_video_task_status", domain="video", side_effect="provider"),
            action_descriptor(runtime("import_video_result"), tool="product_video_result_import", domain="video", requires_user_input=True),
            action_descriptor(runtime("compose_exact_main_video"), tool="product_exact_main_video", domain="video", requires_user_input=True),
        ),
        workflows=(
            WorkflowFragment(
                "video_creation_learning", "2.0",
                (
                    "resolve_video_intent", "create_video_brief", "review_video_brief", "revise_video_brief",
                    "build_video_provider_payload", "check_video_reference_readiness", "check_video_live_readiness",
                    "create_video_execution_policy", "submit_video_generation_task", "check_video_task_status",
                    "review_generated_result", "record_video_result_feedback",
                    "evaluate_generated_result", "create_evolution_proposal", "apply_evolution_proposal",
                ),
            ),
            WorkflowFragment(
                "manual_video_import_learning", "2.0",
                (
                    "import_video_result", "review_generated_result", "record_video_result_feedback",
                    "evaluate_generated_result", "create_evolution_proposal", "apply_evolution_proposal",
                ),
            ),
            WorkflowFragment(
                "exact_main_video_learning", "2.0",
                ("compose_exact_main_video", "review_generated_result", "record_video_result_feedback", "evaluate_generated_result", "create_evolution_proposal", "apply_evolution_proposal"),
            ),
            WorkflowFragment(
                "video_brief_learning", "2.0",
                ("record_video_brief_feedback", "create_evolution_proposal", "apply_evolution_proposal"),
            ),
        ),
        artifact_types=("video_intent", "video_brief", "provider_task", "generated_video"),
    )
