"""Durable SQLite repositories for workflows and command receipts."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ...common import now_iso
from ...contracts.models import IntentDecision, WorkflowInstance, WorkflowStatus, WorkflowStep
from .database import SqliteDatabase, runtime_database


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _object(value: str | None) -> Dict[str, Any]:
    if not value:
        return {}
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("SQLite JSON payload must be an object")
    return payload


class OptimisticVersionConflict(RuntimeError):
    pass


class SqliteWorkflowRepository:
    def __init__(self, product_root: Path | None = None, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()
        self._product_root = product_root.resolve() if product_root else None

    @property
    def database(self) -> SqliteDatabase:
        return self._database

    def _save_in_connection(self, connection, instance: WorkflowInstance) -> int:
        workspace = str(self._product_root or "")
        connection.execute(
            """
            INSERT INTO products(product_id, workspace_path, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                workspace_path=CASE WHEN excluded.workspace_path != '' THEN excluded.workspace_path ELSE products.workspace_path END,
                updated_at=excluded.updated_at,
                version=products.version + 1
            """,
            (instance.product_id, workspace, instance.created_at, instance.updated_at),
        )
        existing = connection.execute(
            "SELECT version FROM workflow_instances WHERE workflow_id=?",
            (instance.workflow_id,),
        ).fetchone()
        values = (
            instance.status.value,
            instance.current_step,
            _json(instance.intent.model_dump(mode="json")),
            instance.pause_reason,
            instance.updated_at,
        )
        if existing is None:
            connection.execute(
                """
                INSERT INTO workflow_instances(
                    workflow_id, product_id, definition, definition_version, trace_id, status,
                    current_step, intent_json, pause_reason, created_at, updated_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    instance.workflow_id,
                    instance.product_id,
                    instance.definition,
                    instance.definition_version,
                    instance.trace_id,
                    *values[:4],
                    instance.created_at,
                    instance.updated_at,
                ),
            )
            new_version = 1
        else:
            expected = int(instance.version)
            cursor = connection.execute(
                """
                UPDATE workflow_instances
                SET status=?, current_step=?, intent_json=?, pause_reason=?, updated_at=?, version=version+1
                WHERE workflow_id=? AND version=?
                """,
                (*values, instance.workflow_id, expected),
            )
            if cursor.rowcount != 1:
                actual = int(existing["version"])
                raise OptimisticVersionConflict(
                    f"workflow '{instance.workflow_id}' expected version {expected}, actual {actual}"
                )
            new_version = expected + 1
        for position, step in enumerate(instance.steps):
            connection.execute(
                """
                INSERT INTO workflow_steps(
                    workflow_id, position, step_id, action, status, args_json, output_json,
                    attempt, idempotency_key, pause_reason, error_code, error_message,
                    started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workflow_id, position) DO UPDATE SET
                    step_id=excluded.step_id,
                    action=excluded.action,
                    status=excluded.status,
                    args_json=excluded.args_json,
                    output_json=excluded.output_json,
                    attempt=excluded.attempt,
                    idempotency_key=excluded.idempotency_key,
                    pause_reason=excluded.pause_reason,
                    error_code=excluded.error_code,
                    error_message=excluded.error_message,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at
                """,
                (
                    instance.workflow_id,
                    position,
                    step.step_id,
                    step.action,
                    step.status.value,
                    _json(step.args),
                    _json(step.output),
                    step.attempt,
                    step.idempotency_key,
                    step.pause_reason,
                    step.error_code,
                    step.error_message,
                    step.started_at or None,
                    step.completed_at or None,
                ),
            )
        return new_version

    def save(self, instance: WorkflowInstance) -> str:
        with self._database.transaction() as connection:
            new_version = self._save_in_connection(connection, instance)
        instance.version = new_version
        return f"sqlite:///{self._database.path}#workflow/{instance.workflow_id}"

    def save_with_event(self, instance: WorkflowInstance, event: Dict[str, object]) -> str:
        with self._database.transaction() as connection:
            new_version = self._save_in_connection(connection, instance)
            self._append_event_in_connection(connection, event)
        instance.version = new_version
        return f"sqlite:///{self._database.path}#workflow/{instance.workflow_id}"

    def _load(self, connection, workflow_id: str) -> WorkflowInstance | None:
        row = connection.execute("SELECT * FROM workflow_instances WHERE workflow_id = ?", (workflow_id,)).fetchone()
        if row is None:
            return None
        step_rows = connection.execute(
            "SELECT * FROM workflow_steps WHERE workflow_id = ? ORDER BY position", (workflow_id,)
        ).fetchall()
        steps = [
            WorkflowStep(
                step_id=item["step_id"],
                action=item["action"],
                status=item["status"],
                args=_object(item["args_json"]),
                output=_object(item["output_json"]),
                attempt=item["attempt"],
                idempotency_key=item["idempotency_key"],
                pause_reason=item["pause_reason"],
                error_code=item["error_code"],
                error_message=item["error_message"],
                started_at=item["started_at"] or "",
                completed_at=item["completed_at"] or "",
            )
            for item in step_rows
        ]
        return WorkflowInstance(
            workflow_id=row["workflow_id"],
            definition=row["definition"],
            definition_version=row["definition_version"],
            product_id=row["product_id"],
            trace_id=row["trace_id"],
            status=row["status"],
            intent=IntentDecision.model_validate(_object(row["intent_json"])),
            steps=steps,
            current_step=row["current_step"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            pause_reason=row["pause_reason"],
            version=row["version"],
        )

    def get(self, workflow_id: str) -> WorkflowInstance | None:
        with self._database.read_session() as connection:
            return self._load(connection, workflow_id)

    def list(self, product_id: str = "") -> List[WorkflowInstance]:
        with self._database.read_session() as connection:
            if product_id:
                rows = connection.execute(
                    "SELECT workflow_id FROM workflow_instances WHERE product_id = ? ORDER BY updated_at, workflow_id",
                    (product_id,),
                ).fetchall()
            else:
                rows = connection.execute("SELECT workflow_id FROM workflow_instances ORDER BY updated_at, workflow_id").fetchall()
            return [item for row in rows if (item := self._load(connection, row["workflow_id"])) is not None]

    def latest_active(self, definition: str = "", product_id: str = "") -> WorkflowInstance | None:
        statuses = ("created", "running", "paused")
        matches = [
            item
            for item in self.list(product_id)
            if item.status.value in statuses and (not definition or item.definition == definition)
        ]
        return matches[-1] if matches else None

    def _append_event_in_connection(self, connection, event: Dict[str, object]) -> None:
        workflow_id = str(event.get("workflow_id") or "")
        if not workflow_id:
            raise ValueError("workflow event requires workflow_id")
        sequence = int(
            connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS value FROM workflow_events WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()["value"]
        )
        connection.execute(
            """
            INSERT INTO workflow_events(
                event_id, workflow_id, sequence, product_id, trace_id, event_type, action, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.get("event_id") or f"workflow-event-{uuid.uuid4().hex}"),
                workflow_id,
                sequence,
                str(event.get("product_id") or ""),
                str(event.get("trace_id") or ""),
                str(event.get("event_type") or "workflow_event"),
                str(event.get("action") or ""),
                _json(event),
                str(event.get("created_at") or now_iso()),
            ),
        )

    def append_event(self, event: Dict[str, object]) -> None:
        with self._database.transaction() as connection:
            self._append_event_in_connection(connection, event)

    def acquire_lease(self, workflow_id: str, owner: str, ttl_seconds: int = 30) -> bool:
        expires = time.time() + max(1, ttl_seconds)
        with self._database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE workflow_instances
                SET lease_owner = ?, lease_expires_at = ?, updated_at = ?
                WHERE workflow_id = ?
                  AND (lease_owner IS NULL OR lease_expires_at < ? OR lease_owner = ?)
                """,
                (owner, expires, now_iso(), workflow_id, time.time(), owner),
            )
            return cursor.rowcount == 1

    def acquire_product_lease(self, product_id: str, owner: str, ttl_seconds: int = 30) -> bool:
        now_epoch = time.time()
        expires = now_epoch + max(1, ttl_seconds)
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO product_leases(product_id, lease_owner, lease_expires_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(product_id) DO UPDATE SET
                    lease_owner=excluded.lease_owner,
                    lease_expires_at=excluded.lease_expires_at,
                    updated_at=excluded.updated_at
                WHERE product_leases.lease_expires_at < ? OR product_leases.lease_owner = ?
                """,
                (product_id, owner, expires, now_iso(), now_epoch, owner),
            )
            row = connection.execute(
                "SELECT lease_owner FROM product_leases WHERE product_id=?",
                (product_id,),
            ).fetchone()
            return row is not None and row["lease_owner"] == owner

    def release_lease(self, workflow_id: str, owner: str) -> None:
        with self._database.transaction() as connection:
            connection.execute(
                "UPDATE workflow_instances SET lease_owner=NULL, lease_expires_at=NULL WHERE workflow_id=? AND lease_owner=?",
                (workflow_id, owner),
            )

    def release_product_lease(self, product_id: str, owner: str) -> None:
        with self._database.transaction() as connection:
            connection.execute(
                "DELETE FROM product_leases WHERE product_id=? AND lease_owner=?",
                (product_id, owner),
            )


class SqliteActionReceiptRepository:
    def __init__(self, product_root: Path | str | None = None, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()
        self._product_id = product_root.resolve().name if isinstance(product_root, Path) else str(product_root or "")

    def key(self, action: str, values: Dict[str, Any]) -> str:
        canonical = _json({"product_id": self._product_id, "action": action, "values": values})
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, action: str, receipt_key: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            row = connection.execute(
                "SELECT * FROM command_receipts WHERE receipt_key=? AND action=?", (receipt_key, action)
            ).fetchone()
            if row is None:
                return {}
            return {
                "success": row["status"] == "completed",
                "status": row["status"],
                "action": row["action"],
                "receipt_key": row["receipt_key"],
                "result": _object(row["result_json"]),
                "error": _object(row["error_json"]),
                "receipt_path": f"sqlite:///{self._database.path}#receipt/{receipt_key}",
            }

    def begin(self, action: str, receipt_key: str, values: Dict[str, Any]) -> str:
        now = now_iso()
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO command_receipts(
                    receipt_key, product_id, action, status, idempotency_values_json, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
                ON CONFLICT(receipt_key) DO NOTHING
                """,
                (receipt_key, self._product_id, action, _json(values), now, now),
            )
        return f"sqlite:///{self._database.path}#receipt/{receipt_key}"

    def claim(self, action: str, receipt_key: str, values: Dict[str, Any], stale_after_seconds: int = 30) -> Dict[str, Any]:
        now = now_iso()
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM command_receipts WHERE receipt_key=? AND action=?",
                (receipt_key, action),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO command_receipts(
                        receipt_key, product_id, action, status, idempotency_values_json, created_at, updated_at
                    ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
                    """,
                    (receipt_key, self._product_id, action, _json(values), now, now),
                )
                return {"claimed": True, "status": "pending"}
            if row["status"] == "failed":
                connection.execute(
                    "UPDATE command_receipts SET status='pending', error_json='{}', updated_at=? WHERE receipt_key=?",
                    (now, receipt_key),
                )
                return {"claimed": True, "status": "pending", "retry": True}
            if row["status"] == "pending":
                try:
                    updated_at = datetime.fromisoformat(str(row["updated_at"]).replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - updated_at.astimezone(timezone.utc)).total_seconds()
                except (TypeError, ValueError):
                    age = float("inf")
                if age >= max(1, int(stale_after_seconds)):
                    connection.execute(
                        "UPDATE command_receipts SET updated_at=?, error_json='{}' WHERE receipt_key=?",
                        (now, receipt_key),
                    )
                    return {"claimed": True, "status": "pending", "retry": True, "recovered": True}
            return {
                "claimed": False,
                "status": row["status"],
                "result": _object(row["result_json"]),
                "receipt_path": f"sqlite:///{self._database.path}#receipt/{receipt_key}",
            }

    def save(self, action: str, receipt_key: str, payload: Dict[str, Any]) -> str:
        now = now_iso()
        values = payload.get("idempotency_values") if isinstance(payload.get("idempotency_values"), dict) else {}
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO command_receipts(
                    receipt_key, product_id, action, status, idempotency_values_json, result_json, created_at, updated_at
                ) VALUES (?, ?, ?, 'completed', ?, ?, ?, ?)
                ON CONFLICT(receipt_key) DO UPDATE SET
                    status='completed', result_json=excluded.result_json, error_json='{}', updated_at=excluded.updated_at
                """,
                (receipt_key, self._product_id, action, _json(values), _json(payload.get("result") or {}), now, now),
            )
        return f"sqlite:///{self._database.path}#receipt/{receipt_key}"

    def fail(self, action: str, receipt_key: str, error: Dict[str, Any]) -> None:
        with self._database.transaction() as connection:
            connection.execute(
                "UPDATE command_receipts SET status='failed', error_json=?, updated_at=? WHERE receipt_key=? AND action=?",
                (_json(error), now_iso(), receipt_key, action),
            )


class SqliteOutboxRepository:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def enqueue(
        self,
        *,
        product_id: str,
        topic: str,
        idempotency_key: str,
        payload: Dict[str, Any],
        workflow_id: str = "",
        step_id: str = "",
        connection=None,
    ) -> str:
        outbox_id = f"outbox-{uuid.uuid4().hex}"
        now = now_iso()
        values = (
            outbox_id,
            product_id,
            workflow_id,
            step_id,
            topic,
            idempotency_key,
            _json(payload),
            time.time(),
            now,
            now,
        )

        def insert(current) -> None:
            current.execute(
                """
                INSERT INTO outbox_events(
                    outbox_id, product_id, workflow_id, step_id, topic,
                    idempotency_key, payload_json, available_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic, idempotency_key) DO NOTHING
                """,
                values,
            )

        if connection is not None:
            insert(connection)
            row = connection.execute(
                "SELECT outbox_id FROM outbox_events WHERE topic=? AND idempotency_key=?",
                (topic, idempotency_key),
            ).fetchone()
        else:
            with self._database.transaction() as current:
                insert(current)
                row = current.execute(
                    "SELECT outbox_id FROM outbox_events WHERE topic=? AND idempotency_key=?",
                    (topic, idempotency_key),
                ).fetchone()
        return str(row["outbox_id"])

    def claim(self, owner: str, lease_seconds: int = 30, outbox_id: str = "") -> Dict[str, Any]:
        now_epoch = time.time()
        expires = now_epoch + max(1, lease_seconds)
        with self._database.transaction() as connection:
            if outbox_id:
                row = connection.execute(
                    """
                    SELECT outbox_id FROM outbox_events
                    WHERE outbox_id=? AND status IN ('pending', 'retry')
                      AND available_at <= ?
                      AND (lease_owner IS NULL OR lease_expires_at < ?)
                    """,
                    (outbox_id, now_epoch, now_epoch),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT outbox_id FROM outbox_events
                    WHERE status IN ('pending', 'retry')
                      AND available_at <= ?
                      AND (lease_owner IS NULL OR lease_expires_at < ?)
                    ORDER BY created_at, outbox_id
                    LIMIT 1
                    """,
                    (now_epoch, now_epoch),
                ).fetchone()
            if row is None:
                return {}
            cursor = connection.execute(
                """
                UPDATE outbox_events
                SET status='processing', lease_owner=?, lease_expires_at=?,
                    attempt=attempt+1, updated_at=?
                WHERE outbox_id=?
                  AND status IN ('pending', 'retry')
                  AND (lease_owner IS NULL OR lease_expires_at < ?)
                """,
                (owner, expires, now_iso(), row["outbox_id"], now_epoch),
            )
            if cursor.rowcount != 1:
                return {}
            claimed = connection.execute(
                "SELECT * FROM outbox_events WHERE outbox_id=?",
                (row["outbox_id"],),
            ).fetchone()
            return self._payload(claimed)

    def complete(self, outbox_id: str, owner: str, result: Dict[str, Any]) -> bool:
        with self._database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE outbox_events
                SET status='completed', result_json=?, error_json='{}',
                    lease_owner=NULL, lease_expires_at=NULL, updated_at=?
                WHERE outbox_id=? AND status='processing' AND lease_owner=?
                """,
                (_json(result), now_iso(), outbox_id, owner),
            )
            return cursor.rowcount == 1

    def fail(
        self,
        outbox_id: str,
        owner: str,
        error: Dict[str, Any],
        *,
        retryable: bool,
        retry_delay_seconds: float = 0,
    ) -> bool:
        status = "retry" if retryable else "failed"
        with self._database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE outbox_events
                SET status=?, error_json=?, available_at=?, lease_owner=NULL,
                    lease_expires_at=NULL, updated_at=?
                WHERE outbox_id=? AND status='processing' AND lease_owner=?
                """,
                (
                    status,
                    _json(error),
                    time.time() + max(0.0, retry_delay_seconds),
                    now_iso(),
                    outbox_id,
                    owner,
                ),
            )
            return cursor.rowcount == 1

    def get(self, outbox_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            row = connection.execute(
                "SELECT * FROM outbox_events WHERE outbox_id=?", (outbox_id,)
            ).fetchone()
            return self._payload(row) if row is not None else {}

    @staticmethod
    def _payload(row) -> Dict[str, Any]:
        return {
            "outbox_id": row["outbox_id"],
            "product_id": row["product_id"],
            "workflow_id": row["workflow_id"],
            "step_id": row["step_id"],
            "topic": row["topic"],
            "idempotency_key": row["idempotency_key"],
            "payload": _object(row["payload_json"]),
            "status": row["status"],
            "attempt": row["attempt"],
            "result": _object(row["result_json"]),
            "error": _object(row["error_json"]),
        }


class SqliteProviderTaskRepository:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def record(
        self,
        *,
        product_id: str,
        provider: str,
        kind: str,
        idempotency_key: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
        status: str,
        workflow_id: str = "",
        step_id: str = "",
        external_task_id: str = "",
    ) -> Dict[str, Any]:
        task_id = f"provider-task-{uuid.uuid4().hex}"
        now = now_iso()
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO provider_tasks(
                    provider_task_id, product_id, workflow_id, step_id, provider, kind,
                    external_task_id, idempotency_key, status, request_json,
                    response_json, created_at, updated_at, attempt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(provider, idempotency_key) DO UPDATE SET
                    status=excluded.status,
                    response_json=excluded.response_json,
                    external_task_id=excluded.external_task_id,
                    updated_at=excluded.updated_at,
                    attempt=provider_tasks.attempt+1
                """,
                (
                    task_id,
                    product_id,
                    workflow_id,
                    step_id,
                    provider,
                    kind,
                    external_task_id,
                    idempotency_key,
                    status,
                    _json(request),
                    _json(response),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM provider_tasks WHERE provider=? AND idempotency_key=?",
                (provider, idempotency_key),
            ).fetchone()
        return {
            "provider_task_id": row["provider_task_id"],
            "provider": row["provider"],
            "kind": row["kind"],
            "status": row["status"],
            "response": _object(row["response_json"]),
            "attempt": row["attempt"],
        }

    def get(self, provider: str, idempotency_key: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            row = connection.execute(
                "SELECT * FROM provider_tasks WHERE provider=? AND idempotency_key=?",
                (provider, idempotency_key),
            ).fetchone()
            if row is None:
                return {}
            return {
                "provider_task_id": row["provider_task_id"],
                "provider": row["provider"],
                "kind": row["kind"],
                "status": row["status"],
                "response": _object(row["response_json"]),
                "attempt": row["attempt"],
            }
