"""SQLite implementation of the M9 review, audit, and recovery boundary."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from ..common import now_iso, products_root
from ..contracts.errors import OptimisticVersionConflict
from .sqlite.database import SqliteDatabase, runtime_database
from .sqlite.domain_repositories import SqliteProductBrainRepository
from .sqlite.repositories import _json, _object


class SqliteRecoveryRepository:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def request_confirmation(self, product_id: str, command: str, subject_id: str, risk: str, trace_id: str) -> str:
        confirmation_id = f"confirmation-{uuid.uuid4().hex}"
        now = now_iso()
        with self._database.transaction() as connection:
            connection.execute(
                """INSERT INTO confirmations(
                    confirmation_id, product_id, command, subject_id, risk_level, status,
                    trace_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
                (confirmation_id, product_id, command, subject_id, risk, trace_id, now, now),
            )
        return confirmation_id

    def record_confirmation(self, confirmation_id: str, *, decision: str, actor: str, reason: str,
                            expected_version: int | None, result: Dict[str, Any]) -> None:
        if not confirmation_id:
            return
        now = now_iso()
        with self._database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE confirmations SET status='decided', decision=?, actor=?, note=?,
                    expected_version=?, result_json=?, decided_at=?, updated_at=?
                    WHERE confirmation_id=? AND status='pending'""",
                (decision, actor, reason, expected_version, _json(result), now, now, confirmation_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("confirmation is missing or has already been decided")

    def reject_proposal(self, product_id: str, proposal_id: str, reason: str) -> Dict[str, Any]:
        now = now_iso()
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT status, payload_json FROM writeback_proposals WHERE product_id=? AND proposal_id=?",
                (product_id, proposal_id),
            ).fetchone()
            if row is None:
                raise KeyError(f"proposal '{proposal_id}' does not exist")
            if row["status"] == "applied":
                raise ValueError("an applied proposal cannot be rejected")
            payload = _object(row["payload_json"])
            payload.update({"status": "rejected", "rejected_at": now, "rejection_reason": reason})
            connection.execute(
                "UPDATE writeback_proposals SET status='rejected', payload_json=?, updated_at=? WHERE product_id=? AND proposal_id=?",
                (_json(payload), now, product_id, proposal_id),
            )
        return payload

    def rollback_brain(self, product_id: str, target_version: int, expected_version: int) -> Dict[str, Any]:
        return SqliteProductBrainRepository(self._database).rollback(product_id, target_version, expected_version)

    def revoke_rule(self, product_id: str, rule_id: str, reason: str) -> Dict[str, Any]:
        now = now_iso()
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT payload_json FROM rule_candidates WHERE product_id=? AND rule_id=?",
                (product_id, rule_id),
            ).fetchone()
            if row is None:
                raise KeyError(f"rule '{rule_id}' does not exist")
            payload = _object(row["payload_json"])
            if payload.get("status") == "revoked":
                return payload
            payload.update({"status": "revoked", "revoked_at": now, "revocation_reason": reason})
            connection.execute(
                "UPDATE rule_candidates SET status='revoked', payload_json=?, updated_at=? WHERE product_id=? AND rule_id=?",
                (_json(payload), now, product_id, rule_id),
            )
        return payload

    def recover_workflow(self, workflow_id: str, *, operation: str, expected_version: int) -> Dict[str, Any]:
        now = now_iso()
        with self._database.transaction() as connection:
            workflow = connection.execute("SELECT * FROM workflow_instances WHERE workflow_id=?", (workflow_id,)).fetchone()
            if workflow is None:
                raise KeyError(f"workflow '{workflow_id}' does not exist")
            if int(workflow["version"]) != expected_version:
                raise OptimisticVersionConflict(
                    f"Workflow '{workflow_id}' expected version {expected_version}, actual {workflow['version']}"
                )
            position = int(workflow["current_step"])
            step = connection.execute(
                "SELECT * FROM workflow_steps WHERE workflow_id=? AND position=?", (workflow_id, position)
            ).fetchone()
            if operation == "retry":
                if workflow["status"] not in {"failed", "paused"} or step is None or step["status"] not in {
                    "failed", "waiting_input", "waiting_confirmation", "waiting_provider"
                }:
                    raise ValueError("workflow is not in a retryable state")
                connection.execute(
                    """UPDATE workflow_steps SET status='ready', pause_reason='', error_code='', error_message='',
                        started_at=NULL, completed_at=NULL WHERE workflow_id=? AND position=?""",
                    (workflow_id, position),
                )
                status, event_type = "paused", "workflow.retry_requested"
            elif operation == "cancel":
                if workflow["status"] in {"succeeded", "cancelled"}:
                    raise ValueError("completed workflow cannot be cancelled")
                connection.execute(
                    "UPDATE workflow_steps SET status='cancelled', completed_at=? WHERE workflow_id=? AND status NOT IN ('succeeded','cancelled')",
                    (now, workflow_id),
                )
                status, event_type = "cancelled", "workflow.cancelled"
            else:
                raise ValueError("unsupported workflow recovery operation")
            new_version = expected_version + 1
            connection.execute(
                """UPDATE workflow_instances SET status=?, pause_reason='', lease_owner=NULL,
                    lease_expires_at=NULL, updated_at=?, version=? WHERE workflow_id=?""",
                (status, now, new_version, workflow_id),
            )
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 AS value FROM workflow_events WHERE workflow_id=?", (workflow_id,)
            ).fetchone()["value"]
            connection.execute(
                """INSERT INTO workflow_events(event_id, workflow_id, sequence, product_id, trace_id,
                    event_type, action, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"workflow-event-{uuid.uuid4().hex}", workflow_id, sequence, workflow["product_id"],
                 workflow["trace_id"], event_type, f"product_workflow_{operation}",
                 _json({"operation": operation, "expected_version": expected_version}), now),
            )
        return {"workflow_id": workflow_id, "product_id": workflow["product_id"], "status": status, "version": new_version}

    def refresh_provider_task(self, provider_task_id: str) -> Dict[str, Any]:
        with self._database.transaction() as connection:
            row = connection.execute("SELECT * FROM provider_tasks WHERE provider_task_id=?", (provider_task_id,)).fetchone()
            if row is None:
                raise KeyError(f"provider task '{provider_task_id}' does not exist")
            connection.execute("UPDATE provider_tasks SET updated_at=? WHERE provider_task_id=?", (now_iso(), provider_task_id))
        return {
            "provider_task_id": provider_task_id, "product_id": row["product_id"], "provider": row["provider"],
            "kind": row["kind"], "status": row["status"], "response": _object(row["response_json"]),
            "refreshed": True,
        }

    def audit(self, product_id: str, command: str, subject_id: str, decision: str, actor: str,
              reason: str, payload: Dict[str, Any], trace_id: str = "") -> None:
        with self._database.transaction() as connection:
            connection.execute(
                """INSERT INTO recovery_events(recovery_event_id, product_id, command, subject_id,
                    decision, actor, reason, payload_json, trace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"recovery-{uuid.uuid4().hex}", product_id, command, subject_id, decision,
                 actor, reason, _json(payload), trace_id, now_iso()),
            )


class SqliteConsoleReader:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def products(self) -> List[Dict[str, Any]]:
        ids = {path.name for path in products_root().iterdir() if path.is_dir()} if products_root().exists() else set()
        with self._database.read_session() as connection:
            for table in ("products", "product_brain_versions", "workflow_instances"):
                ids.update(row["product_id"] for row in connection.execute(f"SELECT DISTINCT product_id FROM {table}"))
        return [{"product_id": item, "workspace_path": str(products_root() / item)} for item in sorted(ids)]

    def snapshot(self, product_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            brain = connection.execute(
                "SELECT version, state_json, created_at FROM product_brain_versions WHERE product_id=? AND status='current'",
                (product_id,),
            ).fetchone()
            workflow = connection.execute(
                "SELECT workflow_id, status, definition, updated_at, version FROM workflow_instances WHERE product_id=? ORDER BY updated_at DESC LIMIT 1",
                (product_id,),
            ).fetchone()
            counts = {
                "pending_proposals": connection.execute("SELECT COUNT(*) c FROM writeback_proposals WHERE product_id=? AND status='proposed'", (product_id,)).fetchone()["c"],
                "open_workflows": connection.execute("SELECT COUNT(*) c FROM workflow_instances WHERE product_id=? AND status IN ('created','running','paused','failed')", (product_id,)).fetchone()["c"],
            }
        return {"product_id": product_id, "brain": ({"version": brain["version"], "state": _object(brain["state_json"]), "created_at": brain["created_at"]} if brain else {}), "latest_workflow": dict(workflow) if workflow else {}, "attention": counts}

    def workflows(self, product_id: str) -> List[Dict[str, Any]]:
        with self._database.read_session() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT workflow_id, definition, status, current_step, updated_at, version FROM workflow_instances WHERE product_id=? ORDER BY updated_at DESC",
                (product_id,),
            )]

    def workflow(self, workflow_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            workflow = connection.execute("SELECT * FROM workflow_instances WHERE workflow_id=?", (workflow_id,)).fetchone()
            if workflow is None:
                return {}
            steps = [dict(row) for row in connection.execute("SELECT * FROM workflow_steps WHERE workflow_id=? ORDER BY position", (workflow_id,))]
            events = [dict(row) for row in connection.execute("SELECT * FROM workflow_events WHERE workflow_id=? ORDER BY sequence", (workflow_id,))]
            tasks = [dict(row) for row in connection.execute("SELECT * FROM provider_tasks WHERE workflow_id=? ORDER BY created_at", (workflow_id,))]
        return {"workflow": dict(workflow), "steps": steps, "events": events, "provider_tasks": tasks}

    def review_queue(self, product_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            proposals = [_object(row["payload_json"]) for row in connection.execute(
                "SELECT payload_json FROM writeback_proposals WHERE product_id=? AND status='proposed' ORDER BY created_at", (product_id,)
            )]
            artifacts = [self._asset(row) for row in connection.execute(
                "SELECT * FROM artifact_records WHERE product_id=? ORDER BY created_at DESC LIMIT 50", (product_id,)
            )]
        return {"product_id": product_id, "proposals": proposals, "results": artifacts}

    def assets(self, product_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            artifacts = [self._asset(row) for row in connection.execute("SELECT * FROM artifact_records WHERE product_id=? ORDER BY created_at DESC", (product_id,))]
            materials = [self._material(row) for row in connection.execute("SELECT * FROM material_records WHERE product_id=? ORDER BY updated_at DESC", (product_id,))]
        return {"product_id": product_id, "artifacts": artifacts, "materials": materials}

    def learning(self, product_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            versions = [{**dict(row), "state": _object(row["state_json"])} for row in connection.execute(
                "SELECT * FROM product_brain_versions WHERE product_id=? ORDER BY version DESC", (product_id,)
            )]
            rules = [_object(row["payload_json"]) for row in connection.execute("SELECT payload_json FROM rule_candidates WHERE product_id=? ORDER BY updated_at DESC", (product_id,))]
            proposals = [_object(row["payload_json"]) for row in connection.execute("SELECT payload_json FROM writeback_proposals WHERE product_id=? ORDER BY updated_at DESC", (product_id,))]
        return {"product_id": product_id, "versions": versions, "rules": rules, "proposals": proposals}

    def media(self, record_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            rows = connection.execute("SELECT product_id, relative_path FROM artifact_records WHERE artifact_id=?", (record_id,)).fetchall()
            if not rows:
                rows = connection.execute("SELECT product_id, relative_path FROM material_records WHERE material_id=?", (record_id,)).fetchall()
            if len(rows) != 1:
                raise KeyError("media record is missing or ambiguous")
        path = (products_root() / rows[0]["product_id"] / rows[0]["relative_path"]).resolve(strict=True)
        root = products_root().resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError("media path is outside the product workspace")
        return {"path": path, "product_id": rows[0]["product_id"]}

    @staticmethod
    def _asset(row) -> Dict[str, Any]:
        return {"record_id": row["artifact_id"], "product_id": row["product_id"], "type": row["artifact_type"], "relative_path": row["relative_path"], "content_hash": row["content_hash"], "payload": _object(row["payload_json"]), "created_at": row["created_at"]}

    @staticmethod
    def _material(row) -> Dict[str, Any]:
        return {"record_id": row["material_id"], "product_id": row["product_id"], "type": "material", "relative_path": row["relative_path"], "content_hash": row["content_hash"], "status": row["status"], "payload": _object(row["payload_json"]), "created_at": row["created_at"]}
