"""Idempotent legacy JSON import, backup, and rollback export."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable

from ..common import now_iso, products_root, timestamp
from ..contracts.models import RuleCandidate, WorkflowInstance
from ..infrastructure.sqlite.database import SqliteDatabase, runtime_database
from ..infrastructure.sqlite.domain_repositories import (
    SqliteArtifactRepository,
    SqliteMaterialRepository,
    SqliteProductBrainRepository,
    SqliteProposalRepository,
    SqliteRuleRepository,
)
from ..infrastructure.sqlite.repositories import SqliteWorkflowRepository, _json


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_manifest(root: Path) -> list[Dict[str, Any]]:
    return [
        {
            "path": str(path.relative_to(root)),
            "size": path.stat().st_size,
            "sha256": _file_hash(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def _manifest_hash(manifest: Iterable[Dict[str, Any]]) -> str:
    return hashlib.sha256(_json({"files": list(manifest)}).encode("utf-8")).hexdigest()


def _read_object(path: Path) -> Dict[str, Any]:
    raw = path.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    payload = json.loads(raw.decode(encoding))
    return payload if isinstance(payload, dict) else {}


def _record_import(
    database: SqliteDatabase,
    *,
    import_id: str,
    product_id: str,
    source_path: Path,
    source_hash: str,
    status: str,
    imported_records: int,
    error: Dict[str, Any] | None = None,
) -> None:
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO legacy_imports(
                import_id, product_id, source_path, source_hash, source_kind,
                status, imported_records, error_json, created_at, completed_at
            ) VALUES (?, ?, ?, ?, 'product_workspace', ?, ?, ?, ?, ?)
            ON CONFLICT(product_id, source_path, source_hash) DO UPDATE SET
                status=excluded.status, imported_records=excluded.imported_records,
                error_json=excluded.error_json, completed_at=excluded.completed_at
            """,
            (
                import_id,
                product_id,
                str(source_path),
                source_hash,
                status,
                imported_records,
                _json(error or {}),
                now_iso(),
                now_iso() if status in {"completed", "failed"} else None,
            ),
        )


def _already_imported(database: SqliteDatabase, product_id: str, source_path: Path, source_hash: str) -> bool:
    with database.read_session() as connection:
        row = connection.execute(
            """
            SELECT 1 FROM legacy_imports
            WHERE product_id=? AND source_path=? AND source_hash=? AND status='completed'
            """,
            (product_id, str(source_path), source_hash),
        ).fetchone()
        return row is not None


def _backup_product(database: SqliteDatabase, product: Path, backup_root: Path, manifest: list[Dict[str, Any]]) -> Path:
    destination = backup_root / product.name
    if not destination.exists():
        shutil.copytree(product, destination, copy_function=shutil.copy2)
    backup_id = f"backup-{uuid.uuid4().hex}"
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO migration_backups(
                backup_id, product_id, source_path, backup_path, content_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (backup_id, product.name, str(product), str(destination), _manifest_hash(manifest), now_iso()),
        )
    return destination


def _import_product(database: SqliteDatabase, product: Path) -> int:
    imported = 0
    brain = SqliteProductBrainRepository(database)
    proposals = SqliteProposalRepository(database)
    artifacts = SqliteArtifactRepository(database)
    materials = SqliteMaterialRepository(database)
    rules = SqliteRuleRepository(database)
    workflows = SqliteWorkflowRepository(product, database)

    state_path = product / "structured" / "product_state.json"
    if state_path.exists():
        brain.ensure_initial(product.name, _read_object(state_path))
        imported += 1

    source_index = product / "structured" / "source_index.jsonl"
    if source_index.exists():
        for line in source_index.read_text(encoding="utf-8-sig").splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict) or not payload.get("source_id"):
                continue
            artifacts.save(
                product.name,
                str(payload["source_id"]),
                "source_registry",
                "structured/source_index.jsonl",
                payload,
            )
            imported += 1

    artifacts_root = product / "artifacts"
    if artifacts_root.exists():
        for path in sorted(artifacts_root.rglob("*.json")):
            payload = _read_object(path)
            if not payload:
                continue
            artifact_id = path.stem
            artifact_type = path.relative_to(artifacts_root).parts[0]
            artifacts.save(product.name, artifact_id, artifact_type, str(path.relative_to(product)), payload)
            if artifact_type == "material_assets" or payload.get("material_id"):
                materials.save(product.name, str(payload.get("material_id") or artifact_id), str(path.relative_to(product)), payload)
            imported += 1

    proposal_root = product / "structured" / "evolution_proposals"
    if proposal_root.exists():
        for path in sorted(proposal_root.glob("*.json")):
            payload = _read_object(path)
            if payload.get("proposal_id"):
                proposals.save(payload)
                imported += 1

    rule_root = product / "structured" / "rule_candidates"
    if rule_root.exists():
        for path in sorted(rule_root.glob("*.json")):
            payload = _read_object(path)
            fields = {name: payload[name] for name in RuleCandidate.model_fields if name in payload}
            if fields.get("rule_id"):
                subject_ids = (fields.get("conditions") or {}).get("source_subject_ids") or [path.stem]
                rules.persist([RuleCandidate.model_validate(fields)], str(subject_ids[0]))
                imported += 1

    workflow_root = product / "structured" / "workflows"
    if workflow_root.exists():
        for path in sorted(workflow_root.glob("*.json")):
            payload = _read_object(path)
            try:
                instance = WorkflowInstance.model_validate(payload)
            except Exception:
                continue
            if workflows.get(instance.workflow_id) is None:
                workflows.save_with_event(
                    instance,
                    {
                        "event_type": "workflow.legacy_imported",
                        "workflow_id": instance.workflow_id,
                        "product_id": instance.product_id,
                        "trace_id": instance.trace_id,
                        "created_at": now_iso(),
                    },
                )
                imported += 1
    return imported


