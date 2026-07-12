"""SQLite-backed runtime observation read model."""

from __future__ import annotations

from ..contracts.durable import Observation
from .sqlite.database import runtime_database
from .sqlite.domain_repositories import SqliteProductBrainRepository
from .sqlite.repositories import _object


class SqliteObservationReader:
    def observe(self, product_id: str) -> Observation:
        database = runtime_database()
        brain = SqliteProductBrainRepository(database).current(product_id)
        with database.read_session() as connection:
            workflow = connection.execute(
                "SELECT workflow_id, status, current_step FROM workflow_instances WHERE product_id=? ORDER BY updated_at DESC LIMIT 1",
                (product_id,),
            ).fetchone()
            artifact_rows = connection.execute(
                "SELECT artifact_id FROM artifact_records WHERE product_id=? ORDER BY created_at DESC LIMIT 50",
                (product_id,),
            ).fetchall()
            material_rows = connection.execute(
                "SELECT material_id FROM material_records WHERE product_id=? AND status='active' ORDER BY updated_at DESC LIMIT 50",
                (product_id,),
            ).fetchall()
            provider_rows = connection.execute(
                "SELECT provider_task_id, provider, kind, status, response_json FROM provider_tasks WHERE product_id=? ORDER BY updated_at DESC LIMIT 20",
                (product_id,),
            ).fetchall()
            step = None
            if workflow:
                step = connection.execute(
                    "SELECT action FROM workflow_steps WHERE workflow_id=? AND position=?",
                    (workflow["workflow_id"], workflow["current_step"]),
                ).fetchone()
        compact = brain.get("state") if isinstance(brain.get("state"), dict) else {}
        return Observation(
            product_id=product_id,
            brain_version_id=str(brain.get("brain_version_id") or ""),
            brain_version=int(brain.get("version") or 0),
            workflow_status=str(workflow["status"]) if workflow else "",
            current_action=str(step["action"]) if step else "",
            artifact_ids=[row["artifact_id"] for row in artifact_rows],
            material_ids=[row["material_id"] for row in material_rows],
            provider_tasks=[{
                "provider_task_id": row["provider_task_id"], "provider": row["provider"],
                "kind": row["kind"], "status": row["status"], "response": _object(row["response_json"]),
            } for row in provider_rows],
            compact_context={
                "name": compact.get("name", ""), "status": compact.get("status", ""),
                "selling_points": list(compact.get("selling_points") or [])[:20],
                "style_preferences": compact.get("style_preferences") or {},
                "learning": compact.get("learning") or {},
            },
        )
