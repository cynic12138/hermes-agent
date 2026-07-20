"""Recoverable orchestration for shot-scoped reliable media production."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Literal

from ..common import ensure_product, now_iso, write_json
from ..contracts.creative_artifacts import (
    MediaCompositeManifestArtifact,
    MediaExecutionPlanArtifact,
    MediaRepairDecisionArtifact,
    MediaShotResultArtifact,
    ProductPlateArtifact,
    ProductionBibleArtifact,
)
from ..contracts.models import TaskAuthorizationRecord
from ..ports.runtime_repositories import artifacts
from ..provider_gateway import generation_provider_gateway
from .authorization import (
    authorization_allows,
    consume_task_authorization,
)
from .media_compositor import compose_final_video, render_shot
from .media_dependencies import inspect_media_dependencies
from .media_plan import compile_media_execution_plan
from .media_qa import configured_media_qa_adapters, run_media_qa
from .media_repair import plan_media_repair
from .media_text_qa import OcrAdapter
from .product_plate import ensure_product_plate
from .professional_artifacts import (
    load_professional_artifact,
    save_professional_artifact,
)
from .story_continuity_qa import VisualAdapter


MediaMode = Literal["fixture", "mock", "live"]


def _resolve_media_qa_adapters(
    *,
    mode: MediaMode,
    shot_count: int,
    ocr_adapter: OcrAdapter | None,
    visual_adapter: VisualAdapter | None,
) -> tuple[OcrAdapter | None, VisualAdapter | None]:
    if ocr_adapter is not None or visual_adapter is not None:
        return ocr_adapter, visual_adapter
    configured_ocr, configured_visual = configured_media_qa_adapters()
    if configured_ocr is not None or configured_visual is not None:
        return configured_ocr, configured_visual
    if (
        mode == "live"
        and os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER") == "1"
    ):
        from .media_vlm_qa import create_doubao_media_qa_adapters

        return create_doubao_media_qa_adapters(
            max_calls=min(5, max(1, int(shot_count))),
        )
    return None, None


def _persist_task(task: Any) -> None:
    if not hasattr(task, "model_dump"):
        return
    path = (
        Path(task.artifact_path)
        if getattr(task, "artifact_path", "")
        else (
            ensure_product(task.product_id)
            / "artifacts"
            / "creative_tasks"
            / f"{task.task_id}.json"
        )
    )
    write_json(path, task.model_dump(mode="json"))


def _selected_material_id(
    task: Any,
    bible: ProductionBibleArtifact,
) -> str:
    for item in getattr(task, "selected_materials", []) or []:
        material_id = str(item.get("material_id") or "").strip()
        if material_id:
            return material_id
    return next(
        (
            str(material_id)
            for material_id, role in bible.asset_roles.items()
            if role == "immutable_product_plate"
        ),
        "",
    )


def _load_plan(task: Any) -> MediaExecutionPlanArtifact:
    plan_id = str(task.professional_artifacts.get("media_execution_plan") or "")
    artifact = load_professional_artifact(task.product_id, plan_id)
    if not isinstance(artifact, MediaExecutionPlanArtifact):
        raise ValueError("creative task media plan is invalid")
    return artifact


def _load_plate(task: Any) -> ProductPlateArtifact | None:
    plate_id = str(task.professional_artifacts.get("product_plate") or "")
    if not plate_id:
        return None
    artifact = load_professional_artifact(task.product_id, plate_id)
    if not isinstance(artifact, ProductPlateArtifact):
        raise ValueError("creative task product plate is invalid")
    return artifact


def _shot_results(
    product_id: str,
    plan_id: str,
) -> list[MediaShotResultArtifact]:
    results = []
    for payload in artifacts().list(product_id, "media_shot_results"):
        if payload.get("plan_id") != plan_id:
            continue
        try:
            results.append(MediaShotResultArtifact.model_validate(payload))
        except ValueError:
            continue
    return sorted(
        results,
        key=lambda item: (item.shot_id, item.attempt, item.created_at),
    )


def _append_result_id(task: Any, artifact_id: str) -> None:
    recorded = task.professional_artifacts.setdefault("media_shot_results", [])
    if artifact_id not in recorded:
        recorded.append(artifact_id)


def _append_artifact_id(
    task: Any,
    collection: str,
    artifact_id: str,
) -> None:
    recorded = task.professional_artifacts.setdefault(collection, [])
    if artifact_id not in recorded:
        recorded.append(artifact_id)


def _pending_media_shots(task: Any) -> dict[str, dict[str, Any]]:
    pending = task.professional_artifacts.setdefault(
        "pending_media_shots",
        {},
    )
    if not isinstance(pending, dict):
        pending = {}
        task.professional_artifacts["pending_media_shots"] = pending
    return pending


def _video_task_id(payload: dict[str, Any]) -> str:
    task_doc = (
        payload.get("video_task")
        if isinstance(payload.get("video_task"), dict)
        else {}
    )
    job_doc = (
        payload.get("job")
        if isinstance(payload.get("job"), dict)
        else {}
    )
    return str(
        payload.get("video_task_id")
        or task_doc.get("video_task_id")
        or job_doc.get("video_task_id")
        or ""
    )


def _normalized_provider_status(payload: dict[str, Any]) -> str:
    status_doc = (
        payload.get("status")
        if isinstance(payload.get("status"), dict)
        else {}
    )
    return str(
        payload.get("normalized_status")
        or status_doc.get("normalized_status")
        or ""
    ).strip().lower()


def _repair_authorized(
    authorization: TaskAuthorizationRecord | None,
    *,
    plan: MediaExecutionPlanArtifact,
    failed_shot_ids: list[str],
) -> bool:
    failed_shots = [
        shot for shot in plan.shots if shot.shot_id in failed_shot_ids
    ]
    billable_shots = [
        shot for shot in failed_shots if shot.execution_mode != "local_motion"
    ]
    if not billable_shots:
        return bool(
            authorization is not None
            and authorization_allows(authorization, "local_media_repair")
        )
    if authorization is None:
        return False
    for shot in billable_shots:
        action = (
            "submit_image_generation_job"
            if shot.execution_mode == "image_background"
            else "submit_video_generation_task"
        )
        if not authorization_allows(authorization, action):
            return False
    return True


def apply_media_quality_gate(
    task: Any,
    *,
    manifest: MediaCompositeManifestArtifact,
    authorization: TaskAuthorizationRecord | None,
    ocr_adapter: OcrAdapter | None,
    visual_adapter: VisualAdapter | None,
) -> dict[str, Any]:
    """Run M14 QA and move a Creative Task only as far as evidence allows."""

    prior_reports = task.professional_artifacts.get("media_qa_reports", [])
    qa_run = len(prior_reports) + 1
    report = run_media_qa(
        task.product_id,
        plan_id=manifest.plan_id,
        manifest_id=manifest.artifact_id,
        ocr_adapter=ocr_adapter,
        visual_adapter=visual_adapter,
        qa_run=qa_run,
    )
    task.professional_artifacts["media_qa_report"] = report.artifact_id
    _append_artifact_id(task, "media_qa_reports", report.artifact_id)
    task.result_descriptors.append(
        {
            "type": "media_qa",
            "task_id": task.task_id,
            "qa_report_id": report.artifact_id,
            "manifest_id": manifest.artifact_id,
            "overall_result": report.overall_result,
            "failed_shot_ids": list(report.failed_shot_ids),
            "created_at": now_iso(),
        }
    )
    if report.overall_result == "PASS":
        task.professional_artifacts.pop("media_repair_decision", None)
        task.status = "AWAITING_FEEDBACK"
        task.current_stage = "AWAITING_FEEDBACK"
        task.blocked_reason = ""
        outcome = {
            "status": "PASS",
            "qa_report": report.model_dump(mode="json"),
        }
    elif report.overall_result == "REPAIR":
        repair_round = (
            len(task.professional_artifacts.get("media_repair_decisions", []))
            + 1
        )
        decision = plan_media_repair(
            task.product_id,
            qa_report_id=report.artifact_id,
            repair_round=repair_round,
        )
        task.professional_artifacts[
            "media_repair_decision"
        ] = decision.artifact_id
        _append_artifact_id(
            task,
            "media_repair_decisions",
            decision.artifact_id,
        )
        plan = load_professional_artifact(
            task.product_id,
            report.plan_id,
        )
        if not isinstance(plan, MediaExecutionPlanArtifact):
            raise ValueError("media repair decision references an invalid plan")
        if (
            decision.authorization_required
            and not _repair_authorized(
                authorization,
                plan=plan,
                failed_shot_ids=report.failed_shot_ids,
            )
        ):
            task.status = "BLOCKED_AUTHORIZATION"
            task.blocked_reason = (
                "Media QA requires Provider repair for failed shots, but the "
                "current task authorization is missing or exhausted."
            )
            outcome_status = "BLOCKED_AUTHORIZATION"
        else:
            task.status = "READY"
            task.blocked_reason = (
                "Media QA produced a bounded repair decision. Continue this "
                "task to repair only the failed shots."
            )
            outcome_status = decision.decision
        task.current_stage = "QUALITY_REVIEW"
        outcome = {
            "status": outcome_status,
            "qa_report": report.model_dump(mode="json"),
            "repair_decision": decision.model_dump(mode="json"),
        }
    elif report.overall_result == "HUMAN_REVIEW":
        task.status = "READY"
        task.current_stage = "QUALITY_REVIEW"
        task.blocked_reason = (
            "Media QA requires human review because one or more visual "
            "observations remain uncertain."
        )
        outcome = {
            "status": "HUMAN_REVIEW",
            "qa_report": report.model_dump(mode="json"),
        }
    else:
        task.status = "FAILED_FINAL"
        task.current_stage = "QUALITY_REVIEW"
        task.blocked_reason = (
            "Media QA rejected the output because of a non-repairable "
            "critical failure."
        )
        outcome = {
            "status": "REJECT",
            "qa_report": report.model_dump(mode="json"),
        }
    task.updated_at = now_iso()
    _persist_task(task)
    return outcome


def _provider_failure(
    task: Any,
    plan: MediaExecutionPlanArtifact,
    shot: Any,
    provider: str,
    attempt: int,
    error: Exception,
) -> MediaShotResultArtifact:
    task_token = hashlib.sha256(plan.task_id.encode("utf-8")).hexdigest()[:10]
    result = MediaShotResultArtifact(
        artifact_id=(
            f"media-shot-{task_token}-{shot.shot_id}-"
            f"{plan.content_hash[:10]}-a{attempt}"
        ),
        task_id=plan.task_id,
        product_id=plan.product_id,
        created_at=now_iso(),
        source_refs=[plan.artifact_id],
        status="BLOCKED",
        plan_id=plan.artifact_id,
        shot_id=shot.shot_id,
        attempt=attempt,
        execution_status=(
            "FAILED_RETRYABLE"
            if attempt < shot.max_attempts
            else "FAILED_FINAL"
        ),
        provider=provider,
        external_call_performed=False,
        input_hashes={},
        error_code="media_provider_failed",
        error_detail=f"{type(error).__name__}: {error}"[:2000],
        command_summary=["prepare shot payload", "submit shot source"],
    )
    save_professional_artifact(result)
    _append_result_id(task, result.artifact_id)
    return result


def _submission_source(
    product_root: Path,
    submission: dict[str, Any],
) -> Path | None:
    source = str(submission.get("source_media") or "")
    if source:
        return product_root / source
    files = submission.get("files") if isinstance(submission.get("files"), dict) else {}
    for key in ("image", "video"):
        value = str(files.get(key) or "")
        if value:
            path = Path(value)
            return path if path.is_absolute() else product_root / path
    result = submission.get("result") if isinstance(submission.get("result"), dict) else {}
    for output in result.get("outputs") or []:
        if not isinstance(output, dict):
            continue
        value = str(output.get("path") or "")
        if value:
            path = Path(value)
            return path if path.is_absolute() else product_root / path
    return None


def prepare_reliable_media_production(
    task: Any,
    *,
    provider: str,
    mode: MediaMode,
) -> dict[str, Any]:
    """Create dependency, plate and plan artifacts without Provider calls."""

    bible_id = str(task.professional_artifacts.get("production_bible") or "")
    bible = load_professional_artifact(task.product_id, bible_id)
    if not isinstance(bible, ProductionBibleArtifact):
        raise ValueError("reliable media production requires a Production Bible")
    material_id = _selected_material_id(task, bible)
    if not material_id:
        raise ValueError("reliable media production requires a selected product material")
    report = inspect_media_dependencies(
        task.product_id,
        task_id=task.task_id,
        material_id=material_id,
        production_bible_id=bible.artifact_id,
    )
    task.professional_artifacts["media_dependency_report"] = report.artifact_id
    task.professional_artifacts.setdefault("media_shot_results", [])
    if report.overall_status == "BLOCKED":
        task.status = "BLOCKED_PROVIDER"
        task.current_stage = "PREPARING_ASSETS"
        task.blocked_reason = "; ".join(report.blockers)
        _persist_task(task)
        return {
            "status": "BLOCKED",
            "dependency_report": report.model_dump(mode="json"),
            "provider_calls": 0,
        }

    exact_packaging = (
        bool(getattr(task.request, "preserve_exact_packaging", False))
        or bible.packaging_strategy == "exact-main-composite"
    )
    plate = (
        ensure_product_plate(
            task.product_id,
            task_id=task.task_id,
            material_id=material_id,
        )
        if exact_packaging
        else None
    )
    if plate:
        task.professional_artifacts["product_plate"] = plate.artifact_id
    plan = compile_media_execution_plan(
        task,
        dependency_report=report,
        product_plate=plate,
        provider=provider,
    )
    task.status = "READY"
    task.current_stage = "GENERATING"
    task.blocked_reason = ""
    task.updated_at = now_iso()
    _persist_task(task)
    return {
        "status": "READY",
        "provider": provider,
        "mode": mode,
        "provider_calls": 0,
        "dependency_report": report.model_dump(mode="json"),
        "product_plate": plate.model_dump(mode="json") if plate else {},
        "plan": plan.model_dump(mode="json"),
    }


def execute_reliable_media_production(
    task: Any,
    *,
    provider: str,
    mode: MediaMode,
    authorization: TaskAuthorizationRecord | None,
    ocr_adapter: OcrAdapter | None = None,
    visual_adapter: VisualAdapter | None = None,
    repair_decision_id: str = "",
) -> dict[str, Any]:
    """Execute pending shots, skipping durable successes and retrying failures."""

    if not task.professional_artifacts.get("media_execution_plan"):
        prepared = prepare_reliable_media_production(
            task,
            provider=provider,
            mode=mode,
        )
        if prepared["status"] != "READY":
            return prepared
    plan = _load_plan(task)
    planned_provider = str(plan.output_requirements.get("provider") or "")
    if planned_provider and planned_provider != provider:
        prior_results = _shot_results(task.product_id, plan.artifact_id)
        pending = _pending_media_shots(task)
        if pending or any(item.external_call_performed for item in prior_results):
            raise ValueError(
                "resume provider cannot change after an external media shot was submitted"
            )
        # A pre-submit plan may be safely replaced when the packaging route or
        # provider selection was corrected. The provider-specific plan id
        # preserves the old plan and failure artifacts for audit.
        task.professional_artifacts.pop("media_execution_plan", None)
        prepared = prepare_reliable_media_production(
            task,
            provider=provider,
            mode=mode,
        )
        if prepared["status"] != "READY":
            return prepared
        plan = _load_plan(task)
    plate = _load_plate(task)
    product_root = ensure_product(task.product_id)
    gateway = generation_provider_gateway()
    provider_calls = 0
    repair_decision: MediaRepairDecisionArtifact | None = None
    forced_repairs: dict[str, Any] = {}
    if repair_decision_id:
        loaded_decision = load_professional_artifact(
            task.product_id,
            repair_decision_id,
        )
        if not isinstance(loaded_decision, MediaRepairDecisionArtifact):
            raise ValueError("media repair resume requires a Repair Decision")
        if loaded_decision.decision not in {
            "LOCAL_REPAIR",
            "PROVIDER_REPAIR",
        }:
            raise ValueError("terminal media repair decisions cannot be executed")
        repair_decision = loaded_decision
        forced_repairs = {
            item.shot_id: item
            for item in loaded_decision.shot_repairs
        }
    else:
        unresolved_decision_id = str(
            task.professional_artifacts.get("media_repair_decision") or ""
        )
        if unresolved_decision_id:
            unresolved = load_professional_artifact(
                task.product_id,
                unresolved_decision_id,
            )
            if not isinstance(unresolved, MediaRepairDecisionArtifact):
                raise ValueError("media repair decision is invalid")
            failed_provider_shots = [
                item.shot_id
                for item in unresolved.shot_repairs
                if item.provider_call_required
            ]
            if (
                unresolved.authorization_required
                and not _repair_authorized(
                    authorization,
                    plan=plan,
                    failed_shot_ids=failed_provider_shots,
                )
            ):
                task.status = "BLOCKED_AUTHORIZATION"
                task.blocked_reason = (
                    "Media QA requires Provider repair, but the current task "
                    "authorization is missing, expired, or exhausted."
                )
                outcome = "BLOCKED_AUTHORIZATION"
            else:
                task.status = "READY"
                task.blocked_reason = (
                    "An unresolved Media Repair Decision must be executed or "
                    "reviewed before this output can be quality-gated again."
                )
                outcome = unresolved.decision
            task.current_stage = "QUALITY_REVIEW"
            task.updated_at = now_iso()
            _persist_task(task)
            return {
                "status": outcome,
                "repair_decision": unresolved.model_dump(mode="json"),
                "provider_calls": 0,
            }

    for shot in plan.shots:
        existing = [
            result
            for result in _shot_results(task.product_id, plan.artifact_id)
            if result.shot_id == shot.shot_id
        ]
        completed = next(
            (
                result
                for result in reversed(existing)
                if result.execution_status == "COMPLETED"
            ),
            None,
        )
        repair = forced_repairs.get(shot.shot_id)
        if completed is not None and repair is None:
            _append_result_id(task, completed.artifact_id)
            continue
        pending_shots = _pending_media_shots(task)
        pending = pending_shots.get(shot.shot_id)
        if pending is not None:
            if mode != "live":
                raise ValueError("pending Provider media shots require live mode")
            if authorization is None or not authorization_allows(
                authorization,
                "check_video_task_status",
            ):
                task.status = "BLOCKED_AUTHORIZATION"
                task.current_stage = "GENERATING"
                task.blocked_reason = (
                    "The task authorization expired before the pending media "
                    "shot could be recovered."
                )
                _persist_task(task)
                return {
                    "status": "BLOCKED_AUTHORIZATION",
                    "pending_shot": shot.shot_id,
                    "provider_calls": provider_calls,
                }
            provider_task_id = str(
                pending.get("video_task_id") or ""
            )
            if not provider_task_id:
                raise ValueError("pending media shot has no recoverable video task id")
            status_result = gateway.check_video_task(
                task.product_id,
                provider_task_id,
                provider,
                True,
            )
            normalized = _normalized_provider_status(status_result)
            if normalized in {"failed", "cancelled", "canceled", "expired"}:
                pending_shots.pop(shot.shot_id, None)
                error = RuntimeError(
                    f"Provider video task reached terminal status: {normalized}"
                )
                attempt = int(pending.get("attempt") or 1)
                result = _provider_failure(
                    task,
                    plan,
                    shot,
                    provider,
                    attempt,
                    error,
                )
                task.status = result.execution_status
                task.current_stage = "GENERATING"
                task.blocked_reason = result.error_detail
                task.updated_at = now_iso()
                _persist_task(task)
                return {
                    "status": result.execution_status,
                    "failed_shot": shot.shot_id,
                    "provider_task_id": provider_task_id,
                    "provider_calls": provider_calls,
                }
            source = _submission_source(product_root, status_result)
            if normalized != "completed" or source is None or not source.is_file():
                task.status = "BLOCKED_PROVIDER"
                task.current_stage = "GENERATING"
                task.blocked_reason = (
                    f"{shot.shot_id} Provider task is "
                    f"{normalized or 'pending'}; continue this task later."
                )
                task.updated_at = now_iso()
                _persist_task(task)
                return {
                    "status": "BLOCKED_PROVIDER",
                    "pending_shot": shot.shot_id,
                    "provider_task_id": provider_task_id,
                    "provider_status": normalized or "pending",
                    "provider_calls": provider_calls,
                }
            attempt = int(pending.get("attempt") or 1)
            result = render_shot(
                task.product_id,
                plan=plan,
                shot=shot,
                source_media=source,
                product_plate=plate,
                attempt=attempt,
            )
            pending_shots.pop(shot.shot_id, None)
            _append_result_id(task, result.artifact_id)
            if result.execution_status != "COMPLETED":
                task.status = result.execution_status
                task.current_stage = "GENERATING"
                task.blocked_reason = result.error_detail
                task.updated_at = now_iso()
                _persist_task(task)
                return {
                    "status": result.execution_status,
                    "failed_shot": shot.shot_id,
                    "provider_task_id": provider_task_id,
                    "shot_result": result.model_dump(mode="json"),
                    "provider_calls": provider_calls,
                }
            continue
        if repair is not None and not repair.provider_call_required:
            if completed is None or not completed.source_relative_path:
                task.status = "READY"
                task.current_stage = "QUALITY_REVIEW"
                task.blocked_reason = (
                    f"{shot.shot_id} cannot be repaired locally because its "
                    "original background source was not retained."
                )
                _persist_task(task)
                return {
                    "status": "HUMAN_REVIEW",
                    "repair_decision": (
                        repair_decision.model_dump(mode="json")
                        if repair_decision
                        else {}
                    ),
                    "repair_shot": shot.shot_id,
                    "provider_calls": provider_calls,
                }
            attempt = max(
                (result.attempt for result in existing),
                default=0,
            ) + 1
            result = render_shot(
                task.product_id,
                plan=plan,
                shot=shot,
                source_media=(
                    product_root / completed.source_relative_path
                ),
                product_plate=plate,
                attempt=attempt,
            )
            _append_result_id(task, result.artifact_id)
            if result.execution_status != "COMPLETED":
                task.status = (
                    "FAILED_RETRYABLE"
                    if result.execution_status == "FAILED_RETRYABLE"
                    else "FAILED_FINAL"
                )
                task.current_stage = "QUALITY_REVIEW"
                task.blocked_reason = result.error_detail
                _persist_task(task)
                return {
                    "status": task.status,
                    "failed_shot": shot.shot_id,
                    "shot_result": result.model_dump(mode="json"),
                    "provider_calls": provider_calls,
                }
            continue
        attempt = max((result.attempt for result in existing), default=0) + 1
        attempt_limit = shot.max_attempts + (1 if repair is not None else 0)
        if attempt > attempt_limit:
            task.status = "FAILED_FINAL"
            task.current_stage = "GENERATING"
            task.blocked_reason = f"{shot.shot_id} exceeded its retry limit"
            _persist_task(task)
            return {
                "status": "FAILED_FINAL",
                "failed_shot": shot.shot_id,
                "provider_calls": provider_calls,
            }

        media_kind = (
            "image"
            if shot.execution_mode in {"image_background", "local_motion"}
            else "video"
        )
        action = (
            "submit_image_generation_job"
            if media_kind == "image"
            else "submit_video_generation_task"
        )
        if mode == "live":
            if authorization is None or not authorization_allows(
                authorization,
                action,
            ):
                task.status = "BLOCKED_AUTHORIZATION"
                task.current_stage = "GENERATING"
                task.blocked_reason = f"task authorization does not allow {action}"
                _persist_task(task)
                return {
                    "status": "BLOCKED_AUTHORIZATION",
                    "blocked_action": action,
                    "provider_calls": provider_calls,
                }
        try:
            prepared = gateway.prepare_media_shot(
                task.product_id,
                plan.artifact_id,
                shot.shot_id,
                provider,
                media_kind,
            )
            submission = gateway.submit_media_shot(
                task.product_id,
                prepared["payload_id"],
                provider,
                mode,
            )
            provider_calls += 1
            if mode == "live" and authorization is not None:
                consume_task_authorization(authorization, action)
            source = _submission_source(product_root, submission)
            if source is None or not source.is_file():
                provider_task_id = _video_task_id(submission)
                if media_kind == "video" and provider_task_id:
                    pending_shots[shot.shot_id] = {
                        "video_task_id": provider_task_id,
                        "provider": provider,
                        "payload_id": prepared["payload_id"],
                        "attempt": attempt,
                        "submitted_at": now_iso(),
                    }
                task.status = "BLOCKED_PROVIDER"
                task.current_stage = "GENERATING"
                task.blocked_reason = (
                    f"{shot.shot_id} provider result is pending or has no local media file"
                )
                task.updated_at = now_iso()
                _persist_task(task)
                return {
                    "status": "BLOCKED_PROVIDER",
                    "pending_shot": shot.shot_id,
                    "provider_task_id": provider_task_id,
                    "provider_submission": submission,
                    "provider_calls": provider_calls,
                }
            result = render_shot(
                task.product_id,
                plan=plan,
                shot=shot,
                source_media=source,
                product_plate=plate,
                attempt=attempt,
            )
            _append_result_id(task, result.artifact_id)
        except Exception as exc:
            result = _provider_failure(
                task,
                plan,
                shot,
                provider,
                attempt,
                exc,
            )
        if result.execution_status != "COMPLETED":
            task.status = (
                "FAILED_RETRYABLE"
                if result.execution_status == "FAILED_RETRYABLE"
                else "FAILED_FINAL"
            )
            task.current_stage = "GENERATING"
            task.blocked_reason = result.error_detail
            task.updated_at = now_iso()
            _persist_task(task)
            return {
                "status": task.status,
                "failed_shot": shot.shot_id,
                "shot_result": result.model_dump(mode="json"),
                "provider_calls": provider_calls,
            }

    completed_results = []
    latest_results = _shot_results(task.product_id, plan.artifact_id)
    for shot in plan.shots:
        completed_results.append(
            next(
                result
                for result in reversed(latest_results)
                if result.shot_id == shot.shot_id
                and result.execution_status == "COMPLETED"
            )
        )
    manifest = compose_final_video(
        task.product_id,
        plan=plan,
        shot_results=completed_results,
    )
    task.professional_artifacts["media_composite_manifest"] = manifest.artifact_id
    result_id = (
        f"video-result-{task.task_id}-m13-"
        f"{manifest.output_content_hash[:10]}"
    )
    result_path = (
        product_root
        / "artifacts"
        / "generated_videos"
        / f"{result_id}.json"
    )
    result_document = {
        "schema_version": "product_creative.generation_result.v0.5.1",
        "result_id": result_id,
        "task_id": task.task_id,
        "product_id": task.product_id,
        "created_at": now_iso(),
        "provider": "hybrid-shot-graph",
        "brief_type": "video",
        "mode": mode,
        "status": "completed",
        "external_call_performed": mode == "live",
        "source_media_plan_id": plan.artifact_id,
        "source_media_manifest_id": manifest.artifact_id,
        "outputs": [
            {
                "type": "video",
                "path": manifest.output_relative_path,
                "mime_type": "video/mp4",
                "bytes": (
                    product_root / manifest.output_relative_path
                ).stat().st_size,
                "mock": False,
                "description": (
                    "Shot-scoped hybrid production with immutable product plate "
                    "and deterministic subtitles."
                ),
            }
        ],
        "review": {
            "requires_human_review": True,
            "ready_for_feedback": True,
            "notes": (
                "Review story quality, packaging integrity, subtitle accuracy, "
                "and whether the selected creative direction matches the product."
            ),
        },
        "summary": (
            "Produced a recoverable shot-level video and composed the final MP4."
        ),
    }
    write_json(result_path, result_document)
    descriptor = {
        "type": "media_result",
        "task_id": task.task_id,
        "result_id": result_id,
        "plan_id": plan.artifact_id,
        "manifest_id": manifest.artifact_id,
        "path": manifest.output_relative_path,
        "content_hash": manifest.output_content_hash,
        "created_at": now_iso(),
    }
    if descriptor not in task.result_descriptors:
        task.result_descriptors.append(descriptor)
    ocr_adapter, visual_adapter = _resolve_media_qa_adapters(
        mode=mode,
        shot_count=len(plan.shots),
        ocr_adapter=ocr_adapter,
        visual_adapter=visual_adapter,
    )
    quality = apply_media_quality_gate(
        task,
        manifest=manifest,
        authorization=authorization,
        ocr_adapter=ocr_adapter,
        visual_adapter=visual_adapter,
    )
    result_document["review"] = {
        "requires_human_review": quality["status"] != "PASS",
        "ready_for_feedback": quality["status"] == "PASS",
        "qa_report_id": task.professional_artifacts.get(
            "media_qa_report",
            "",
        ),
        "qa_result": (
            quality.get("qa_report") or {}
        ).get("overall_result", ""),
        "notes": (
            "Automated media QA passed; collect user feedback."
            if quality["status"] == "PASS"
            else task.blocked_reason
        ),
    }
    write_json(result_path, result_document)
    return {
        "status": (
            "COMPLETED" if quality["status"] == "PASS" else quality["status"]
        ),
        "provider_calls": provider_calls,
        "shot_results": [
            result.model_dump(mode="json")
            for result in completed_results
        ],
        "manifest": manifest.model_dump(mode="json"),
        "result": result_document,
        "quality": quality,
    }


def resume_reliable_media_production(
    task: Any,
    *,
    provider: str,
    mode: MediaMode,
    authorization: TaskAuthorizationRecord | None,
    ocr_adapter: OcrAdapter | None = None,
    visual_adapter: VisualAdapter | None = None,
    repair_decision_id: str = "",
) -> dict[str, Any]:
    return execute_reliable_media_production(
        task,
        provider=provider,
        mode=mode,
        authorization=authorization,
        ocr_adapter=ocr_adapter,
        visual_adapter=visual_adapter,
        repair_decision_id=repair_decision_id,
    )
