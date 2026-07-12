"""Workflow state snapshot service for Product Creative runtime."""

from __future__ import annotations

from typing import Any, Dict, List

from ..common import product_dir
from ..contracts.models import WorkflowStatus
from ..ports.runtime_repositories import product_brains, rules, workflows
from .evidence import (
    is_newer,
    latest_json,
    latest_json_matching,
    proposal_pair,
    source_count,
)


WORKFLOW_STATUS_SCHEMA_VERSION = "product_creative.workflow_status.v4.9"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _compact_item(item: Dict[str, Any], extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not item:
        return {}
    payload = item.get("payload") or {}
    compact = {
        "id": item.get("id", ""),
        "path": item.get("path", ""),
        "created_at": item.get("created_at", ""),
        "status": item.get("status", ""),
    }
    if extra:
        compact.update(extra)
    if payload.get("target"):
        compact["target"] = payload.get("target")
    return compact


def _feedback_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "selected": bool(payload.get("selected")),
        "eligible_for_evolution_proposal": bool(payload.get("eligible_for_evolution_proposal")),
        "source_artifact_id": _text(payload.get("source_artifact_id")),
        "source_result_id": _text(payload.get("source_result_id")),
        "brief_type": _text(payload.get("brief_type")),
        "variant": payload.get("variant"),
    }


def _run_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    channel_content = artifacts.get("channel_content") if isinstance(artifacts.get("channel_content"), dict) else {}
    channel_evaluation = artifacts.get("channel_evaluation") if isinstance(artifacts.get("channel_evaluation"), dict) else {}
    review_package = artifacts.get("channel_review_package") if isinstance(artifacts.get("channel_review_package"), dict) else {}
    return {
        "target": _text(payload.get("target")),
        "best_variant": summary.get("best_variant"),
        "review_package_id": _text(summary.get("review_package_id")),
        "channel_content_id": _text(channel_content.get("id")),
        "channel_content_path": _text(channel_content.get("path")),
        "channel_evaluation_id": _text(channel_evaluation.get("id")),
        "channel_review_package_id": _text(review_package.get("id")),
        "next_feedback_command": _text(
            (((payload.get("next_actions") or {}).get("record_selected_feedback") or {}).get("command"))
        ),
    }


def _provider_payload_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    request = payload.get("request") if isinstance(payload.get("request"), dict) else {}
    draft = request.get("provider_request_draft") if isinstance(request.get("provider_request_draft"), dict) else {}
    return {
        "provider": _text(payload.get("provider")),
        "brief_type": _text(payload.get("brief_type")),
        "source_brief_id": _text(payload.get("source_brief_id")),
        "body_ready_for_live": bool(draft.get("body_ready_for_live")) if draft else False,
        "unresolved_reference_count": len(_list(draft.get("unresolved_reference_assets"))) if draft else 0,
    }


def _video_reference_readiness_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "payload_id": _text(payload.get("payload_id")),
        "ready_for_provider": bool(payload.get("ready_for_provider")),
        "body_ready_for_live": bool(payload.get("body_ready_for_live")),
        "blocker_count": len(_list(payload.get("blockers"))),
    }


def _live_readiness_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "provider": _text(payload.get("provider")),
        "kind": _text(payload.get("kind")),
        "payload_id": _text(payload.get("payload_id")),
        "ready_for_live": bool(payload.get("ready_for_live")),
        "blocker_count": len(_list(payload.get("blockers"))),
    }


def _video_execution_policy_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "payload_id": _text(payload.get("payload_id")),
        "provider": _text(payload.get("provider")),
        "mode": _text(payload.get("mode")),
        "confirmed": bool(payload.get("confirmed")),
        "external_call_allowed": bool(payload.get("external_call_allowed")),
    }


def _video_task_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    return {
        "remote_task_id": _text(payload.get("remote_task_id")),
        "provider": _text(payload.get("provider")),
        "source_payload_id": _text(payload.get("source_payload_id")),
        "execution_policy_id": _text(payload.get("execution_policy_id")),
        "result_available": bool(result.get("available")),
        "result_id": _text(result.get("result_id")),
        "result_url": _text(result.get("result_url")),
    }


def _video_task_status_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "video_task_id": _text(payload.get("video_task_id")),
        "remote_task_id": _text(payload.get("remote_task_id")),
        "provider": _text(payload.get("provider")),
        "normalized_status": _text(payload.get("normalized_status")),
        "result_id": _text(payload.get("result_id")),
        "result_url": _text(payload.get("result_url")),
    }


