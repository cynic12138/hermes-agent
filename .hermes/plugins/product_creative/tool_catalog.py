"""Compatibility projection of capability-owned Hermes command descriptors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .capabilities.registry import command_descriptors


@dataclass(frozen=True)
class ProductToolSpec:
    name: str
    schema: Dict[str, Any]
    handler_name: str


_PUBLIC_TOOL_ORDER = (
    "product_create", "product_ingest", "product_context_pack", "product_workspace_resolve",
    "product_workflow_status", "product_workflow_next", "product_workflow_summary", "product_action_guard",
    "product_workflow_plan", "product_conversation_adapter", "product_workflow_execute", "product_workflow_run",
    "product_asset_register", "product_asset_bind_url", "product_asset_list", "product_provider_capability_matrix",
    "product_material_resolve", "product_external_source_collect", "product_inspiration_candidates", "product_inspiration_pack",
    "product_llm_inspiration_pack", "product_inspiration_library_confirm", "product_material_manifest", "product_material_compat",
    "product_material_card_rebuild", "product_material_library_map", "product_task_material_pack", "product_material_usage",
    "product_material_feedback", "product_image_analyze", "product_visual_align", "product_video_intent",
    "product_video_brief", "product_target_list", "product_generate", "product_evaluate",
    "product_channel_evaluate", "product_channel_review_package", "product_channel_review_run", "product_brief",
    "product_image_generate", "product_image_intent", "product_image_brief", "product_image_brief_review_package",
    "product_image_brief_revise", "product_batch_generation_policy", "product_image_provider_payload", "product_image_generation_run",
    "product_selected_image_asset", "product_video_generate", "product_video_reference_readiness", "product_video_execution_policy",
    "product_provider_list", "product_provider_validate", "product_generation_job", "product_video_task_status",
    "product_video_result_import", "product_artifact_manifest", "product_review_package", "product_video_brief_review_package",
    "product_video_brief_revise", "product_result_feedback", "product_result_review_package", "product_result_evaluate",
    "product_task_overview_package", "product_exact_main_video", "product_channel_feedback", "product_video_brief_feedback",
    "product_live_readiness", "product_wiki_upgrade", "product_wiki_lint", "product_state_export",
    "product_fingerprint", "product_creative_run", "product_image_qa", "product_comparison_package",
    "product_feedback_record", "product_evolve",
)
_ORDER = {name: position for position, name in enumerate(_PUBLIC_TOOL_ORDER)}
PRODUCT_TOOL_SPECS: List[ProductToolSpec] = sorted(
    (
        ProductToolSpec(item.name, item.schema, item.compatibility_handler_name)
        for item in command_descriptors().values()
    ),
    key=lambda item: _ORDER.get(item.name, len(_ORDER)),
)
