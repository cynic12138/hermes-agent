"""Recoverable user-goal records that orchestrate existing capability workflows."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List

from ..brain.discovery import assess_product_readiness, create_field_confirmation_proposal
from ..application.command_bus import command_bus
from ..application.planner import GoalPlanner
from ..common import ensure_product, now_iso, read_json, write_json
from ..contracts.models import (
    CreativeTaskPlan,
    CreativeTaskRecord,
    CreativeTaskRequest,
    DiscoveryQuestion,
    DiscoverySessionRecord,
)
from ..contracts.durable import CommandEnvelope
from ..provider_registry import provider_entry
from .authorization import (
    approve_task_authorization,
    authorization_allows,
    consume_task_authorization,
    create_task_authorization_request,
    load_task_authorization,
)
from ..ports.runtime_repositories import artifacts


def _plan_stages(request: CreativeTaskRequest) -> List[str]:
    stages = ["UNDERSTANDING"]
    if request.requires_fresh_inspiration:
        stages.append("RESEARCHING")
    stages.append("IDEATING")
    if any(item in request.deliverables for item in ("image", "video")):
        stages.append("PREPARING_ASSETS")
    stages.extend(["GENERATING", "DELIVERING", "AWAITING_FEEDBACK"])
    return stages


def _ensure_authorization_request(task: CreativeTaskRecord) -> None:
    needs_authorization = any(
        step.guard == "task_authorization" for step in task.plan.actions
    )
    if task.readiness.ready and needs_authorization and not task.authorization_request_id:
        request = create_task_authorization_request(task)
        task.authorization_request_id = request.request_id


def _replan_task(task: CreativeTaskRecord) -> None:
    task.plan = CreativeTaskPlan(
        task_id=task.task_id,
        stages=_plan_stages(task.request),
        actions=GoalPlanner().creative_task_actions(task.request),
    )
    task.completed_stages = []
    task.selected_materials = []
    task.selected_idea = {}
    task.authorization_request_id = ""
    task.authorization_id = ""


def _latest_capability_output(task: CreativeTaskRecord, action: str) -> dict:
    for item in reversed(task.result_descriptors):
        if item.get("type") == "capability_result" and item.get("action") == action:
            output = item.get("output")
            return output if isinstance(output, dict) else {}
    return {}


def _effective_goal(task: CreativeTaskRecord) -> str:
    if not task.revision_messages:
        return task.request.raw_message
    return f"{task.request.raw_message}\n本次修订要求：{task.revision_messages[-1]}"


def _material_task(request: CreativeTaskRequest) -> str:
    if "video" in request.deliverables:
        return "video_brief"
    if "image" in request.deliverables:
        return "image_brief"
    return "channel_content"


def _provider_for(task: CreativeTaskRecord, kind: str) -> str:
    requested = task.provider.strip()
    if requested in {"mock", "mock-all"}:
        return f"mock-{kind}"
    if requested:
        try:
            if kind in (provider_entry(requested).get("supported_types") or []):
                return requested
        except ValueError:
            pass
    return "volcengine-ark-video" if kind == "video" else "volcengine-ark-image"


def _offline_action_args(task: CreativeTaskRecord, action: str) -> dict:
    product_id = task.product_id
    selected_id = str((task.selected_materials or [{}])[0].get("material_id") or "")
    if action == "prepare_task_material_pack":
        return {"product_id": product_id, "task": _material_task(task.request), "limit": 3}
    if action == "create_inspiration_candidates":
        return {
            "product_id": product_id,
            "snapshot": _latest_capability_output(task, "collect_external_source_snapshot").get("snapshot_id", ""),
            "goal": _effective_goal(task),
            "max_candidates": 5,
        }
    if action == "create_inspiration_pack":
        candidate_output = _latest_capability_output(task, "create_inspiration_candidates")
        return {
            "product_id": product_id,
            "candidates": [
                item.get("candidate_id")
                for item in candidate_output.get("candidates") or []
                if isinstance(item, dict) and item.get("candidate_id")
            ],
            "goal": _effective_goal(task),
            "target": "video_brief" if "video" in task.request.deliverables else "image_brief",
            "limit": 3,
        }
    if action == "run_channel_review":
        return {
            "product_id": product_id,
            "target": (
                "douyin-short-video-script"
                if "抖音" in task.request.raw_message
                else "ecommerce-main-image-copy"
            ),
            "variants": 3,
            "creative_brief": {
                "goal": _effective_goal(task),
                "raw_message": _effective_goal(task),
                "requested_outputs": list(task.request.deliverables),
                "source": "rule_fallback",
            },
        }
    if action == "resolve_image_intent":
        return {
            "product_id": product_id,
            "message": _effective_goal(task),
            "target": "ecommerce-main-image-copy",
            "count": 1,
            "style": "",
            "provider": _provider_for(task, "image"),
        }
    if action == "create_image_brief":
        return {
            "product_id": product_id,
            "intent_id": _latest_capability_output(task, "resolve_image_intent").get("intent_id", ""),
            "artifact_id": "",
            "variant": None,
        }
    if action == "review_image_brief":
        briefs = _latest_capability_output(task, "create_image_brief").get("briefs") or []
        brief_id = briefs[0].get("brief_id", "") if briefs and isinstance(briefs[0], dict) else ""
        return {"product_id": product_id, "brief_id": brief_id}
    if action == "create_batch_generation_policy":
        briefs = _latest_capability_output(task, "create_image_brief").get("briefs") or []
        brief_id = briefs[0].get("brief_id", "") if briefs and isinstance(briefs[0], dict) else ""
        return {
            "product_id": product_id,
            "intent_id": _latest_capability_output(task, "resolve_image_intent").get("intent_id", ""),
            "brief_id": brief_id,
            "provider": _provider_for(task, "image"),
            "mode": "mock" if _provider_for(task, "image").startswith("mock") else "live",
            "count": 1,
            "note": f"Approved only for Creative Task {task.task_id}.",
            "confirmed": True,
        }
    if action == "build_image_provider_payload":
        briefs = _latest_capability_output(task, "create_image_brief").get("briefs") or []
        brief_id = briefs[0].get("brief_id", "") if briefs and isinstance(briefs[0], dict) else ""
        return {
            "product_id": product_id,
            "brief_id": brief_id,
            "provider": _provider_for(task, "image"),
            "batch_policy_id": _latest_capability_output(task, "create_batch_generation_policy").get("policy_id", ""),
        }
    if action == "check_image_live_readiness":
        return {
            "product_id": product_id,
            "payload_id": _latest_capability_output(task, "build_image_provider_payload").get("payload_id", ""),
            "provider": _provider_for(task, "image"),
            "kind": "image",
        }
    if action == "resolve_video_intent":
        return {
            "product_id": product_id,
            "message": _effective_goal(task),
            "asset": selected_id,
            "platform": "douyin" if "抖音" in task.request.raw_message else "",
            "theme": "",
        }
    if action == "create_video_brief":
        return {
            "product_id": product_id,
            "intent_id": _latest_capability_output(task, "resolve_video_intent").get("intent_id", ""),
        }
    if action == "review_video_brief":
        return {
            "product_id": product_id,
            "brief_id": _latest_capability_output(task, "create_video_brief").get("brief_id", ""),
        }
    if action == "build_video_provider_payload":
        return {
            "product_id": product_id,
            "brief_id": _latest_capability_output(task, "create_video_brief").get("brief_id", ""),
            "provider": _provider_for(task, "video"),
        }
    if action in {"check_video_reference_readiness", "check_video_live_readiness"}:
        return {
            "product_id": product_id,
            "payload_id": _latest_capability_output(task, "build_video_provider_payload").get("payload_id", ""),
            "provider": _provider_for(task, "video"),
            "kind": "video",
        }
    if action == "create_video_execution_policy":
        return {
            "product_id": product_id,
            "payload_id": _latest_capability_output(task, "build_video_provider_payload").get("payload_id", ""),
            "provider": _provider_for(task, "video"),
            "mode": "mock" if _provider_for(task, "video").startswith("mock") else "live",
            "note": f"Approved only for Creative Task {task.task_id}.",
            "confirmed": True,
        }
    if action == "compose_exact_main_video":
        return {
            "product_id": product_id,
            "asset": selected_id,
            "theme": _effective_goal(task),
            "template": "anime_story",
            "duration": 10,
            "fps": 24,
        }
    if action == "review_generated_result":
        _, result_id = _latest_generated_result(task)
        return {"product_id": product_id, "result_id": result_id}
    return {"product_id": product_id}


def _record_capability_result(task: CreativeTaskRecord, action: str, result) -> None:
    task.result_descriptors.append(
        {
            "type": "capability_result",
            "action": action,
            "status": result.status,
            "output": result.output,
        }
    )


def _prepare_video_material_understanding(task: CreativeTaskRecord, intent_output: dict) -> dict:
    """Satisfy the existing video-intent material prerequisites with mock-only local analysis."""

    current = intent_output
    for _ in range(2):
        intent = current.get("video_intent") if isinstance(current.get("video_intent"), dict) else {}
        recommended = intent.get("recommended_steps") or []
        next_step = recommended[0] if recommended and isinstance(recommended[0], dict) else {}
        selected = intent.get("selected_material") if isinstance(intent.get("selected_material"), dict) else {}
        if current.get("status") == "ready_for_video_brief":
            return current
        if next_step.get("step") == "analyze_image":
            action = "analyze_material_image"
            args = {
                "product_id": task.product_id,
                "asset": selected.get("material_id", ""),
                "provider": "mock-vision",
            }
        elif next_step.get("step") == "visual_align":
            action = "align_visual_analysis"
            latest_analysis = _latest_capability_output(task, "analyze_material_image")
            related_artifacts = (
                intent.get("related_artifacts")
                if isinstance(intent.get("related_artifacts"), dict)
                else {}
            )
            args = {
                "product_id": task.product_id,
                # The intent resolver can select an analysis that predates
                # this Creative Task. Prefer a task-local analysis when one
                # was just created, otherwise reuse the durable analysis id
                # already attached to the resolved video intent.
                "analysis": latest_analysis.get("analysis_id", "")
                or related_artifacts.get("image_analysis_id", ""),
                "note": "Task-scoped alignment for creative preparation; no Product Brain writeback.",
            }
        else:
            return current
        result = command_bus().dispatch(
            CommandEnvelope(
                command=action,
                product_id=task.product_id,
                trace_id=f"trace-{task.task_id}",
                idempotency_key=f"{task.task_id}:{action}:{args.get('asset') or args.get('analysis') or 'step'}",
                payload=args,
            )
        )
        if not result.success:
            return current
        _record_capability_result(task, action, result)
        rerun = command_bus().dispatch(
            CommandEnvelope(
                command="resolve_video_intent",
                product_id=task.product_id,
                trace_id=f"trace-{task.task_id}",
                payload=_offline_action_args(task, "resolve_video_intent"),
            )
        )
        if not rerun.success:
            return current
        _record_capability_result(task, "resolve_video_intent", rerun)
        current = rerun.output
    return current


def advance_offline_preparation(task: CreativeTaskRecord) -> CreativeTaskRecord:
    """Run only local, non-billable steps and stop before any external call."""

    if not task.readiness.ready:
        return task
    for step in task.plan.actions:
        if step.status == "COMPLETED":
            continue
        task.current_stage = step.stage
        if step.action == "collect_external_source_snapshot":
            if not task.authorization_id:
                task.status = "BLOCKED_AUTHORIZATION"
                task.blocked_reason = "External research is waiting for task authorization."
            else:
                task.status = "RESEARCHING"
                task.blocked_reason = "Hermes must collect authorized external evidence before inspiration mining can continue."
            break
        if task.provider.startswith("mock") and step.action in {
            "check_video_reference_readiness",
            "check_video_live_readiness",
            "create_video_execution_policy",
            "check_image_live_readiness",
        }:
            step.status = "COMPLETED"
            task.result_descriptors.append(
                {
                    "type": "capability_result",
                    "action": step.action,
                    "status": "succeeded",
                    "output": {
                        "success": True,
                        "mode": "mock",
                        "external_call_performed": False,
                        "not_required_for_mock": True,
                    },
                }
            )
            continue
        if step.guard == "task_authorization":
            if not task.authorization_id:
                task.status = "BLOCKED_AUTHORIZATION"
                task.blocked_reason = f"{step.action} is waiting for task authorization."
            else:
                task.status = "READY"
                task.blocked_reason = (
                    f"{step.action} is ready for the live execution runner; "
                    "offline preparation does not call external providers."
                )
            break
        task_authorized_local_policy = step.action in {
            "create_video_execution_policy",
            "create_batch_generation_policy",
        } and bool(task.authorization_id)
        if step.guard == "human_confirmation" and not task_authorized_local_policy:
            task.status = "BLOCKED_AUTHORIZATION"
            task.blocked_reason = f"{step.action} is waiting at an authorization boundary."
            break
        args = _offline_action_args(task, step.action)
        try:
            result = command_bus().dispatch(
                CommandEnvelope(
                    command=step.action,
                    product_id=task.product_id,
                    trace_id=f"trace-{task.task_id}",
                    confirmed=task_authorized_local_policy,
                    payload=args,
                )
            )
        except Exception as exc:
            step.status = "FAILED"
            task.status = "FAILED_FINAL"
            task.blocked_reason = f"{step.action} failed: {type(exc).__name__}: {exc}"
            break
        if not result.success:
            step.status = "FAILED"
            task.status = "FAILED_RETRYABLE" if result.retryable else "FAILED_FINAL"
            task.blocked_reason = result.error_message or f"{step.action} failed"
            break
        step.status = "COMPLETED"
        _record_capability_result(task, step.action, result)
        if step.action == "prepare_task_material_pack":
            pack = result.output.get("task_material_pack") or {}
            task.selected_materials = list(pack.get("selected_materials") or [])
            if not task.selected_materials:
                task.status = "BLOCKED_PRODUCT"
                task.blocked_reason = "No usable product material was selected for this task."
                break
        if step.action == "create_inspiration_pack":
            pack = result.output.get("inspiration_pack") or {}
            candidates = pack.get("candidates") or []
            task.selected_idea = dict(candidates[0]) if candidates and isinstance(candidates[0], dict) else {}
        if step.action == "resolve_video_intent" and result.output.get("status") != "ready_for_video_brief":
            prepared = _prepare_video_material_understanding(task, result.output)
            if prepared.get("status") != "ready_for_video_brief":
                task.status = "BLOCKED_PRODUCT"
                task.blocked_reason = "Selected product material still needs preparation before a video brief can be created."
                break
        if step.action == "review_video_brief" and task.request.autonomy_mode == "preview_first":
            task.status = "NEEDS_INPUT"
            task.blocked_reason = "The creative preview is ready for user review."
            break
        if step.action == "check_video_reference_readiness" and not result.output.get("ready_for_provider"):
            task.status = "BLOCKED_PRODUCT"
            task.blocked_reason = "; ".join(result.output.get("blockers") or ["Video references are not provider-ready."])
            break
        if step.action == "check_video_live_readiness" and not result.output.get("ready_for_live"):
            task.status = "BLOCKED_PROVIDER"
            task.blocked_reason = "; ".join(result.output.get("blockers") or ["Video provider is not ready."])
            break
    else:
        task.status = "AWAITING_FEEDBACK"
        task.current_stage = "AWAITING_FEEDBACK"
        task.blocked_reason = ""

    for stage in task.plan.stages:
        stage_steps = [item for item in task.plan.actions if item.stage == stage]
        if stage_steps and all(item.status == "COMPLETED" for item in stage_steps):
            if stage not in task.completed_stages:
                task.completed_stages.append(stage)
    task.updated_at = now_iso()
    return task


def execute_authorized_mock_generation(task: CreativeTaskRecord) -> CreativeTaskRecord:
    """Exercise the durable provider path without network or billable calls."""

    if (
        not task.provider.startswith("mock")
        or not task.authorization_id
        or task.status in {"FAILED_FINAL", "FAILED_RETRYABLE", "BLOCKED_PRODUCT", "BLOCKED_PROVIDER"}
    ):
        return task
    submit_actions = {"submit_image_generation_job", "submit_video_generation_task"}
    for _ in range(2):
        submit_index = next(
            (
                index
                for index, item in enumerate(task.plan.actions)
                if item.action in submit_actions and item.status != "COMPLETED"
            ),
            -1,
        )
        if submit_index < 0:
            break
        if any(item.status != "COMPLETED" for item in task.plan.actions[:submit_index]):
            return task
        submit = task.plan.actions[submit_index]
        authorization = load_task_authorization(task.product_id, task.authorization_id)
        if not authorization_allows(authorization, submit.action):
            task.status = "BLOCKED_AUTHORIZATION"
            task.blocked_reason = "Task authorization is missing, expired, or exhausted."
            return task
        is_video = submit.action == "submit_video_generation_task"
        kind = "video" if is_video else "image"
        payload_action = "build_video_provider_payload" if is_video else "build_image_provider_payload"
        payload_id = _latest_capability_output(task, payload_action).get("payload_id", "")
        payload = {
            "product_id": task.product_id,
            "payload_id": payload_id,
            "provider": _provider_for(task, kind),
            "mode": "mock",
        }
        if is_video:
            payload["execution_policy_id"] = ""
        else:
            payload["count"] = 1
        result = command_bus().dispatch(
            CommandEnvelope(
                command=submit.action,
                product_id=task.product_id,
                trace_id=f"trace-{task.task_id}",
                idempotency_key=f"{task.task_id}:{submit.action}:{payload_id}",
                confirmed=True,
                payload=payload,
            )
        )
        if not result.success:
            task.status = "FAILED_RETRYABLE" if result.retryable else "FAILED_FINAL"
            task.blocked_reason = result.error_message or str(
                result.output.get("error") or result.output or "Mock generation failed."
            )
            return task
        output = dict(result.output)
        if is_video:
            generated = output.get("result") if isinstance(output.get("result"), dict) else {}
            output["result_id"] = generated.get("result_id", "")
        submit.status = "COMPLETED"
        task.result_descriptors.append(
            {
                "type": "capability_result",
                "action": submit.action,
                "status": result.status,
                "output": output,
            }
        )
        if is_video:
            status_step = next(
                (item for item in task.plan.actions if item.action == "check_video_task_status"),
                None,
            )
            if status_step is not None:
                status_step.status = "COMPLETED"
        consume_task_authorization(authorization, submit.action)
        advance_offline_preparation(task)
    task.status = "AWAITING_FEEDBACK"
    task.current_stage = "AWAITING_FEEDBACK"
    task.blocked_reason = ""
    task.updated_at = now_iso()
    return task


def _video_task_id(output: dict) -> str:
    task_doc = output.get("video_task") if isinstance(output.get("video_task"), dict) else {}
    job_doc = output.get("job") if isinstance(output.get("job"), dict) else {}
    return str(
        output.get("video_task_id")
        or task_doc.get("video_task_id")
        or job_doc.get("video_task_id")
        or ""
    )


def execute_authorized_live_generation(task: CreativeTaskRecord) -> CreativeTaskRecord:
    """Submit or poll one authorized live provider operation.

    The caller must have received explicit task-scoped authorization. This
    function is never used by offline preparation or tests with the default
    provider gateway unless PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1 is set.
    """

    if task.provider.startswith("mock") or not task.authorization_id or task.status == "RESEARCHING":
        return task
    if os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER") != "1":
        task.status = "READY"
        task.blocked_reason = (
            "Live provider execution is authorized for this task but disabled in this runtime. "
            "Set PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1 only in an approved live session."
        )
        task.updated_at = now_iso()
        return task
    if task.status in {"FAILED_FINAL", "BLOCKED_PRODUCT", "BLOCKED_PROVIDER"}:
        return task
    authorization = load_task_authorization(task.product_id, task.authorization_id)
    submit_actions = {"submit_image_generation_job", "submit_video_generation_task"}
    submit_index = next(
        (
            index
            for index, item in enumerate(task.plan.actions)
            if item.action in submit_actions and item.status != "COMPLETED"
        ),
        -1,
    )
    if submit_index >= 0:
        if any(item.status != "COMPLETED" for item in task.plan.actions[:submit_index]):
            return task
        submit = task.plan.actions[submit_index]
        if not authorization_allows(authorization, submit.action):
            task.status = "BLOCKED_AUTHORIZATION"
            task.blocked_reason = "Task authorization is missing, expired, or exhausted."
            return task
        is_video = submit.action == "submit_video_generation_task"
        kind = "video" if is_video else "image"
        payload_action = "build_video_provider_payload" if is_video else "build_image_provider_payload"
        payload_id = str(_latest_capability_output(task, payload_action).get("payload_id") or "")
        payload = {
            "product_id": task.product_id,
            "payload_id": payload_id,
            "provider": _provider_for(task, kind),
            "mode": "live",
        }
        if is_video:
            payload["execution_policy_id"] = str(
                _latest_capability_output(task, "create_video_execution_policy").get("policy_id") or ""
            )
        else:
            payload["count"] = 1
        try:
            result = command_bus().dispatch(
                CommandEnvelope(
                    command=submit.action,
                    product_id=task.product_id,
                    trace_id=f"trace-{task.task_id}",
                    idempotency_key=f"{task.task_id}:{submit.action}:{payload_id}",
                    confirmed=True,
                    payload=payload,
                )
            )
        except Exception as exc:
            task.status = "FAILED_RETRYABLE"
            task.blocked_reason = f"{submit.action} failed: {type(exc).__name__}: {exc}"
            task.updated_at = now_iso()
            return task
        if not result.success:
            task.status = "FAILED_RETRYABLE" if result.retryable else "FAILED_FINAL"
            task.blocked_reason = result.error_message or f"{submit.action} failed"
            task.updated_at = now_iso()
            return task
        submit.status = "COMPLETED"
        _record_capability_result(task, submit.action, result)
        consume_task_authorization(authorization, submit.action)
        if is_video:
            remote_task_id = _video_task_id(result.output)
            if not remote_task_id:
                task.status = "FAILED_FINAL"
                task.blocked_reason = "Video provider submission did not return a recoverable task id."
            else:
                task.status = "GENERATING"
                task.current_stage = "GENERATING"
                task.blocked_reason = "Video generation was submitted; continue this task to refresh provider status."
        else:
            advance_offline_preparation(task)
        task.updated_at = now_iso()
        return task

    status_index = next(
        (
            index
            for index, item in enumerate(task.plan.actions)
            if item.action == "check_video_task_status" and item.status != "COMPLETED"
        ),
        -1,
    )
    if status_index < 0 or any(item.status != "COMPLETED" for item in task.plan.actions[:status_index]):
        return task
    if not authorization_allows(authorization, "check_video_task_status"):
        task.status = "BLOCKED_AUTHORIZATION"
        task.blocked_reason = "The task authorization expired before video status recovery completed."
        return task
    submit_output = _latest_capability_output(task, "submit_video_generation_task")
    remote_task_id = _video_task_id(submit_output)
    if not remote_task_id:
        task.status = "FAILED_FINAL"
        task.blocked_reason = "The submitted video task id is missing; provider status cannot be recovered."
        return task
    attempts = sum(
        1
        for item in task.result_descriptors
        if item.get("type") == "capability_result" and item.get("action") == "check_video_task_status"
    )
    try:
        result = command_bus().dispatch(
            CommandEnvelope(
                command="check_video_task_status",
                product_id=task.product_id,
                trace_id=f"trace-{task.task_id}",
                idempotency_key=f"{task.task_id}:check_video_task_status:{attempts + 1}",
                confirmed=True,
                payload={
                    "product_id": task.product_id,
                    "task_id": remote_task_id,
                    "provider": _provider_for(task, "video"),
                    "download": True,
                },
            )
        )
    except Exception as exc:
        task.status = "FAILED_RETRYABLE"
        task.blocked_reason = f"check_video_task_status failed: {type(exc).__name__}: {exc}"
        task.updated_at = now_iso()
        return task
    if not result.success:
        task.status = "FAILED_RETRYABLE" if result.retryable else "FAILED_FINAL"
        task.blocked_reason = result.error_message or "Video provider status check failed."
        task.updated_at = now_iso()
        return task
    _record_capability_result(task, "check_video_task_status", result)
    normalized_status = str(
        result.output.get("normalized_status")
        or (result.output.get("status") or {}).get("normalized_status")
        or ""
    ).lower()
    if normalized_status == "completed" and (
        result.output.get("result_id") or (result.output.get("result") or {}).get("result_id")
    ):
        task.plan.actions[status_index].status = "COMPLETED"
        task.blocked_reason = ""
        advance_offline_preparation(task)
    elif normalized_status in {"failed", "cancelled", "canceled"}:
        task.plan.actions[status_index].status = "FAILED"
        task.status = "FAILED_FINAL"
        task.blocked_reason = f"Video provider reached terminal status: {normalized_status}."
    else:
        task.status = "GENERATING"
        task.current_stage = "GENERATING"
        task.blocked_reason = f"Video provider status is {normalized_status or 'pending'}; continue this task later."
    task.updated_at = now_iso()
    return task


def _reconcile_external_research(task: CreativeTaskRecord) -> bool:
    pending = next(
        (
            step
            for step in task.plan.actions
            if step.action == "collect_external_source_snapshot" and step.status != "COMPLETED"
        ),
        None,
    )
    if pending is None:
        return True
    snapshots = [
        item
        for item in artifacts().list(task.product_id, "external_source_snapshots")
        if str(item.get("created_at") or "") >= task.created_at
        and item.get("not_product_fact") is True
    ]
    if not snapshots:
        return False
    snapshots.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("snapshot_id") or "")))
    snapshot = snapshots[-1]
    pending.status = "COMPLETED"
    task.result_descriptors.append(
        {
            "type": "capability_result",
            "action": "collect_external_source_snapshot",
            "status": "succeeded",
            "output": {
                "snapshot_id": snapshot.get("snapshot_id", ""),
                "status": snapshot.get("status", ""),
                "not_product_fact": True,
                "external_collection_performed": snapshot.get("external_collection_performed", False),
            },
        }
    )
    task.blocked_reason = ""
    return True


def _degrade_external_research(task: CreativeTaskRecord, message: str) -> bool:
    normalized = (message or "").strip()
    failed = any(marker in normalized for marker in ("搜索失败", "抓取失败", "都失败", "无法搜索", "登录失效", "限流"))
    opted_out = any(marker in normalized for marker in ("不使用实时", "跳过实时", "不用实时", "使用已有"))
    if not (failed and opted_out):
        return False
    for step in task.plan.actions:
        if step.action in {
            "collect_external_source_snapshot",
            "create_inspiration_candidates",
            "create_inspiration_pack",
        }:
            step.status = "COMPLETED"
    task.selected_idea = {
        "source": "confirmed_product_brain_and_historical_context",
        "freshness": "not_realtime",
        "goal": _effective_goal(task),
    }
    task.result_descriptors.append(
        {
            "type": "research_fallback",
            "status": "degraded",
            "reason": normalized,
            "used_realtime_information": False,
            "product_brain_writeback": False,
            "created_at": now_iso(),
        }
    )
    task.blocked_reason = ""
    return True


def _latest_generated_result(task: CreativeTaskRecord) -> tuple[str, str]:
    for item in reversed(task.result_descriptors):
        if item.get("type") != "capability_result":
            continue
        action = str(item.get("action") or "")
        output = item.get("output") if isinstance(item.get("output"), dict) else {}
        if action == "submit_video_generation_task" and output.get("result_id"):
            return "video", str(output["result_id"])
        if action == "check_video_task_status":
            result = output.get("result") if isinstance(output.get("result"), dict) else {}
            result_id = output.get("result_id") or result.get("result_id")
            if result_id:
                return "video", str(result_id)
        if action == "compose_exact_main_video" and output.get("result_id"):
            return "video", str(output["result_id"])
        if action == "submit_image_generation_job":
            run = output.get("image_generation_run") if isinstance(output.get("image_generation_run"), dict) else {}
            jobs = run.get("jobs") if isinstance(run.get("jobs"), list) else []
            if jobs and isinstance(jobs[0], dict) and jobs[0].get("result_id"):
                return "image", str(jobs[0]["result_id"])
    return "", ""


def _is_long_term_feedback(message: str) -> bool:
    normalized = (message or "").strip()
    if any(marker in normalized for marker in ("不要长期", "不用记住", "别记住", "只改这一次", "仅这一次")):
        return False
    return any(marker in normalized for marker in ("以后", "今后", "长期", "记住", "每次", "都要"))


def _record_result_feedback_for_task(
    task: CreativeTaskRecord,
    message: str,
    *,
    allow_evolve: bool,
) -> dict:
    kind, result_id = _latest_generated_result(task)
    if not kind or not result_id:
        return {}
    action = "record_video_result_feedback" if kind == "video" else "record_image_result_feedback"
    result = command_bus().dispatch(
        CommandEnvelope(
            command=action,
            product_id=task.product_id,
            trace_id=f"trace-{task.task_id}",
            idempotency_key=f"{task.task_id}:{action}:{len(task.revision_messages)}:{allow_evolve}",
            payload={
                "product_id": task.product_id,
                "result_id": result_id,
                "note": message,
                "selected": True,
                "rating": 5 if allow_evolve else None,
                "allow_evolve": allow_evolve,
            },
        )
    )
    if not result.success:
        raise RuntimeError(result.error_message or "result feedback could not be recorded")
    _record_capability_result(task, action, result)
    return dict(result.output)


def _reset_for_task_revision(task: CreativeTaskRecord, message: str) -> None:
    task.revision_messages.append(message)
    task.result_descriptors.append(
        {
            "type": "task_revision",
            "revision": len(task.revision_messages),
            "scope": "current_task",
            "message": message,
            "created_at": now_iso(),
            "original_goal_preserved": True,
            "product_brain_writeback": False,
        }
    )
    preserved = {
        "collect_external_source_snapshot",
        "create_inspiration_candidates",
        "create_inspiration_pack",
    }
    for step in task.plan.actions:
        if step.action not in preserved:
            step.status = "PENDING"
    task.completed_stages = [stage for stage in task.completed_stages if stage == "RESEARCHING"]
    task.authorization_request_id = ""
    task.authorization_id = ""
    task.status = "READY"
    task.current_stage = "IDEATING"
    task.blocked_reason = ""
    _ensure_authorization_request(task)
    advance_offline_preparation(task)


def start_creative_task(
    product_id: str,
    message: str,
    *,
    autonomy_mode: str = "",
    provider: str = "",
) -> CreativeTaskRecord:
    base = ensure_product(product_id)
    request = CreativeTaskRequest.from_message(message)
    if autonomy_mode:
        request.autonomy_mode = autonomy_mode
    task_id = f"task-{uuid.uuid4().hex}"
    readiness = assess_product_readiness(base.name, request, task_id=task_id)
    now = now_iso()
    path = base / "artifacts" / "creative_tasks" / f"{task_id}.json"
    task = CreativeTaskRecord(
        task_id=task_id,
        product_id=base.name,
        created_at=now,
        updated_at=now,
        status="READY" if readiness.ready else "NEEDS_INPUT",
        current_stage="UNDERSTANDING",
        request=request,
        readiness=readiness,
        plan=CreativeTaskPlan(
            task_id=task_id,
            stages=_plan_stages(request),
            actions=GoalPlanner().creative_task_actions(request),
        ),
        questions=list(readiness.questions),
        blocked_reason="" if readiness.ready else "Product knowledge is incomplete for this task.",
        provider=provider or (
            "volcengine-ark-video" if "video" in request.deliverables else "volcengine-ark-image"
        ),
        artifact_path=str(path),
    )
    _ensure_authorization_request(task)
    if task.readiness.ready:
        advance_offline_preparation(task)
    write_json(path, task.model_dump(mode="json"))
    return task


def load_creative_task(product_id: str, task_id: str) -> CreativeTaskRecord:
    base = ensure_product(product_id)
    path = base / "artifacts" / "creative_tasks" / f"{task_id}.json"
    payload = read_json(path, {})
    if not payload:
        payload = artifacts().get(base.name, task_id)
    if not payload:
        raise FileNotFoundError(f"creative task '{task_id}' does not exist for product '{base.name}'")
    task = CreativeTaskRecord.model_validate(payload)
    if task.product_id != base.name:
        raise ValueError("creative task belongs to a different product workspace")
    return task


def _discovery_artifact_id(task_id: str) -> str:
    return f"discovery-{task_id}"


def _discovery_path(product_id: str, task_id: str) -> Path:
    return (
        ensure_product(product_id)
        / "artifacts"
        / "discovery_sessions"
        / f"{_discovery_artifact_id(task_id)}.json"
    )


def load_discovery_session(product_id: str, task_id: str) -> DiscoverySessionRecord:
    base = ensure_product(product_id)
    payload = read_json(_discovery_path(base.name, task_id), {})
    if not payload:
        payload = artifacts().get(base.name, _discovery_artifact_id(task_id))
    if not payload:
        raise FileNotFoundError(f"discovery session for task '{task_id}' does not exist")
    session = DiscoverySessionRecord.model_validate(payload)
    if session.product_id != base.name:
        raise ValueError("discovery session belongs to a different product workspace")
    return session


def _load_or_start_discovery_session(task: CreativeTaskRecord) -> DiscoverySessionRecord:
    try:
        return load_discovery_session(task.product_id, task.task_id)
    except FileNotFoundError:
        now = now_iso()
        path = _discovery_path(task.product_id, task.task_id)
        return DiscoverySessionRecord(
            task_id=task.task_id,
            product_id=task.product_id,
            created_at=now,
            updated_at=now,
            artifact_path=str(path),
        )


def _recheck_blocked_product_preparation(task: CreativeTaskRecord) -> CreativeTaskRecord:
    """Re-run only local preparation after a product prerequisite changes."""

    paid_actions = {"submit_image_generation_job", "submit_video_generation_task"}
    if any(
        step.action in paid_actions and step.status == "COMPLETED"
        for step in task.plan.actions
    ):
        return task
    start_index = next(
        (
            index
            for index, step in enumerate(task.plan.actions)
            if step.action
            in {"prepare_task_material_pack", "resolve_image_intent", "resolve_video_intent"}
        ),
        -1,
    )
    if start_index < 0:
        return task
    for step in task.plan.actions[start_index:]:
        step.status = "PENDING"
    task.status = "READY"
    task.current_stage = task.plan.actions[start_index].stage
    task.blocked_reason = ""
    advance_offline_preparation(task)
    execute_authorized_live_generation(task)
    return task


def _retry_failed_local_delivery(task: CreativeTaskRecord) -> bool:
    """Retry post-generation local delivery without reopening paid actions."""

    if task.status != "FAILED_FINAL":
        return False
    failed_indexes = [
        index for index, step in enumerate(task.plan.actions) if step.status == "FAILED"
    ]
    if not failed_indexes or any(task.plan.actions[index].stage != "DELIVERING" for index in failed_indexes):
        return False
    paid_actions = {"submit_image_generation_job", "submit_video_generation_task"}
    paid_steps = [step for step in task.plan.actions if step.action in paid_actions]
    if not paid_steps or any(step.status != "COMPLETED" for step in paid_steps):
        return False
    first_failed = min(failed_indexes)
    if any(step.status != "COMPLETED" for step in task.plan.actions[:first_failed]):
        return False
    for step in task.plan.actions[first_failed:]:
        if step.stage == "DELIVERING" and step.status in {"FAILED", "PENDING"}:
            step.status = "PENDING"
    task.status = "READY"
    task.current_stage = "DELIVERING"
    task.blocked_reason = ""
    advance_offline_preparation(task)
    return True


def _apply_task_constraint_revision(task: CreativeTaskRecord, message: str) -> bool:
    """Replan an unapproved task when the user adds a stricter packaging constraint."""

    normalized = (message or "").strip()
    if not normalized or task.authorization_id or task.request.preserve_exact_packaging:
        return False
    combined = CreativeTaskRequest.from_message(f"{task.request.raw_message}\n{normalized}")
    if not combined.preserve_exact_packaging:
        return False
    task.revision_messages.append(normalized)
    task.result_descriptors.append(
        {
            "type": "task_plan_revision",
            "revision": len(task.revision_messages),
            "reason": "stricter_exact_packaging_constraint",
            "message": normalized,
            "original_goal_preserved": True,
            "created_at": now_iso(),
        }
    )
    task.request.preserve_exact_packaging = True
    _replan_task(task)
    task.readiness = assess_product_readiness(
        task.product_id,
        task.request,
        task_id=task.task_id,
    )
    task.questions = list(task.readiness.questions)
    task.status = "READY" if task.readiness.ready else "NEEDS_INPUT"
    task.current_stage = "UNDERSTANDING"
    task.blocked_reason = "" if task.readiness.ready else "Product knowledge is incomplete for this task."
    _ensure_authorization_request(task)
    return True


def continue_creative_task(
    product_id: str,
    task_id: str,
    message: str,
    *,
    confirmed: bool = False,
    proposal_id: str = "",
    authorization_id: str = "",
) -> CreativeTaskRecord:
    task = load_creative_task(product_id, task_id)
    session = _load_or_start_discovery_session(task)
    if confirmed and (proposal_id or task.pending_proposal_id):
        selected_proposal = proposal_id or task.pending_proposal_id
        proposal_kind = task.pending_proposal_kind
        if not selected_proposal or selected_proposal != task.pending_proposal_id:
            raise ValueError("confirmation must reference the task's pending proposal")
        result = command_bus().dispatch(
            CommandEnvelope(
                command="apply_evolution_proposal",
                product_id=task.product_id,
                trace_id=f"trace-{task.task_id}",
                confirmed=True,
                payload={
                    "product_id": task.product_id,
                    "apply_id": selected_proposal,
                    "proposal_id": selected_proposal,
                },
            )
        )
        if not result.success:
            raise RuntimeError(result.error_message or "proposal confirmation failed")
        task.pending_proposal_id = ""
        task.pending_proposal_kind = ""
        if proposal_kind == "learning":
            task.status = "COMPLETED"
            task.current_stage = "COMPLETED"
            task.questions = []
            task.blocked_reason = ""
        else:
            task.readiness = assess_product_readiness(
                task.product_id,
                task.request,
                task_id=task.task_id,
            )
            task.questions = list(task.readiness.questions)
            task.status = "READY" if task.readiness.ready else "NEEDS_INPUT"
            task.blocked_reason = "" if task.readiness.ready else "Product knowledge is incomplete for this task."
            _ensure_authorization_request(task)
        task.result_descriptors.append(
            {
                "type": "product_brain_learning_confirmation" if proposal_kind == "learning" else "product_brain_field_confirmation",
                "proposal_id": selected_proposal,
                "status": "applied",
                "action_receipt": result.output.get("action_receipt", ""),
            }
        )
        session.turns.append(
            {
                "created_at": now_iso(),
                "message": (message or "").strip(),
                "field_key": "",
                "proposal_id": selected_proposal,
                "answer_status": "CONFIRMED",
            }
        )
        session.updated_at = now_iso()
        task.updated_at = session.updated_at
        write_json(_discovery_path(task.product_id, task.task_id), session.model_dump(mode="json"))
        task_path = Path(task.artifact_path) if task.artifact_path else (
            ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
        )
        write_json(task_path, task.model_dump(mode="json"))
        return task

    if (
        task.status == "BLOCKED_AUTHORIZATION"
        and not authorization_id
        and _apply_task_constraint_revision(task, message)
    ):
        if task.readiness.ready:
            advance_offline_preparation(task)
        task.updated_at = now_iso()
        task_path = Path(task.artifact_path) if task.artifact_path else (
            ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
        )
        write_json(task_path, task.model_dump(mode="json"))
        return task

    if authorization_id:
        if authorization_id == task.authorization_request_id:
            authorization = approve_task_authorization(
                task.product_id,
                task.task_id,
                authorization_id,
                confirmed=confirmed,
            )
        else:
            authorization = load_task_authorization(task.product_id, authorization_id)
        if authorization.task_id != task.task_id:
            raise ValueError("task authorization belongs to a different Creative Task")
        task.authorization_id = authorization.authorization_id
        task.updated_at = now_iso()
        task.result_descriptors.append(
            {
                "type": "task_authorization",
                "authorization_id": authorization.authorization_id,
                "status": authorization.status,
            }
        )
        advance_offline_preparation(task)
        execute_authorized_mock_generation(task)
        execute_authorized_live_generation(task)
        task_path = Path(task.artifact_path) if task.artifact_path else (
            ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
        )
        write_json(task_path, task.model_dump(mode="json"))
        return task
    if task.status == "BLOCKED_PRODUCT":
        _recheck_blocked_product_preparation(task)
        task.updated_at = now_iso()
        task_path = Path(task.artifact_path) if task.artifact_path else (
            ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
        )
        write_json(task_path, task.model_dump(mode="json"))
        return task
    if task.status == "FAILED_FINAL" and _retry_failed_local_delivery(task):
        task.updated_at = now_iso()
        task_path = Path(task.artifact_path) if task.artifact_path else (
            ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
        )
        write_json(task_path, task.model_dump(mode="json"))
        return task
    if task.status in {"READY", "GENERATING", "FAILED_RETRYABLE"} and task.authorization_id:
        execute_authorized_mock_generation(task)
        execute_authorized_live_generation(task)
        task_path = Path(task.artifact_path) if task.artifact_path else (
            ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
        )
        write_json(task_path, task.model_dump(mode="json"))
        return task
    if task.status == "RESEARCHING":
        reconciled = _reconcile_external_research(task)
        if not reconciled:
            reconciled = _degrade_external_research(task, message)
        if reconciled:
            advance_offline_preparation(task)
            execute_authorized_mock_generation(task)
            execute_authorized_live_generation(task)
        task.updated_at = now_iso()
        task_path = Path(task.artifact_path) if task.artifact_path else (
            ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
        )
        write_json(task_path, task.model_dump(mode="json"))
        return task

    if task.status == "AWAITING_FEEDBACK" and (message or "").strip():
        normalized_feedback = (message or "").strip()
        if _is_long_term_feedback(normalized_feedback):
            feedback = _record_result_feedback_for_task(
                task,
                normalized_feedback,
                allow_evolve=True,
            )
            if not feedback:
                raise ValueError("long-term learning currently requires a generated image or video result")
            proposal = command_bus().dispatch(
                CommandEnvelope(
                    command="create_evolution_proposal",
                    product_id=task.product_id,
                    trace_id=f"trace-{task.task_id}",
                    idempotency_key=f"{task.task_id}:learning-proposal:{feedback.get('feedback_id', '')}",
                    payload={
                        "product_id": task.product_id,
                        "source_feedback_id": feedback.get("feedback_id", ""),
                    },
                )
            )
            if not proposal.success:
                raise RuntimeError(proposal.error_message or "learning proposal could not be created")
            _record_capability_result(task, "create_evolution_proposal", proposal)
            task.pending_proposal_id = str(proposal.output.get("proposal_id") or "")
            task.pending_proposal_kind = "learning"
            task.status = "NEEDS_INPUT"
            task.current_stage = "AWAITING_FEEDBACK"
            task.blocked_reason = "A long-term learning proposal is waiting for explicit Product Brain confirmation."
            task.questions = [
                DiscoveryQuestion(
                    question_id=f"confirm-{task.pending_proposal_id}",
                    field_key="learning.feedback_preferences",
                    prompt="请审阅并确认是否将这条长期偏好写入 Product Brain。",
                    priority=0,
                    blocking=True,
                )
            ]
        else:
            _record_result_feedback_for_task(
                task,
                normalized_feedback,
                allow_evolve=False,
            )
            _reset_for_task_revision(task, normalized_feedback)
        task.updated_at = now_iso()
        task_path = Path(task.artifact_path) if task.artifact_path else (
            ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
        )
        write_json(task_path, task.model_dump(mode="json"))
        return task

    if task.pending_proposal_id:
        raise ValueError("the pending field proposal must be confirmed or rejected before continuing discovery")
    prompt = task.questions[0] if task.questions else None
    normalized = (message or "").strip()
    unknown = any(marker in normalized for marker in ("不确定", "不知道", "暂不清楚", "不清楚"))
    field_key = prompt.field_key if prompt else ""
    answer_status = "UNKNOWN" if unknown else "PROVIDED"
    session.turns.append(
        {
            "created_at": now_iso(),
            "message": normalized,
            "field_key": field_key,
            "question_id": prompt.question_id if prompt else "",
            "answer_status": answer_status,
        }
    )
    if unknown and field_key:
        if field_key not in session.acknowledged_unknown_fields:
            session.acknowledged_unknown_fields.append(field_key)
        task.questions = [item for item in task.questions if item.field_key != field_key]
        task.blocked_reason = (
            f"{field_key} remains UNKNOWN. The task stays blocked where this field is required, "
            "but the same question will not be repeated in this discovery turn."
        )
    elif prompt and normalized and field_key == "delivery_spec":
        answer_request = CreativeTaskRequest.from_message(normalized)
        if not answer_request.deliverables:
            task.blocked_reason = "The requested delivery type is still unclear; please say text, image, video, or a combination."
        else:
            task.request.deliverables = list(answer_request.deliverables)
            task.request.goal_kind = "creative"
            _replan_task(task)
            task.readiness = assess_product_readiness(
                task.product_id,
                task.request,
                task_id=task.task_id,
            )
            task.questions = list(task.readiness.questions)
            task.status = "READY" if task.readiness.ready else "NEEDS_INPUT"
            task.blocked_reason = "" if task.readiness.ready else "Product knowledge is incomplete for this task."
            session.turns[-1]["answer_status"] = "TASK_CONTEXT_UPDATED"
            _ensure_authorization_request(task)
            advance_offline_preparation(task)
    elif prompt and normalized and field_key == "current_packaging":
        # A text answer cannot prove package identity or image fidelity. Keep
        # the task safely blocked and direct Hermes to the existing material
        # registration flow instead of turning prose into a canonical fact.
        task.status = "NEEDS_INPUT"
        task.blocked_reason = (
            "Current packaging requires an actual registered material. "
            "Please upload/register the current main image as current_main_image, "
            "video_first_frame, or product_photo, then continue this task."
        )
        task.questions = [
            DiscoveryQuestion(
                question_id=prompt.question_id,
                field_key="current_packaging",
                prompt="请上传或登记当前包装/商品主图，并明确哪张是当前商品主体。",
                priority=prompt.priority,
                blocking=True,
            )
        ]
        session.turns[-1]["answer_status"] = "MATERIAL_REQUIRED"
    elif prompt and normalized:
        proposal = create_field_confirmation_proposal(
            task.product_id,
            task.task_id,
            field_key,
            normalized,
        )
        task.pending_proposal_id = str(proposal["proposal_id"])
        task.pending_proposal_kind = "discovery"
        task.questions = [
            DiscoveryQuestion(
                question_id=f"confirm-{proposal['proposal_id']}",
                field_key=field_key,
                prompt=f"请确认是否将这项理解写入 Product Brain：{proposal['updates']}",
                priority=0,
                blocking=True,
            )
        ]
        task.blocked_reason = "A field-level Product Brain proposal is waiting for explicit confirmation."
        session.turns[-1]["answer_status"] = "PROPOSED"
        session.turns[-1]["proposal_id"] = proposal["proposal_id"]
    session.updated_at = now_iso()
    task.updated_at = session.updated_at
    write_json(_discovery_path(task.product_id, task.task_id), session.model_dump(mode="json"))
    task_path = Path(task.artifact_path) if task.artifact_path else (
        ensure_product(task.product_id) / "artifacts" / "creative_tasks" / f"{task.task_id}.json"
    )
    write_json(task_path, task.model_dump(mode="json"))
    return task
