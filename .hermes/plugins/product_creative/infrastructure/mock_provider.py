"""Deterministic provider gateway for runtime and recovery tests."""

from __future__ import annotations

import hashlib
import json
from typing import Dict

from ..ports.provider import ProviderRequest, ProviderResponse
from ..common import now_iso
from .sqlite.database import SqliteDatabase, runtime_database


class MockProviderGateway:
    def __init__(self, database: SqliteDatabase | None = None):
        self.calls: Dict[str, int] = {}
        self._database = database or runtime_database()

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        failure = str(request.payload.get("inject_failure") or "")
        if failure == "timeout":
            raise TimeoutError("injected mock provider timeout")
        if failure == "permanent":
            raise ValueError("injected mock provider rejection")
        digest = hashlib.sha256(request.idempotency_key.encode("utf-8")).hexdigest()[:16]
        external_task_id = f"mock-{digest}"
        payload = {
            "success": True,
            "provider": request.provider,
            "kind": request.kind,
            "mock": True,
            "result_id": f"mock-result-{digest}",
        }
        with self._database.transaction() as connection:
            existing = connection.execute(
                "SELECT response_json, external_task_id FROM mock_provider_effects WHERE idempotency_key=?",
                (request.idempotency_key,),
            ).fetchone()
            if existing is not None:
                return ProviderResponse(
                    status="completed",
                    external_task_id=existing["external_task_id"],
                    payload=json.loads(existing["response_json"]),
                )
            connection.execute(
                """
                INSERT INTO mock_provider_effects(
                    idempotency_key, provider, kind, response_json, external_task_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request.idempotency_key,
                    request.provider,
                    request.kind,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    external_task_id,
                    now_iso(),
                ),
            )
            self.calls[request.idempotency_key] = self.calls.get(request.idempotency_key, 0) + 1
        return ProviderResponse(status="completed", external_task_id=external_task_id, payload=payload)
