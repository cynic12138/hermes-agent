"""Shot-scoped repair decisions derived from immutable M14 QA reports."""

from __future__ import annotations

from collections import defaultdict

from ..common import now_iso
from ..contracts.creative_artifacts import (
    MediaExecutionPlanArtifact,
    MediaQaReportArtifact,
    MediaRepairDecisionArtifact,
    MediaShotRepair,
)
from .professional_artifacts import (
    load_professional_artifact,
    save_professional_artifact,
)


def _repair_action(category: str, check_id: str) -> tuple[str, bool]:
    if category == "subtitle":
        return "rerender_subtitle", False
    if category == "packaging":
        return "recomposite_plate", False
    if category == "technical" and check_id.startswith("shot-duration"):
        return "recompose_final", False
    return "regenerate_background", True


def plan_media_repair(
    product_id: str,
    *,
    qa_report_id: str,
    repair_round: int,
) -> MediaRepairDecisionArtifact:
    """Create a bounded repair decision without executing Provider calls."""

    report = load_professional_artifact(product_id, qa_report_id)
    if not isinstance(report, MediaQaReportArtifact):
        raise ValueError("media repair requires a Media QA Report")
    plan = load_professional_artifact(product_id, report.plan_id)
    if not isinstance(plan, MediaExecutionPlanArtifact):
        raise ValueError("media repair requires a Media Execution Plan")
    failed_by_shot: dict[str, list] = defaultdict(list)
    for check in report.checks:
        if check.status == "FAIL" and check.shot_id:
            failed_by_shot[check.shot_id].append(check)
    preserved = [
        shot.shot_id
        for shot in plan.shots
        if shot.shot_id not in failed_by_shot
    ]
    effective_round = min(max(1, repair_round), 2)
    if repair_round > 2 or report.overall_result in {"HUMAN_REVIEW", "REJECT"}:
        decision = MediaRepairDecisionArtifact(
            artifact_id=(
                f"media-repair-{plan.task_id}-{report.qa_run}-human"
            ),
            task_id=plan.task_id,
            product_id=plan.product_id,
            created_at=now_iso(),
            source_refs=[report.artifact_id, plan.artifact_id],
            status="BLOCKED",
            qa_report_id=report.artifact_id,
            decision=(
                "REJECT" if report.overall_result == "REJECT" else "HUMAN_REVIEW"
            ),
            repair_round=effective_round,
            shot_repairs=[],
            preserved_shot_ids=preserved,
            estimated_provider_calls=0,
            authorization_required=False,
            reason=(
                "Automatic repair limit reached; human review is required."
                if repair_round > 2
                else "QA result is not safe for automatic repair."
            ),
        )
        save_professional_artifact(decision)
        return decision
    if report.overall_result != "REPAIR" or not failed_by_shot:
        raise ValueError("media QA report does not request an automatic repair")

    repairs: list[MediaShotRepair] = []
    for shot in plan.shots:
        checks = failed_by_shot.get(shot.shot_id)
        if not checks:
            continue
        actions = [_repair_action(item.category, item.check_id) for item in checks]
        provider_required = any(item[1] for item in actions)
        action = (
            "regenerate_background"
            if provider_required
            else next(
                (
                    candidate
                    for candidate in (
                        "rerender_subtitle",
                        "recomposite_plate",
                        "recompose_final",
                    )
                    if any(item[0] == candidate for item in actions)
                ),
                "recompose_final",
            )
        )
        repairs.append(
            MediaShotRepair(
                shot_id=shot.shot_id,
                check_ids=[item.check_id for item in checks],
                action=action,
                reason="; ".join(
                    f"{item.check_id}={item.status}" for item in checks
                ),
                provider_call_required=provider_required,
            )
        )
    provider_calls = sum(
        1 for item in repairs if item.provider_call_required
    )
    decision = MediaRepairDecisionArtifact(
        artifact_id=(
            f"media-repair-{plan.task_id}-{report.qa_run}-round-{effective_round}"
        ),
        task_id=plan.task_id,
        product_id=plan.product_id,
        created_at=now_iso(),
        source_refs=[report.artifact_id, plan.artifact_id],
        status="NEEDS_REVISION",
        qa_report_id=report.artifact_id,
        decision=(
            "PROVIDER_REPAIR" if provider_calls else "LOCAL_REPAIR"
        ),
        repair_round=effective_round,
        shot_repairs=repairs,
        preserved_shot_ids=preserved,
        estimated_provider_calls=provider_calls,
        authorization_required=provider_calls > 0,
        reason=(
            "Repair only failed shots and preserve all previously passing shots."
        ),
    )
    save_professional_artifact(decision)
    return decision
