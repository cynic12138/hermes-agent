"""SQLite repositories for learning, Product Brain, artifacts, and materials."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ...common import now_iso
from ...contracts.models import RuleCandidate
from .database import SqliteDatabase, runtime_database
from .repositories import OptimisticVersionConflict, _json, _object


def content_hash(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SqliteRuleRepository:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def persist(self, candidates: Iterable[RuleCandidate], subject_id: str) -> List[str]:
        ids: List[str] = []
        with self._database.transaction() as connection:
            for candidate in candidates:
                row = connection.execute(
                    """
                    SELECT * FROM rule_candidates
                    WHERE product_id=? AND conflict_key=? AND json_extract(payload_json, '$.value')=?
                    ORDER BY created_at LIMIT 1
                    """,
                    (candidate.product_id, candidate.conflict_key, candidate.value),
                ).fetchone()
                if row is not None:
                    payload = _object(row["payload_json"])
                    conditions = payload.get("conditions") if isinstance(payload.get("conditions"), dict) else {}
                    subjects = [str(item) for item in conditions.get("source_subject_ids") or []]
                    if subject_id not in subjects:
                        subjects.append(subject_id)
                        payload["sample_size"] = int(payload.get("sample_size") or 1) + 1
                        payload["confidence"] = min(0.95, round(float(payload.get("confidence") or 0) + 0.08, 2))
                    conditions["source_subject_ids"] = subjects
                    payload["conditions"] = conditions
                    rule_id = str(row["rule_id"])
                    connection.execute(
                        """
                        UPDATE rule_candidates SET sample_size=?, confidence=?, payload_json=?, updated_at=?
                        WHERE rule_id=?
                        """,
                        (payload["sample_size"], payload["confidence"], _json(payload), now_iso(), rule_id),
                    )
                    self._insert_evidence(connection, rule_id, candidate)
                    ids.append(rule_id)
                    continue

                conflicts = connection.execute(
                    """
                    SELECT rule_id FROM rule_candidates
                    WHERE product_id=? AND conflict_key=? AND status NOT IN ('rejected', 'revoked')
                    """,
                    (candidate.product_id, candidate.conflict_key),
                ).fetchall()
                payload = candidate.model_dump(mode="json")
                payload.setdefault("conditions", {})["source_subject_ids"] = [subject_id]
                if conflicts:
                    payload["status"] = "review_required"
                    payload["conditions"]["conflicts_with"] = [row["rule_id"] for row in conflicts]
                now = candidate.created_at or now_iso()
                connection.execute(
                    """
                    INSERT INTO rule_candidates(
                        rule_id, product_id, conflict_key, scope, target_path, status,
                        risk_level, sample_size, confidence, payload_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candidate.rule_id,
                        candidate.product_id,
                        candidate.conflict_key,
                        candidate.scope,
                        candidate.target_path,
                        payload["status"],
                        candidate.risk_level,
                        candidate.sample_size,
                        candidate.confidence,
                        _json(payload),
                        now,
                        now,
                    ),
                )
                self._insert_evidence(connection, candidate.rule_id, candidate)
                for conflict in conflicts:
                    connection.execute(
                        """
                        INSERT INTO rule_conflicts(
                            conflict_id, product_id, conflict_key, left_rule_id,
                            right_rule_id, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"conflict-{uuid.uuid4().hex}",
                            candidate.product_id,
                            candidate.conflict_key,
                            conflict["rule_id"],
                            candidate.rule_id,
                            now,
                        ),
                    )
                ids.append(candidate.rule_id)
        return ids

    @staticmethod
    def _insert_evidence(connection, rule_id: str, candidate: RuleCandidate) -> None:
        for evidence in candidate.evidence:
            connection.execute(
                """
                INSERT INTO rule_evidence(rule_id, evidence_id, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(rule_id, evidence_id) DO UPDATE SET payload_json=excluded.payload_json
                """,
                (rule_id, evidence.evidence_id, _json(evidence.model_dump(mode="json")), now_iso()),
            )

    def get(self, rule_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            row = connection.execute("SELECT payload_json FROM rule_candidates WHERE rule_id=?", (rule_id,)).fetchone()
            return _object(row["payload_json"]) if row else {}

    def list(self, product_id: str, subject_id: str = "") -> List[Dict[str, Any]]:
        with self._database.read_session() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM rule_candidates WHERE product_id=? ORDER BY created_at, rule_id",
                (product_id,),
            ).fetchall()
        payloads = [_object(row["payload_json"]) for row in rows]
        if not subject_id:
            return payloads
        return [
            payload
            for payload in payloads
            if subject_id == (payload.get("conditions") or {}).get("source_subject_id")
            or subject_id in ((payload.get("conditions") or {}).get("source_subject_ids") or [])
        ]

    def mark_applied(self, product_id: str, rule_ids: Iterable[str], applied_at: str, proposal_id: str) -> None:
        with self._database.transaction() as connection:
            for rule_id in rule_ids:
                row = connection.execute(
                    "SELECT payload_json FROM rule_candidates WHERE rule_id=? AND product_id=?",
                    (str(rule_id), product_id),
                ).fetchone()
                if row is None:
                    continue
                payload = _object(row["payload_json"])
                payload.update(
                    {"status": "applied", "applied_at": applied_at, "applied_by_proposal_id": proposal_id}
                )
                connection.execute(
                    "UPDATE rule_candidates SET status='applied', payload_json=?, updated_at=? WHERE rule_id=?",
                    (_json(payload), applied_at, str(rule_id)),
                )

    def eligible(self, product_id: str, minimum_samples: int = 2, minimum_confidence: float = 0.68) -> List[Dict[str, Any]]:
        with self._database.read_session() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM rule_candidates r
                WHERE r.product_id=?
                  AND r.status IN ('candidate', 'approved')
                  AND r.sample_size>=?
                  AND r.confidence>=?
                  AND NOT EXISTS (
                    SELECT 1 FROM rule_conflicts c
                    WHERE c.product_id=r.product_id AND c.conflict_key=r.conflict_key AND c.status='open'
                  )
                ORDER BY r.confidence DESC, r.sample_size DESC, r.created_at
                """,
                (product_id, minimum_samples, minimum_confidence),
            ).fetchall()
        return [_object(row["payload_json"]) for row in rows]

    def decay(self, product_id: str, factor: float = 0.95, floor: float = 0.2) -> int:
        factor = min(1.0, max(0.0, factor))
        floor = min(1.0, max(0.0, floor))
        changed = 0
        with self._database.transaction() as connection:
            rows = connection.execute(
                "SELECT rule_id, confidence, payload_json FROM rule_candidates WHERE product_id=? AND status NOT IN ('applied', 'rejected', 'revoked')",
                (product_id,),
            ).fetchall()
            for row in rows:
                confidence = max(floor, round(float(row["confidence"]) * factor, 4))
                payload = _object(row["payload_json"])
                payload["confidence"] = confidence
                connection.execute(
                    "UPDATE rule_candidates SET confidence=?, payload_json=?, updated_at=? WHERE rule_id=?",
                    (confidence, _json(payload), now_iso(), row["rule_id"]),
                )
                changed += 1
        return changed

    def revoke(self, product_id: str, rule_id: str, reason: str) -> bool:
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT payload_json FROM rule_candidates WHERE product_id=? AND rule_id=?",
                (product_id, rule_id),
            ).fetchone()
            if row is None:
                return False
            payload = _object(row["payload_json"])
            payload.update({"status": "revoked", "revoked_at": now_iso(), "revocation_reason": reason})
            connection.execute(
                "UPDATE rule_candidates SET status='revoked', payload_json=?, updated_at=? WHERE product_id=? AND rule_id=?",
                (_json(payload), now_iso(), product_id, rule_id),
            )
            return True


