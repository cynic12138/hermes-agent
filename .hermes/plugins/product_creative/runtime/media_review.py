"""Confirmed human decisions for immutable M14 media QA reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common import ensure_product, now_iso, write_json
from ..contracts.creative_artifacts import (
    MediaHumanOverrideArtifact,
    MediaQaReportArtifact,
)
from ..ports.runtime_repositories import receipts, recovery
from .professional_artifacts import (
    load_professional_artifact,
    save_professional_artifact,
)


def record_media_qa_decision(
    product_id: str,
    *,
    qa_report_id: str,
    decision: str,
    reason: str,
    actor: str,
    confirmation_id: str,
    trace_id: str = "",
) -> dict[str, Any]:
    """Persist a confirmed decision without mutating the original QA report."""

    if decision not in {"approve", "reject", "accept_with_warning"}:
        raise ValueError("media QA decision must be approve, reject, or accept_with_warning")
    if not reason.strip():
        raise ValueError("media QA decision requires a human reason")
    if not confirmation_id.strip():
        raise ValueError("media QA decision requires a confirmation id")
    report = load_professional_artifact(product_id, qa_report_id)
    if not isinstance(report, MediaQaReportArtifact):
        raise ValueError("media QA decision requires a Media QA Report")

    repository = receipts(product_id)
    values = {
        "qa_report_id": qa_report_id,
        "decision": decision,
        "confirmation_id": confirmation_id,
    }
    receipt_key = repository.key("product_media_qa_decide", values)
    claim = repository.claim(
        "product_media_qa_decide",
        receipt_key,
        values,
    )
    if not claim["claimed"] and claim["status"] == "completed":
        return {
            **dict(claim.get("result") or {}),
            "idempotent_replay": True,
            "action_receipt": claim["receipt_path"],
        }
    pending_receipt_path = repository.begin(
        "product_media_qa_decide",
        receipt_key,
        values,
    )
    override = MediaHumanOverrideArtifact(
        artifact_id=(
            f"media-override-{report.task_id}-{report.qa_run}-{decision}"
        ),
        task_id=report.task_id,
        product_id=report.product_id,
        created_at=now_iso(),
        source_refs=[report.artifact_id],
        status="BLOCKED" if decision == "reject" else "PASS",
        qa_report_id=report.artifact_id,
        decision=decision,
        reason=reason.strip(),
        actor=actor.strip() or "user",
        confirmation_id=confirmation_id,
        receipt_id=pending_receipt_path,
    )
    save_professional_artifact(override)
    payload = {
        "success": True,
        "product_id": report.product_id,
        "qa_report_id": report.artifact_id,
        "override": override.model_dump(mode="json"),
    }
    receipt_path = repository.save(
        "product_media_qa_decide",
        receipt_key,
        {
            "idempotency_values": values,
            "created_at": now_iso(),
            "result": payload,
        },
    )
    store = recovery()
    store.record_confirmation(
        confirmation_id,
        decision=decision,
        actor=actor.strip() or "user",
        reason=reason.strip(),
        expected_version=None,
        result=payload,
    )
    store.audit(
        report.product_id,
        "product_media_qa_decide",
        report.artifact_id,
        decision,
        actor.strip() or "user",
        reason.strip(),
        payload,
        trace_id,
    )

    task_path = (
        ensure_product(report.product_id)
        / "artifacts"
        / "creative_tasks"
        / f"{report.task_id}.json"
    )
    if task_path.is_file():
        from ..capabilities.learning.feedback_service import (
            record_result_feedback,
        )
        from ..capabilities.learning.result_evaluation_service import (
            create_result_evaluation,
        )
        from .creative_tasks import load_creative_task

        task = load_creative_task(report.product_id, report.task_id)
        task.professional_artifacts[
            "media_human_override"
        ] = override.artifact_id
        recorded = task.professional_artifacts.setdefault(
            "media_human_overrides",
            [],
        )
        if override.artifact_id not in recorded:
            recorded.append(override.artifact_id)
        task.result_descriptors.append(
            {
                "type": "media_qa_human_decision",
                "qa_report_id": report.artifact_id,
                "override_id": override.artifact_id,
                "decision": decision,
                "reason": reason.strip(),
                "action_receipt": receipt_path,
                "created_at": now_iso(),
            }
        )
        media_result = next(
            (
                item
                for item in reversed(task.result_descriptors)
                if item.get("type") == "media_result"
                and item.get("result_id")
            ),
            {},
        )
        result_id = str(media_result.get("result_id") or "")
        if result_id:
            feedback = record_result_feedback(
                report.product_id,
                result_id,
                reason.strip(),
                selected=decision != "reject",
                rating=1 if decision == "reject" else 4,
                issues=(
                    [
                        f"Media QA {report.overall_result}: "
                        + "; ".join(report.hard_blockers)
                    ]
                    if decision == "reject"
                    else []
                ),
                like_reasons=(
                    [reason.strip()]
                    if decision in {"approve", "accept_with_warning"}
                    else []
                ),
                dislike_reasons=(
                    [reason.strip()] if decision == "reject" else []
                ),
                allow_evolve=False,
            )
            evaluation = create_result_evaluation(
                report.product_id,
                result_id,
                feedback=str(feedback.get("feedback_id") or ""),
            )
            task.result_descriptors.append(
                {
                    "type": "media_qa_learning_evidence",
                    "feedback_id": feedback.get("feedback_id", ""),
                    "evaluation_id": evaluation.get(
                        "result_evaluation_id",
                        "",
                    ),
                    "rule_candidate_ids": evaluation.get(
                        "rule_candidate_ids",
                        [],
                    ),
                    "product_brain_writeback": False,
                    "created_at": now_iso(),
                }
            )
        if decision == "reject":
            task.status = "FAILED_FINAL"
            task.current_stage = "QUALITY_REVIEW"
            task.blocked_reason = reason.strip()
        else:
            task.status = "AWAITING_FEEDBACK"
            task.current_stage = "AWAITING_FEEDBACK"
            task.blocked_reason = ""
        task.updated_at = now_iso()
        write_json(task_path, task.model_dump(mode="json"))
    return {**payload, "action_receipt": receipt_path}
