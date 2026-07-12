"""Durable provider dispatch adapter."""

from __future__ import annotations

from typing import Any, Dict

from ..ports.provider import ProviderRequest, ProviderResponse
from .outbox_worker import OutboxWorker
from .sqlite.repositories import SqliteOutboxRepository


class _Gateway:
    def __init__(self, execute, args: Dict[str, Any]):
        self._execute = execute
        self._args = dict(args)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        output = self._execute(dict(self._args))
        return ProviderResponse(
            status="completed" if output.get("success") else "failed",
            payload=output,
            external_task_id=str(output.get("video_task_id") or output.get("task_id") or output.get("image_run_id") or output.get("result_id") or ""),
        )


class DurableProviderDispatcher:
    def dispatch(self, *, command, descriptor, definition, receipt_key: str) -> Dict[str, Any]:
        idempotency_key = receipt_key or command.idempotency_key
        if not idempotency_key:
            raise ValueError("provider capability requires an idempotency key")
        outbox = SqliteOutboxRepository()
        outbox_id = outbox.enqueue(
            product_id=command.product_id, workflow_id=command.workflow_id, step_id=command.step_id,
            topic=f"provider.{command.action}", idempotency_key=idempotency_key,
            payload={"provider": str(command.args.get("provider") or "mock"), "kind": descriptor.domain,
                     "command": command.action, "command_args": dict(command.args)},
        )
        current = outbox.get(outbox_id)
        if current.get("status") != "completed":
            delivery = OutboxWorker(_Gateway(definition.execute, command.args), outbox).run_once(outbox_id)
            if not delivery.get("success"):
                return {"success": False, "error": delivery.get("error") or {"error_code": "OUTBOX_IN_PROGRESS", "retryable": True}, "outbox_id": outbox_id}
            current = outbox.get(outbox_id)
        task = current.get("result") if isinstance(current.get("result"), dict) else {}
        response = task.get("response") if isinstance(task.get("response"), dict) else {}
        return {**response, "outbox_id": outbox_id, "provider_task_id": task.get("provider_task_id", "")}