def _video_result_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    outputs = [entry for entry in _list(payload.get("outputs")) if isinstance(entry, dict)]
    first = outputs[0] if outputs else {}
    return {
        "video_task_id": _text(payload.get("video_task_id")),
        "remote_task_id": _text(payload.get("remote_task_id")),
        "provider": _text(payload.get("provider")),
        "remote_url": _text(payload.get("remote_url")),
        "local_video_path": _text(first.get("path")),
        "ready_for_feedback": bool((payload.get("review") or {}).get("ready_for_feedback")),
    }


def _image_intent_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    material_context = payload.get("material_context") if isinstance(payload.get("material_context"), dict) else {}
    return {
        "target": _text(payload.get("target")),
        "channel": _text(payload.get("channel")),
        "preset": _text(payload.get("preset")),
        "count_limit": payload.get("count_limit"),
        "provider": _text(payload.get("provider")),
        "task_material_pack_id": _text(material_context.get("task_material_pack_id")),
    }


def _image_brief_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    target = payload.get("target") if isinstance(payload.get("target"), dict) else {}
    return {
        "source_image_intent_id": _text(payload.get("source_image_intent_id")),
        "source_brief_id": _text(payload.get("source_brief_id")),
        "channel": _text(target.get("channel")),
        "preset": _text(target.get("preset")),
        "status": _text(payload.get("status")),
    }


def _image_brief_review_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "source_brief_id": _text(payload.get("source_brief_id")),
        "patch_id": _text(payload.get("patch_id")),
    }


def _batch_policy_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "source_image_intent_id": _text(payload.get("source_image_intent_id")),
        "source_brief_id": _text(payload.get("source_brief_id")),
        "provider": _text(payload.get("provider")),
        "mode": _text(payload.get("mode")),
        "count_limit": payload.get("count_limit"),
        "confirmed": bool(payload.get("confirmed")),
    }


def _image_run_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    comparison = payload.get("comparison_package") if isinstance(payload.get("comparison_package"), dict) else {}
    jobs = _list(payload.get("jobs"))
    first_result = ""
    if jobs and isinstance(jobs[0], dict):
        first_result = _text(jobs[0].get("result_id"))
    return {
        "provider": _text(payload.get("provider")),
        "mode": _text(payload.get("mode")),
        "count": payload.get("count"),
        "first_result_id": first_result,
        "comparison_package_id": _text(comparison.get("id")),
        "external_call_count": payload.get("external_call_count"),
    }


def _review_package_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "review_type": _text(payload.get("review_type")),
        "source_brief_id": _text(payload.get("source_brief_id")),
        "external_call_performed": bool(payload.get("external_call_performed")),
    }


def _proposal_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "risk_level": _text(payload.get("risk_level")),
        "target_state_paths": _list(payload.get("target_state_paths")),
        "requires_human_review": bool(payload.get("requires_human_review")),
        "applied_at": _text(payload.get("applied_at")),
    }


def _material_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "role": _text(payload.get("role")),
        "stored_path": _text(payload.get("stored_path")),
        "remote_url": _text(payload.get("remote_url")),
        "status": _text(payload.get("status")),
    }


def _image_analysis_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "material_id": _text(payload.get("material_id")),
        "provider": _text(payload.get("provider")),
        "external_call_performed": bool(payload.get("external_call_performed")),
        "confidence": _text(payload.get("confidence")),
    }


def _visual_alignment_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "material_id": _text(payload.get("material_id")),
        "source_analysis_id": _text(payload.get("source_analysis_id")),
        "eligible_for_evolution_proposal": bool(payload.get("eligible_for_evolution_proposal")),
    }


def _material_card_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
    return {
        "material_id": _text(payload.get("material_id")),
        "role": _text(payload.get("role")),
        "has_image_analysis": bool(readiness.get("has_image_analysis")),
        "has_visual_alignment": bool(readiness.get("has_visual_alignment")),
        "blocked_as_primary_reference": bool(readiness.get("blocked_as_primary_reference")),
    }


def _task_material_pack_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "task": _text(payload.get("task")),
        "channel": _text(payload.get("channel")),
        "selected_count": len(_list(payload.get("selected_materials"))),
        "missing_requirements": _list(payload.get("missing_requirements")),
    }


