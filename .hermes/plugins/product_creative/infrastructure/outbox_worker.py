"""Lease-based outbox delivery with provider idempotency recording."""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict

from ..ports.provider import ProviderRequest, ProviderTaskGateway
from .mock_provider import MockProviderGateway
from .sqlite.repositories import SqliteOutboxRepository, SqliteProviderTaskRepository


class OutboxWorker:
    def __init__(
        self,
        gateway: ProviderTaskGateway | None = None,
        outbox: SqliteOutboxRepository | None = None,
        tasks: SqliteProviderTaskRepository | None = None,
        owner: str = "",
        fault_injector: Callable[[str, Dict[str, Any]], None] | None = None,
    ):
        self._gateway = gateway or MockProviderGateway()
        self._outbox = outbox or SqliteOutboxRepository()
        self._tasks = tasks or SqliteProviderTaskRepository()
        self._owner = owner or f"outbox-worker-{uuid.uuid4().hex}"
        self._fault_injector = fault_injector

    def _inject(self, stage: str, payload: Dict[str, Any]) -> None:
        if self._fault_injector is not None:
            self._fault_injector(stage, payload)

    def run_once(self, outbox_id: str = "") -> Dict[str, Any]:
        message = self._outbox.claim(self._owner, outbox_id=outbox_id)
        if not message:
            return {"processed": False}
        self._inject("after_claim", message)
        payload = message["payload"]
        provider = str(payload.get("provider") or "mock")
        kind = str(payload.get("kind") or message["topic"])
        request = ProviderRequest(
            provider=provider,
            kind=kind,
            idempotency_key=message["idempotency_key"],
            payload=payload,
        )
        try:
            existing = self._tasks.get(provider, message["idempotency_key"])
            if existing:
                self._outbox.complete(message["outbox_id"], self._owner, existing)
                return {
                    "processed": True,
                    "success": True,
                    "outbox_id": message["outbox_id"],
                    "task": existing,
                    "recovered": True,
                }
            response = self._gateway.execute(request)
            self._inject("after_provider", {**message, "provider_response": response.payload})
            task = self._tasks.record(
                product_id=message["product_id"],
                provider=provider,
                kind=kind,
                idempotency_key=message["idempotency_key"],
                request=payload,
                response=response.payload,
                status=response.status,
                workflow_id=message["workflow_id"],
                step_id=message["step_id"],
                external_task_id=response.external_task_id,
            )
            self._inject("after_task_record", {**message, "task": task})
            self._inject("before_complete", {**message, "task": task})
            if not self._outbox.complete(message["outbox_id"], self._owner, task):
                raise RuntimeError("outbox lease was lost before completion")
            return {"processed": True, "success": True, "outbox_id": message["outbox_id"], "task": task}
        except Exception as exc:
            retryable = isinstance(exc, TimeoutError)
            error = {"type": type(exc).__name__, "message": str(exc), "retryable": retryable}
            self._outbox.fail(
                message["outbox_id"],
                self._owner,
                error,
                retryable=retryable,
            )
            return {"processed": True, "success": False, "outbox_id": message["outbox_id"], "error": error}
