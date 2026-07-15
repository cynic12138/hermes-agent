"""Feedback, rule proposal, and Product Brain writeback actions."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from .api import evolve_product, record_channel_feedback, record_result_feedback, record_video_brief_feedback
from ..execution_helpers import items, quality_scores, text
from ..models import ActionRuntimeDefinition


_IMAGE_FIELDS = ("subject_clarity", "product_recognizability", "composition", "style_fit", "copy_fit", "packaging_fidelity", "text_control", "factuality")
_VIDEO_FIELDS = ("subject_clarity", "product_recognizability", "composition", "style_fit", "copy_fit", "motion_quality", "scene_fit", "first_frame_consistency", "factuality")
_BRIEF_FIELDS = ("hook_strength", "storyboard_clarity", "product_grounding", "prompt_specificity", "channel_fit", "factuality")
_CHANNEL_FIELDS = ("channel_fit", "factuality", "tone_fit", "actionability")


def _result_feedback(args: Dict[str, Any], fields: tuple[str, ...]) -> Dict[str, Any]:
    return record_result_feedback(
        text(args.get("product_id")), text(args.get("result_id")), text(args.get("note")),
        bool(args.get("selected")), args.get("rating"), items(args.get("issues")),
        bool(args.get("allow_evolve")), quality_scores(args, fields),
        items(args.get("like_reasons")), items(args.get("dislike_reasons")),
    )


def _video_brief_feedback(args: Dict[str, Any]) -> Dict[str, Any]:
    return record_video_brief_feedback(
        text(args.get("product_id")), text(args.get("brief_id")), text(args.get("note")),
        bool(args.get("selected")), args.get("rating"), items(args.get("issues")),
        items(args.get("like_reasons")), items(args.get("dislike_reasons")),
        bool(args.get("allow_evolve")), quality_scores(args, _BRIEF_FIELDS),
    )


def _channel_feedback(args: Dict[str, Any]) -> Dict[str, Any]:
    return record_channel_feedback(
        text(args.get("product_id")), text(args.get("artifact_id")), text(args.get("note")),
        bool(args.get("selected")), args.get("variant"), args.get("rating"),
        items(args.get("issues")), items(args.get("like_reasons")), items(args.get("dislike_reasons")),
        bool(args.get("allow_evolve")), quality_scores(args, _CHANNEL_FIELDS),
    )


def _apply_plan(context: Dict[str, Any]) -> Dict[str, Any]:
    status = context.get("status") if isinstance(context.get("status"), dict) else {}
    evidence = status.get("evidence") if isinstance(status.get("evidence"), dict) else {}
    proposed = evidence.get("latest_proposed_proposal") if isinstance(evidence.get("latest_proposed_proposal"), dict) else {}
    applied = evidence.get("latest_applied_proposal") if isinstance(evidence.get("latest_applied_proposal"), dict) else {}
    proposal_id = text(context.get("proposal_id")) or text(proposed.get("id")) or text(applied.get("id")) or "<proposal-id>"
    return {"product_id": text(context.get("product_id")), "apply_id": proposal_id}


def _apply_guard(context: Dict[str, Any]) -> Dict[str, Any]:
    status = context.get("status") if isinstance(context.get("status"), dict) else {}
    evidence = status.get("evidence") if isinstance(status.get("evidence"), dict) else {}
    proposal_id = text(context.get("proposal_id"))
    proposed = evidence.get("latest_proposed_proposal") if isinstance(evidence.get("latest_proposed_proposal"), dict) else {}
    applied = evidence.get("latest_applied_proposal") if isinstance(evidence.get("latest_applied_proposal"), dict) else {}
    proposed_id, applied_id = text(proposed.get("id")), text(applied.get("id"))
    if context.get("confirmed") and proposal_id and proposal_id == applied_id:
        return {"allowed": True, "proposal_id": proposal_id, "reason": "Confirmed idempotent replay is allowed."}
    if text(status.get("status")) != "proposal_ready_for_confirmation" or not proposed_id:
        return {"allowed": False, "reason": "No proposed evolution proposal is waiting for confirmation."}
    if proposal_id and proposal_id != proposed_id:
        return {"allowed": False, "reason": f"Proposal '{proposal_id}' is not the latest proposal '{proposed_id}'."}
    if not context.get("confirmed"):
        return {"allowed": False, "reason": "Product Brain writeback requires explicit confirmation."}
    return {"allowed": True, "proposal_id": proposal_id or proposed_id, "reason": "Explicit confirmation was provided."}


def action_definitions() -> Iterable[ActionRuntimeDefinition]:
    return (
        ActionRuntimeDefinition("record_image_result_feedback", lambda args: _result_feedback(args, _IMAGE_FIELDS)),
        ActionRuntimeDefinition("record_video_result_feedback", lambda args: _result_feedback(args, _VIDEO_FIELDS)),
        ActionRuntimeDefinition("record_video_brief_feedback", _video_brief_feedback),
        ActionRuntimeDefinition("record_channel_feedback", _channel_feedback),
        ActionRuntimeDefinition(
            "create_evolution_proposal",
            lambda args: evolve_product(
                text(args.get("product_id")),
                source_feedback_id=text(args.get("source_feedback_id")),
            ),
            auto_advance=True,
        ),
        ActionRuntimeDefinition(
            "apply_evolution_proposal",
            lambda args: evolve_product(text(args.get("product_id")), text(args.get("apply_id"))),
            idempotency_fields=("apply_id",), plan_policy=_apply_plan, guard_policy=_apply_guard,
            missing_input_policy=lambda context: () if context.get("confirmed") else ("explicit_confirmation",),
        ),
    )


def runtime(action: str) -> ActionRuntimeDefinition:
    return {item.name: item for item in action_definitions()}[action]