def _material_usage_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "task": _text(payload.get("task")),
        "channel": _text(payload.get("channel")),
        "artifact_id": _text(payload.get("artifact_id")),
        "task_material_pack_id": _text(payload.get("task_material_pack_id")),
        "used_material_ids": _list(payload.get("used_material_ids")),
    }


def _material_feedback_extra(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = item.get("payload") or {}
    return {
        "material_id": _text(payload.get("material_id")),
        "task": _text(payload.get("task")),
        "channel": _text(payload.get("channel")),
        "selected": bool(payload.get("selected")),
        "rejected": bool(payload.get("rejected")),
        "eligible_for_evolution_proposal": bool(payload.get("eligible_for_evolution_proposal")),
    }


def _derive_status(
    source_count_value: int,
    latest_run: Dict[str, Any],
    latest_feedback: Dict[str, Any],
    latest_proposed: Dict[str, Any],
    latest_applied: Dict[str, Any],
) -> str:
    if is_newer(latest_proposed, latest_feedback) and is_newer(latest_proposed, latest_run):
        return "proposal_ready_for_confirmation"
    if latest_feedback and is_newer(latest_feedback, latest_proposed) and is_newer(latest_feedback, latest_applied):
        return "feedback_recorded"
    if latest_run and is_newer(latest_run, latest_feedback) and is_newer(latest_run, latest_proposed):
        return "channel_run_ready_for_review"
    if latest_applied and is_newer(latest_applied, latest_run) and is_newer(latest_applied, latest_feedback):
        return "brain_updated"
    if source_count_value > 0:
        return "ready_for_channel_run"
    return "product_initialized"


def safety_contract() -> Dict[str, Any]:
    return {
        "status_next_summary_mutate_product_brain": False,
        "feedback_mutates_product_brain": False,
        "proposal_creation_mutates_product_brain": False,
        "proposal_apply_mutates_product_brain": True,
        "proposal_apply_requires_explicit_user_confirmation": True,
    }


def _runtime_projection(base) -> Dict[str, Any]:
    repository = workflows()
    instances = repository.list(base.name)
    active_statuses = {WorkflowStatus.CREATED, WorkflowStatus.RUNNING, WorkflowStatus.PAUSED}
    active = [item for item in instances if item.status in active_statuses]
    latest = instances[-1] if instances else None
    rule_counts: Dict[str, int] = {}
    rule_scope_counts: Dict[str, int] = {}
    for rule in rules().list(base.name):
        status = _text(rule.get("status")) or "unknown"
        scope = _text(rule.get("scope")) or "unknown"
        rule_counts[status] = rule_counts.get(status, 0) + 1
        rule_scope_counts[scope] = rule_scope_counts.get(scope, 0) + 1
    return {
        "workflow_instance_count": len(instances),
        "active_workflow_count": len(active),
        "latest_workflow": {
            "workflow_id": latest.workflow_id,
            "definition": latest.definition,
            "trace_id": latest.trace_id,
            "status": latest.status.value,
            "current_action": (
                latest.steps[latest.current_step].action
                if latest.current_step < len(latest.steps)
                else ""
            ),
            "pause_reason": latest.pause_reason,
            "updated_at": latest.updated_at,
        } if latest else {},
        "rule_candidates": {
            "count": sum(rule_counts.values()),
            "by_status": rule_counts,
            "by_scope": rule_scope_counts,
        },
    }


def workflow_status(product_id: str) -> Dict[str, Any]:
    base = product_dir(product_id)
    if not base.exists():
        return {
            "success": True,
            "schema_version": WORKFLOW_STATUS_SCHEMA_VERSION,
            "product_id": base.name,
            "exists": False,
            "status": "no_product",
            "evidence": {},
            "safety": safety_contract(),
        }

    current_brain = product_brains().current(base.name)
    state = current_brain.get("state") if isinstance(current_brain.get("state"), dict) else {}
    latest_run = latest_json(base, "artifacts/channel_review_runs", "channel_review_run_id")
    latest_material_asset = latest_json(base, "artifacts/material_assets", "material_id")
    latest_image_analysis = latest_json(base, "artifacts/image_analysis", "analysis_id")
    latest_visual_alignment = latest_json(base, "artifacts/visual_alignments", "alignment_id")
    latest_material_card = latest_json(base, "artifacts/material_cards", "material_card_id")
    latest_task_material_pack = latest_json(base, "artifacts/task_material_packs", "task_material_pack_id")
    latest_material_usage = latest_json(base, "artifacts/material_usage", "usage_id")
    latest_material_feedback = latest_json(base, "artifacts/material_feedback", "feedback_id")
    latest_material_execution_input = latest_json(base, "artifacts/material_execution_inputs", "execution_input_id")
    latest_external_source_snapshot = latest_json(base, "artifacts/external_source_snapshots", "snapshot_id")
    latest_inspiration_candidate = latest_json(base, "artifacts/inspiration_candidates", "candidate_id")
    latest_inspiration_pack = latest_json(base, "artifacts/inspiration_packs", "pack_id")
    latest_llm_inspiration_pack = latest_json(base, "artifacts/llm_inspiration_packs", "pack_id")
    latest_inspiration_library_entry = latest_json(base, "artifacts/inspiration_library", "entry_id")
    latest_image_intent = latest_json(base, "artifacts/image_intents", "intent_id")
    latest_image_brief = latest_json(base, "artifacts/image_briefs", "brief_id")
    latest_image_brief_review = latest_json(base, "artifacts/image_brief_reviews", "review_id")
    latest_image_brief_patch = latest_json(base, "artifacts/image_brief_patches", "patch_id")
    latest_batch_policy = latest_json(base, "artifacts/batch_generation_policies", "policy_id")
    latest_image_payload = latest_json_matching(
        base,
        "artifacts/provider_payloads",
        lambda payload: payload.get("brief_type") == "image",
        "payload_id",
    )
    latest_image_run = latest_json(base, "artifacts/image_generation_runs", "image_run_id")
    latest_image_result = latest_json(base, "artifacts/generated_images", "result_id")
    latest_video_intent = latest_json(base, "artifacts/video_intents", "intent_id")
    latest_video_brief = latest_json(base, "artifacts/video_scripts", "brief_id")
    latest_video_brief_patch = latest_json(base, "artifacts/video_brief_patches", "patch_id")
    latest_video_payload = latest_json_matching(
        base,
        "artifacts/provider_payloads",
        lambda payload: payload.get("brief_type") == "video",
        "payload_id",
    )
    latest_video_reference_readiness = latest_json(
        base,
        "artifacts/video_reference_readiness",
        "reference_readiness_id",
        "readiness_id",
    )
    latest_video_live_readiness = latest_json_matching(
        base,
        "artifacts/live_readiness",
        lambda payload: payload.get("kind") == "video",
        "readiness_id",
    )
    latest_video_execution_policy = latest_json(base, "artifacts/video_execution_policies", "policy_id")
    latest_video_task = latest_json(base, "artifacts/video_tasks", "video_task_id")
    latest_video_task_status = latest_json(base, "artifacts/video_task_status", "video_task_status_id", "status_id")
    latest_video_result = latest_json(base, "artifacts/generated_videos", "result_id")
    latest_review_package = latest_json(base, "artifacts/review_packages", "review_package_id")
    latest_package = latest_json(base, "artifacts/channel_review_packages", "channel_review_package_id")
    latest_channel_feedback = latest_json(base, "artifacts/channel_feedback", "feedback_id")
    latest_result_feedback = latest_json(base, "artifacts/result_feedback", "feedback_id")
    latest_video_brief_feedback = latest_json(base, "artifacts/video_brief_feedback", "feedback_id")
    latest_feedback = latest_channel_feedback
    if is_newer(latest_result_feedback, latest_channel_feedback):
        latest_feedback = latest_result_feedback
    if is_newer(latest_video_brief_feedback, latest_feedback):
        latest_feedback = latest_video_brief_feedback
    if is_newer(latest_material_feedback, latest_feedback):
        latest_feedback = latest_material_feedback
    proposals = proposal_pair(base)
    count = source_count(base)
    status = _derive_status(
        count,
        latest_run,
        latest_feedback,
        proposals["latest_proposed"],
        proposals["latest_applied"],
    )
    return {
        "success": True,
        "schema_version": WORKFLOW_STATUS_SCHEMA_VERSION,
        "product_id": base.name,
        "exists": True,
        "status": status,
        "runtime": _runtime_projection(base),
        "product_state": {
            "status": _text(state.get("status")),
            "name": _text(state.get("name")),
            "updated_at": _text(state.get("updated_at")),
            "selling_point_count": len(_list(state.get("selling_points"))),
            "channel_preference_count": len(_list((state.get("learning") or {}).get("channel_preferences"))),
            "video_script_preference_count": len(_list((state.get("learning") or {}).get("video_script_preferences"))),
        },
        "evidence": {
            "source_count": count,
            "latest_channel_review_run": _compact_item(latest_run, _run_extra(latest_run)),
            "latest_material_asset": _compact_item(latest_material_asset, _material_extra(latest_material_asset)),
            "latest_image_analysis": _compact_item(latest_image_analysis, _image_analysis_extra(latest_image_analysis)),
            "latest_visual_alignment": _compact_item(latest_visual_alignment, _visual_alignment_extra(latest_visual_alignment)),
            "latest_material_card": _compact_item(latest_material_card, _material_card_extra(latest_material_card)),
            "latest_task_material_pack": _compact_item(latest_task_material_pack, _task_material_pack_extra(latest_task_material_pack)),
            "latest_material_usage": _compact_item(latest_material_usage, _material_usage_extra(latest_material_usage)),
            "latest_material_feedback": _compact_item(latest_material_feedback, _material_feedback_extra(latest_material_feedback)),
            "latest_material_execution_input": _compact_item(latest_material_execution_input),
            "latest_external_source_snapshot": _compact_item(latest_external_source_snapshot),
            "latest_inspiration_candidate": _compact_item(latest_inspiration_candidate),
            "latest_inspiration_pack": _compact_item(latest_inspiration_pack),
            "latest_llm_inspiration_pack": _compact_item(latest_llm_inspiration_pack),
            "latest_inspiration_library_entry": _compact_item(latest_inspiration_library_entry),
            "latest_image_intent": _compact_item(latest_image_intent, _image_intent_extra(latest_image_intent)),
            "latest_image_brief": _compact_item(latest_image_brief, _image_brief_extra(latest_image_brief)),
            "latest_image_brief_review": _compact_item(latest_image_brief_review, _image_brief_review_extra(latest_image_brief_review)),
            "latest_image_brief_patch": _compact_item(latest_image_brief_patch),
            "latest_batch_generation_policy": _compact_item(latest_batch_policy, _batch_policy_extra(latest_batch_policy)),
            "latest_image_provider_payload": _compact_item(latest_image_payload, _provider_payload_extra(latest_image_payload)),
            "latest_image_generation_run": _compact_item(latest_image_run, _image_run_extra(latest_image_run)),
            "latest_image_result": _compact_item(latest_image_result),
            "latest_video_intent": _compact_item(latest_video_intent),
            "latest_video_brief": _compact_item(latest_video_brief),
            "latest_video_brief_patch": _compact_item(latest_video_brief_patch),
            "latest_video_provider_payload": _compact_item(latest_video_payload, _provider_payload_extra(latest_video_payload)),
            "latest_video_reference_readiness": _compact_item(
                latest_video_reference_readiness,
                _video_reference_readiness_extra(latest_video_reference_readiness),
            ),
            "latest_video_live_readiness": _compact_item(latest_video_live_readiness, _live_readiness_extra(latest_video_live_readiness)),
            "latest_video_execution_policy": _compact_item(latest_video_execution_policy, _video_execution_policy_extra(latest_video_execution_policy)),
            "latest_video_task": _compact_item(latest_video_task, _video_task_extra(latest_video_task)),
            "latest_video_task_status": _compact_item(latest_video_task_status, _video_task_status_extra(latest_video_task_status)),
            "latest_video_result": _compact_item(latest_video_result, _video_result_extra(latest_video_result)),
            "latest_review_package": _compact_item(latest_review_package, _review_package_extra(latest_review_package)),
            "latest_channel_review_package": _compact_item(latest_package),
            "latest_feedback": _compact_item(latest_feedback, _feedback_extra(latest_feedback)),
            "latest_video_brief_feedback": _compact_item(latest_video_brief_feedback, _feedback_extra(latest_video_brief_feedback)),
            "latest_proposed_proposal": _compact_item(proposals["latest_proposed"], _proposal_extra(proposals["latest_proposed"])),
            "latest_applied_proposal": _compact_item(proposals["latest_applied"], _proposal_extra(proposals["latest_applied"])),
        },
        "safety": safety_contract(),
    }
