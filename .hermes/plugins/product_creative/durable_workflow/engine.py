"""Execution-before-persistence workflow state machine."""

from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Any, Dict

from ..common import now_iso
from ..contracts.models import IntentDecision, WorkflowInstance, WorkflowStatus, WorkflowStep, WorkflowStepStatus
from ..ports.runtime_repositories import workflows
from ..runtime.workflow_catalog import WorkflowDefinition


@dataclass(frozen=True)
class DurableStepHandle:
    workflow_id: str
    step_id: str
    action: str
    product_id: str
    trace_id: str
    lease_owner: str
    runnable: bool
    idempotency_key: str


class DurableWorkflowEngine:
    def __init__(self, repository=None, lease_seconds: int = 30):
        self._repository = repository or workflows()
        self._lease_seconds = max(1, lease_seconds)

    def _resumable(self, product_id: str, action: str) -> WorkflowInstance | None:
        active = {WorkflowStatus.CREATED, WorkflowStatus.RUNNING, WorkflowStatus.PAUSED}
        for instance in reversed(self._repository.list(product_id)):
            if instance.status not in active or instance.current_step >= len(instance.steps):
                continue
            if instance.steps[instance.current_step].action == action:
                return instance
        return None

    def _new_instance(
        self,
        product_id: str,
        definition: WorkflowDefinition,
        decision: IntentDecision,
        trace_id: str,
    ) -> WorkflowInstance:
        workflow_id = f"workflow-{uuid.uuid4().hex}"
        now = now_iso()
        steps = [
            WorkflowStep(
                step_id=f"step-{uuid.uuid4().hex}",
                action=action,
                status=WorkflowStepStatus.PENDING,
                idempotency_key=f"{workflow_id}:{position}:{action}",
            )
            for position, action in enumerate(definition.actions_from(decision.action), 1)
        ]
        return WorkflowInstance(
            workflow_id=workflow_id,
            definition=definition.name,
            definition_version=definition.version,
            product_id=product_id,
            trace_id=trace_id,
            status=WorkflowStatus.CREATED,
            intent=decision,
            steps=steps,
            created_at=now,
            updated_at=now,
        )

    def begin_step(
        self,
        product_id: str,
        definition: WorkflowDefinition,
        decision: IntentDecision,
        args: Dict[str, Any],
        trace_id: str,
        runnable: bool,
        pause_reason: str = "",
    ) -> DurableStepHandle:
        owner = f"worker-{uuid.uuid4().hex}"
        if not self._repository.acquire_product_lease(product_id, owner, self._lease_seconds):
            raise RuntimeError(f"product '{product_id}' is leased by another worker")
        instance = self._resumable(product_id, decision.action)
        created = instance is None
        if instance is None:
            instance = self._new_instance(product_id, definition, decision, trace_id)
            self._repository.save_with_event(
                instance,
                {
                    "event_type": "workflow.created",
                    "workflow_id": instance.workflow_id,
                    "product_id": product_id,
                    "trace_id": trace_id,
                    "action": decision.action,
                    "definition": definition.name,
                    "created_at": instance.created_at,
                },
            )
        if instance.current_step >= len(instance.steps):
            raise RuntimeError(f"workflow '{instance.workflow_id}' has no current step")
        step = instance.steps[instance.current_step]
        if step.action != decision.action:
            raise RuntimeError(
                f"workflow '{instance.workflow_id}' expects '{step.action}', not '{decision.action}'"
            )
        instance.intent = decision
        step.args = dict(args)
        instance.updated_at = now_iso()
        if not runnable:
            if pause_reason == "blocked_for_confirmation":
                step.status = WorkflowStepStatus.WAITING_CONFIRMATION
            elif pause_reason == "waiting_for_user_input":
                step.status = WorkflowStepStatus.WAITING_INPUT
            else:
                step.status = WorkflowStepStatus.READY
            step.pause_reason = pause_reason or "not_runnable"
            instance.status = WorkflowStatus.PAUSED
            instance.pause_reason = step.pause_reason
            self._repository.save_with_event(
                instance,
                {
                    "event_type": "workflow.paused",
                    "workflow_id": instance.workflow_id,
                    "product_id": product_id,
                    "trace_id": instance.trace_id,
                    "action": step.action,
                    "pause_reason": step.pause_reason,
                    "created_at": instance.updated_at,
                },
            )
            self._repository.release_product_lease(product_id, owner)
            return DurableStepHandle(
                instance.workflow_id, step.step_id, step.action, product_id, instance.trace_id, "", False, step.idempotency_key
            )
        if not self._repository.acquire_lease(instance.workflow_id, owner, self._lease_seconds):
            self._repository.release_product_lease(product_id, owner)
            raise RuntimeError(f"workflow '{instance.workflow_id}' is leased by another worker")
        step.status = WorkflowStepStatus.RUNNING
        step.attempt += 1
        step.started_at = now_iso()
        step.completed_at = ""
        step.pause_reason = ""
        instance.status = WorkflowStatus.RUNNING
        instance.pause_reason = ""
        self._repository.save_with_event(
            instance,
            {
                "event_type": "workflow.step_started",
                "workflow_id": instance.workflow_id,
                "product_id": product_id,
                "trace_id": instance.trace_id,
                "action": step.action,
                "step_id": step.step_id,
                "attempt": step.attempt,
                "resumed": not created,
                "created_at": instance.updated_at,
            },
        )
        return DurableStepHandle(
            instance.workflow_id, step.step_id, step.action, product_id, instance.trace_id, owner, True, step.idempotency_key
        )

    def complete_step(
        self,
        handle: DurableStepHandle,
        output: Dict[str, Any],
        success: bool,
        error_code: str = "",
        error_message: str = "",
    ) -> Dict[str, Any]:
        instance = self._repository.get(handle.workflow_id)
        if instance is None or instance.current_step >= len(instance.steps):
            raise RuntimeError(f"workflow '{handle.workflow_id}' is not resumable")
        step = instance.steps[instance.current_step]
        if step.step_id != handle.step_id:
            raise RuntimeError(f"workflow '{handle.workflow_id}' step changed while executing")
        step.output = dict(output)
        instance.updated_at = now_iso()
        step.completed_at = instance.updated_at
        provider_status = str(output.get("normalized_status") or "").lower()
        if success and provider_status in {"queued", "pending", "processing", "running"}:
            step.status = WorkflowStepStatus.WAITING_PROVIDER
            step.pause_reason = "provider_processing"
            step.idempotency_key = f"{instance.workflow_id}:{step.step_id}:poll:{step.attempt + 1}:{uuid.uuid4().hex}"
            instance.status = WorkflowStatus.PAUSED
            instance.pause_reason = step.pause_reason
            event_type = "workflow.waiting_provider"
        elif success:
            step.status = WorkflowStepStatus.SUCCEEDED
            instance.current_step += 1
            if instance.current_step >= len(instance.steps):
                instance.status = WorkflowStatus.SUCCEEDED
                instance.pause_reason = ""
                event_type = "workflow.succeeded"
            else:
                instance.status = WorkflowStatus.PAUSED
                instance.pause_reason = "next_step_ready"
                instance.steps[instance.current_step].status = WorkflowStepStatus.READY
                event_type = "workflow.step_succeeded"
        else:
            step.status = WorkflowStepStatus.FAILED
            step.error_code = error_code or "ACTION_FAILED"
            step.error_message = error_message
            instance.status = WorkflowStatus.FAILED
            instance.pause_reason = "step_failed"
            event_type = "workflow.step_failed"
        self._repository.save_with_event(
            instance,
            {
                "event_type": event_type,
                "workflow_id": instance.workflow_id,
                "product_id": instance.product_id,
                "trace_id": instance.trace_id,
                "action": step.action,
                "step_id": step.step_id,
                "success": success,
                "provider_status": provider_status,
                "error_code": step.error_code,
                "created_at": instance.updated_at,
            },
        )
        if handle.lease_owner:
            self._repository.release_lease(instance.workflow_id, handle.lease_owner)
            self._repository.release_product_lease(instance.product_id, handle.lease_owner)
        return self.summary(instance)

    @staticmethod
    def summary(instance: WorkflowInstance) -> Dict[str, Any]:
        current = instance.steps[instance.current_step] if instance.current_step < len(instance.steps) else None
        return {
            "schema_version": "product_creative.workflow_instance.v2",
            "workflow_id": instance.workflow_id,
            "definition": instance.definition,
            "definition_version": instance.definition_version,
            "trace_id": instance.trace_id,
            "status": instance.status.value,
            "current_step": instance.current_step,
            "current_action": current.action if current else "",
            "pause_reason": instance.pause_reason,
            "path": f"sqlite://workflow/{instance.workflow_id}",
        }

    def summary_for(self, workflow_id: str) -> Dict[str, Any]:
        instance = self._repository.get(workflow_id)
        return self.summary(instance) if instance else {}


_ENGINE: DurableWorkflowEngine | None = None


def durable_workflow_engine() -> DurableWorkflowEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = DurableWorkflowEngine()
    return _ENGINE
