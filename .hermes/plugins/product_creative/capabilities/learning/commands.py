"""Capability-owned Hermes command adapters for learning."""

from __future__ import annotations
from typing import Any, Dict
from .feedback_service import (
    record_channel_feedback,
    record_result_feedback,
)
from ...common import TOOLSET, json_text
from ...runtime.errors import classify_exception, error_result, record_runtime_error
from .result_evaluation_service import create_result_evaluation
from ..review.result_review_service import create_result_review_package
from .feedback_repository import record_feedback
from .writeback_service import evolve_product
from ..models import CommandDescriptor
from . import schemas

def _tool_ok(fn, args: Dict[str, Any]) -> str:
    try:
        return json_text(fn(args))
    except Exception as exc:
        error = classify_exception(
            exc,
            "hermes_tool_adapter",
            str(args.get("product_id") or args.get("id") or ""),
            str(args.get("action") or ""),
        )
        error["diagnostic_path"] = record_runtime_error(error)
        return json_text(error_result(error) | {"diagnostic_path": error["diagnostic_path"]})

def _handle_product_result_feedback(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: record_result_feedback(
            a.get("product_id") or a.get("id"),
            a.get("result_id") or a.get("result"),
            a.get("note") or "",
            bool(a.get("selected")),
            a.get("rating"),
            a.get("issues") or a.get("issue") or [],
            bool(a.get("allow_evolve")),
            {
                "subject_clarity": a.get("subject_clarity"),
                "product_recognizability": a.get("product_recognizability"),
                "composition": a.get("composition"),
                "style_fit": a.get("style_fit"),
                "copy_fit": a.get("copy_fit"),
                "packaging_fidelity": a.get("packaging_fidelity"),
                "text_control": a.get("text_control"),
                "motion_quality": a.get("motion_quality"),
                "scene_fit": a.get("scene_fit"),
                "first_frame_consistency": a.get("first_frame_consistency"),
                "factuality": a.get("factuality"),
            },
            a.get("like_reasons") or a.get("like_reason") or [],
            a.get("dislike_reasons") or a.get("dislike_reason") or [],
        ),
        args,
    )

def _handle_product_result_evaluate(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: create_result_evaluation(
            a.get("product_id") or a.get("id"),
            a.get("result_id") or a.get("result"),
            a.get("feedback_id") or a.get("feedback") or "",
            a.get("provider") or "",
            a.get("model") or "",
        ),
        args,
    )

def _handle_product_channel_feedback(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: record_channel_feedback(
            a.get("product_id") or a.get("id"),
            a.get("artifact_id") or a.get("artifact"),
            a.get("note") or "",
            bool(a.get("selected")),
            a.get("variant"),
            a.get("rating"),
            a.get("issues") or a.get("issue") or [],
            a.get("like_reasons") or a.get("like_reason") or [],
            a.get("dislike_reasons") or a.get("dislike_reason") or [],
            bool(a.get("allow_evolve")),
            {
                "channel_fit": a.get("channel_fit"),
                "factuality": a.get("factuality"),
                "tone_fit": a.get("tone_fit"),
                "actionability": a.get("actionability"),
            },
            {
                key: a.get(key)
                for key in ("impressions", "views", "clicks", "likes", "saves", "shares", "comments", "conversions", "spend", "revenue")
            },
        ),
        args,
    )

def _handle_product_feedback(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: record_feedback(
            a.get("product_id") or a.get("id"),
            a.get("artifact_id") or a.get("artifact"),
            a.get("note") or "",
            bool(a.get("selected")),
            a.get("variant"),
            a.get("rating"),
        ),
        args,
    )

def _handle_product_evolve(args: Dict[str, Any], **_kw: Any) -> str:
    return _tool_ok(
        lambda a: evolve_product(a.get("product_id") or a.get("id"), a.get("apply_id") or a.get("apply")),
        args,
    )

def command_descriptors() -> tuple[CommandDescriptor, ...]:
    return (
        CommandDescriptor("product_result_feedback", schemas.PRODUCT_RESULT_FEEDBACK_SCHEMA, _handle_product_result_feedback, "learning", "_handle_product_result_feedback"),
        CommandDescriptor("product_result_evaluate", schemas.PRODUCT_RESULT_EVALUATE_SCHEMA, _handle_product_result_evaluate, "learning", "_handle_product_result_evaluate"),
        CommandDescriptor("product_channel_feedback", schemas.PRODUCT_CHANNEL_FEEDBACK_SCHEMA, _handle_product_channel_feedback, "learning", "_handle_product_channel_feedback"),
        CommandDescriptor("product_feedback_record", schemas.PRODUCT_FEEDBACK_SCHEMA, _handle_product_feedback, "learning", "_handle_product_feedback"),
        CommandDescriptor("product_evolve", schemas.PRODUCT_EVOLVE_SCHEMA, _handle_product_evolve, "learning", "_handle_product_evolve"),
    )