class SqliteProposalRepository:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def save(self, proposal: Dict[str, Any]) -> str:
        now = str(proposal.get("created_at") or now_iso())
        updates = [item for item in proposal.get("updates") or [] if isinstance(item, dict)]
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO writeback_proposals(
                    proposal_id, product_id, status, risk_level, payload_json, created_at, updated_at, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_id, proposal_id) DO UPDATE SET
                    status=excluded.status, risk_level=excluded.risk_level,
                    payload_json=excluded.payload_json, updated_at=excluded.updated_at,
                    applied_at=excluded.applied_at
                """,
                (
                    proposal["proposal_id"],
                    proposal["product_id"],
                    proposal.get("status") or "proposed",
                    proposal.get("risk_level") or "medium",
                    _json(proposal),
                    now,
                    now_iso(),
                    proposal.get("applied_at") or None,
                ),
            )
            connection.execute(
                "DELETE FROM proposal_updates WHERE product_id=? AND proposal_id=?",
                (proposal["product_id"], proposal["proposal_id"]),
            )
            for position, update in enumerate(updates):
                connection.execute(
                    "INSERT INTO proposal_updates(product_id, proposal_id, position, target_path, payload_json) VALUES (?, ?, ?, ?, ?)",
                    (proposal["product_id"], proposal["proposal_id"], position, str(update.get("path") or ""), _json(update)),
                )
        return f"sqlite:///{self._database.path}#proposal/{proposal['proposal_id']}"

    def get(self, proposal_id: str, product_id: str = "") -> Dict[str, Any]:
        with self._database.read_session() as connection:
            if product_id:
                row = connection.execute(
                    "SELECT payload_json FROM writeback_proposals WHERE product_id=? AND proposal_id=?",
                    (product_id, proposal_id),
                ).fetchone()
            else:
                rows = connection.execute(
                    "SELECT payload_json FROM writeback_proposals WHERE proposal_id=?", (proposal_id,)
                ).fetchall()
                if len(rows) > 1:
                    raise KeyError(f"proposal '{proposal_id}' is ambiguous without product_id")
                row = rows[0] if rows else None
            return _object(row["payload_json"]) if row else {}

    def list(self, product_id: str) -> List[Dict[str, Any]]:
        with self._database.read_session() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM writeback_proposals WHERE product_id=? ORDER BY created_at, proposal_id",
                (product_id,),
            ).fetchall()
        return [_object(row["payload_json"]) for row in rows]


class SqliteProductBrainRepository:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def current(self, product_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            row = connection.execute(
                """
                SELECT * FROM product_brain_versions
                WHERE product_id=? AND status='current'
                ORDER BY version DESC LIMIT 1
                """,
                (product_id,),
            ).fetchone()
            return self._version_payload(row) if row else {}

    def ensure_initial(self, product_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        current = self.current(product_id)
        if current:
            return current
        version_id = f"brain-{uuid.uuid4().hex}"
        now = now_iso()
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO product_brain_versions(
                    brain_version_id, product_id, version, state_json, content_hash, status, created_at, change_kind
                ) VALUES (?, ?, 1, ?, ?, 'current', ?, 'initial')
                """,
                (version_id, product_id, _json(state), content_hash(state), now),
            )
        return self.current(product_id)

    def commit_state(
        self,
        product_id: str,
        state: Dict[str, Any],
        *,
        change_kind: str,
        expected_version: int | None = None,
        trace_id: str = "",
    ) -> Dict[str, Any]:
        current = self.current(product_id)
        if not current:
            return self.ensure_initial(product_id, state)
        if content_hash(state) == current["content_hash"]:
            return current
        expected = int(current["version"] if expected_version is None else expected_version)
        new_id = f"brain-{uuid.uuid4().hex}"
        now = now_iso()
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM product_brain_versions WHERE product_id=? AND status='current'",
                (product_id,),
            ).fetchone()
            actual = int(row["version"]) if row else 0
            if row is None or actual != expected:
                raise OptimisticVersionConflict(
                    f"Product Brain '{product_id}' expected version {expected}, actual {actual}"
                )
            connection.execute(
                "UPDATE product_brain_versions SET status='superseded' WHERE brain_version_id=?",
                (row["brain_version_id"],),
            )
            connection.execute(
                """
                INSERT INTO product_brain_versions(
                    brain_version_id, product_id, version, parent_version_id,
                    state_json, content_hash, status, created_at, change_kind, trace_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'current', ?, ?, ?)
                """,
                (
                    new_id,
                    product_id,
                    expected + 1,
                    row["brain_version_id"],
                    _json(state),
                    content_hash(state),
                    now,
                    change_kind,
                    trace_id,
                ),
            )
            saved = connection.execute(
                "SELECT * FROM product_brain_versions WHERE brain_version_id=?", (new_id,)
            ).fetchone()
        return self._version_payload(saved)

    def apply_proposal(
        self,
        *,
        product_id: str,
        proposal_id: str,
        expected_version: int,
        state: Dict[str, Any],
        applied_rule_ids: Iterable[str],
        proposal_updates: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        now = now_iso()
        new_id = f"brain-{uuid.uuid4().hex}"
        with self._database.transaction() as connection:
            current = connection.execute(
                "SELECT * FROM product_brain_versions WHERE product_id=? AND status='current'",
                (product_id,),
            ).fetchone()
            if current is None or int(current["version"]) != expected_version:
                actual = int(current["version"]) if current else 0
                raise OptimisticVersionConflict(
                    f"Product Brain '{product_id}' expected version {expected_version}, actual {actual}"
                )
            proposal = connection.execute(
                "SELECT status, payload_json FROM writeback_proposals WHERE product_id=? AND proposal_id=?",
                (product_id, proposal_id),
            ).fetchone()
            if proposal is None:
                raise KeyError(f"proposal '{proposal_id}' does not exist")
            if proposal["status"] == "applied":
                return self._version_payload(current)
            new_version = expected_version + 1
            connection.execute(
                "UPDATE product_brain_versions SET status='superseded' WHERE brain_version_id=?",
                (current["brain_version_id"],),
            )
            connection.execute(
                """
                INSERT INTO product_brain_versions(
                    brain_version_id, product_id, version, parent_version_id, proposal_id,
                    state_json, content_hash, status, created_at, change_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'current', ?, 'proposal_apply')
                """,
                (
                    new_id,
                    product_id,
                    new_version,
                    current["brain_version_id"],
                    proposal_id,
                    _json(state),
                    content_hash(state),
                    now,
                ),
            )
            stored_proposal = _object(proposal["payload_json"])
            if proposal_updates is not None:
                stored_proposal.update(proposal_updates)
            stored_proposal.update({"status": "applied", "applied_at": now})
            connection.execute(
                """
                UPDATE writeback_proposals SET status='applied', payload_json=?, applied_at=?, updated_at=?
                WHERE product_id=? AND proposal_id=?
                """,
                (_json(stored_proposal), now, now, product_id, proposal_id),
            )
            for rule_id in applied_rule_ids:
                row = connection.execute(
                    "SELECT payload_json FROM rule_candidates WHERE rule_id=? AND product_id=?",
                    (str(rule_id), product_id),
                ).fetchone()
                if row:
                    payload = _object(row["payload_json"])
                    payload.update({"status": "applied", "applied_at": now, "applied_by_proposal_id": proposal_id})
                    connection.execute(
                        "UPDATE rule_candidates SET status='applied', payload_json=?, updated_at=? WHERE rule_id=?",
                        (_json(payload), now, str(rule_id)),
                    )
            row = connection.execute(
                "SELECT * FROM product_brain_versions WHERE brain_version_id=?", (new_id,)
            ).fetchone()
        return self._version_payload(row)

    def rollback(self, product_id: str, target_version: int, expected_version: int) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            target = connection.execute(
                "SELECT state_json FROM product_brain_versions WHERE product_id=? AND version=?",
                (product_id, target_version),
            ).fetchone()
        if target is None:
            raise KeyError(f"Product Brain version {target_version} does not exist")
        rollback_proposal = {
            "proposal_id": f"rollback-{uuid.uuid4().hex}",
            "product_id": product_id,
            "status": "proposed",
            "risk_level": "high",
            "updates": [],
            "created_at": now_iso(),
            "rollback_target_version": target_version,
        }
        SqliteProposalRepository(self._database).save(rollback_proposal)
        return self.apply_proposal(
            product_id=product_id,
            proposal_id=rollback_proposal["proposal_id"],
            expected_version=expected_version,
            state=_object(target["state_json"]),
            applied_rule_ids=(),
        )

    def record_generation_snapshot(
        self,
        product_id: str,
        target: str,
        payload: Dict[str, Any],
        snapshot_id: str = "",
    ) -> Dict[str, Any]:
        current = self.current(product_id)
        if not current:
            raise RuntimeError(f"Product Brain '{product_id}' has no confirmed version")
        snapshot_id = snapshot_id or f"snapshot-{uuid.uuid4().hex}"
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO generation_snapshots(
                    snapshot_id, product_id, brain_version_id, target, payload_json, content_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_id) DO NOTHING
                """,
                (
                    snapshot_id,
                    product_id,
                    current["brain_version_id"],
                    target,
                    _json(payload),
                    content_hash(payload),
                    now_iso(),
                ),
            )
        return {
            "snapshot_id": snapshot_id,
            "brain_version_id": current["brain_version_id"],
            "brain_version": current["version"],
        }

    @staticmethod
    def _version_payload(row) -> Dict[str, Any]:
        return {
            "brain_version_id": row["brain_version_id"],
            "product_id": row["product_id"],
            "version": row["version"],
            "parent_version_id": row["parent_version_id"] or "",
            "proposal_id": row["proposal_id"] or "",
            "state": _object(row["state_json"]),
            "content_hash": row["content_hash"],
            "status": row["status"],
            "created_at": row["created_at"],
            "change_kind": row["change_kind"],
            "trace_id": row["trace_id"],
        }


class SqliteArtifactRepository:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def save(self, product_id: str, artifact_id: str, artifact_type: str, relative_path: str, payload: Dict[str, Any]) -> str:
        with self._database.transaction() as connection:
            existing = connection.execute(
                "SELECT artifact_id FROM artifact_records WHERE product_id=? AND relative_path=?",
                (product_id, relative_path),
            ).fetchone()
            if existing is not None and existing["artifact_id"] != artifact_id:
                connection.execute(
                    """
                    UPDATE artifact_records
                    SET artifact_type=?, content_hash=?, payload_json=?
                    WHERE product_id=? AND relative_path=?
                    """,
                    (artifact_type, content_hash(payload), _json(payload), product_id, relative_path),
                )
                return f"sqlite:///{self._database.path}#artifact/{existing['artifact_id']}"
            connection.execute(
                """
                INSERT INTO artifact_records(
                    artifact_id, product_id, artifact_type, relative_path, content_hash, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_id, artifact_id) DO UPDATE SET
                    artifact_type=excluded.artifact_type, relative_path=excluded.relative_path,
                    content_hash=excluded.content_hash, payload_json=excluded.payload_json
                """,
                (artifact_id, product_id, artifact_type, relative_path, content_hash(payload), _json(payload), now_iso()),
            )
        return f"sqlite:///{self._database.path}#artifact/{artifact_id}"

    def list(self, product_id: str, artifact_type: str = "") -> List[Dict[str, Any]]:
        with self._database.read_session() as connection:
            if artifact_type:
                rows = connection.execute(
                    "SELECT payload_json FROM artifact_records WHERE product_id=? AND artifact_type=? ORDER BY created_at",
                    (product_id, artifact_type),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload_json FROM artifact_records WHERE product_id=? ORDER BY created_at",
                    (product_id,),
                ).fetchall()
        return [_object(row["payload_json"]) for row in rows]

    def list_records(self, product_id: str, artifact_type: str = "") -> List[Dict[str, Any]]:
        with self._database.read_session() as connection:
            if artifact_type:
                rows = connection.execute(
                    "SELECT artifact_id, artifact_type, relative_path, payload_json, created_at FROM artifact_records WHERE product_id=? AND artifact_type=? ORDER BY created_at, artifact_id",
                    (product_id, artifact_type),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT artifact_id, artifact_type, relative_path, payload_json, created_at FROM artifact_records WHERE product_id=? ORDER BY created_at, artifact_id",
                    (product_id,),
                ).fetchall()
        return [{
            "artifact_id": row["artifact_id"], "artifact_type": row["artifact_type"],
            "relative_path": row["relative_path"], "payload": _object(row["payload_json"]),
            "recorded_at": row["created_at"],
        } for row in rows]

    def get(self, product_id: str, artifact_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            row = connection.execute(
                "SELECT payload_json FROM artifact_records WHERE product_id=? AND artifact_id=?",
                (product_id, artifact_id),
            ).fetchone()
            return _object(row["payload_json"]) if row else {}


class SqliteMaterialRepository:
    def __init__(self, database: SqliteDatabase | None = None):
        self._database = database or runtime_database()

    def save(self, product_id: str, material_id: str, relative_path: str, payload: Dict[str, Any], status: str = "active") -> str:
        now = now_iso()
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO material_records(
                    material_id, product_id, relative_path, content_hash, status, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_id, material_id) DO UPDATE SET
                    relative_path=excluded.relative_path, content_hash=excluded.content_hash,
                    status=excluded.status, payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (material_id, product_id, relative_path, content_hash(payload), status, _json(payload), now, now),
            )
        return f"sqlite:///{self._database.path}#material/{material_id}"

    def get(self, product_id: str, material_id: str) -> Dict[str, Any]:
        with self._database.read_session() as connection:
            row = connection.execute(
                "SELECT payload_json FROM material_records WHERE product_id=? AND material_id=?",
                (product_id, material_id),
            ).fetchone()
            return _object(row["payload_json"]) if row else {}

    def list(self, product_id: str) -> List[Dict[str, Any]]:
        with self._database.read_session() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM material_records WHERE product_id=? ORDER BY created_at, material_id",
                (product_id,),
            ).fetchall()
        return [_object(row["payload_json"]) for row in rows]