def reindex_legacy_metadata(
    source_root: Path | None = None,
    database: SqliteDatabase | None = None,
) -> Dict[str, Any]:
    database = database or runtime_database()
    source_root = (source_root or products_root()).resolve()
    results = []
    for product in sorted(path for path in source_root.iterdir() if path.is_dir()):
        try:
            count = _import_product(database, product)
            results.append({"product_id": product.name, "status": "completed", "indexed_records": count})
        except Exception as exc:
            results.append({"product_id": product.name, "status": "failed", "error": str(exc)})
    return {
        "success": all(item["status"] == "completed" for item in results),
        "source_root": str(source_root),
        "product_count": len(results),
        "results": results,
    }


def backup_and_import(
    source_root: Path | None = None,
    backup_root: Path | None = None,
    database: SqliteDatabase | None = None,
) -> Dict[str, Any]:
    database = database or runtime_database()
    source_root = (source_root or products_root()).resolve()
    backup_root = (
        backup_root
        or (source_root.parents[1] / "pcbak" / timestamp())
    ).resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    results = []
    for product in sorted(path for path in source_root.iterdir() if path.is_dir()):
        manifest = _tree_manifest(product)
        source_hash = _manifest_hash(manifest)
        if _already_imported(database, product.name, product, source_hash):
            results.append({"product_id": product.name, "status": "already_imported", "source_hash": source_hash})
            continue
        import_id = f"legacy-import-{uuid.uuid4().hex}"
        try:
            destination = _backup_product(database, product, backup_root, manifest)
            (destination / "migration-manifest.json").write_text(
                json.dumps({"product_id": product.name, "source_hash": source_hash, "files": manifest}, indent=2),
                encoding="utf-8",
            )
            count = _import_product(database, product)
            _record_import(
                database,
                import_id=import_id,
                product_id=product.name,
                source_path=product,
                source_hash=source_hash,
                status="completed",
                imported_records=count,
            )
            results.append(
                {
                    "product_id": product.name,
                    "status": "completed",
                    "source_hash": source_hash,
                    "backup_path": str(destination),
                    "imported_records": count,
                }
            )
        except Exception as exc:
            _record_import(
                database,
                import_id=import_id,
                product_id=product.name,
                source_path=product,
                source_hash=source_hash,
                status="failed",
                imported_records=0,
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            results.append({"product_id": product.name, "status": "failed", "error": str(exc)})
    return {
        "success": all(item["status"] in {"completed", "already_imported"} for item in results),
        "source_root": str(source_root),
        "backup_root": str(backup_root),
        "product_count": len(results),
        "results": results,
    }


def export_legacy_layout(product_id: str, destination: Path, database: SqliteDatabase | None = None) -> Dict[str, Any]:
    database = database or runtime_database()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    brain = SqliteProductBrainRepository(database).current(product_id)
    if not brain:
        raise KeyError(f"Product Brain '{product_id}' does not exist")
    state_path = destination / "structured" / "product_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(brain["state"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    count = 1
    with database.read_session() as connection:
        for row in connection.execute(
            "SELECT relative_path, payload_json FROM artifact_records WHERE product_id=?", (product_id,)
        ):
            path = destination / row["relative_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(json.loads(row["payload_json"]), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            count += 1
        for row in connection.execute(
            "SELECT proposal_id, payload_json FROM writeback_proposals WHERE product_id=?", (product_id,)
        ):
            path = destination / "structured" / "evolution_proposals" / f"{row['proposal_id']}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(json.loads(row["payload_json"]), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            count += 1
    return {"success": True, "product_id": product_id, "destination": str(destination), "exported_records": count}
