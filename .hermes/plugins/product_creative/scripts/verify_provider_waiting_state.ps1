[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$python = "C:\Users\1\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"

$test = @'
import json
import sys
import tempfile
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / ".hermes" / "plugins"))

from product_creative.contracts.models import IntentDecision
from product_creative.durable_workflow.engine import DurableWorkflowEngine
from product_creative.infrastructure.sqlite.database import SqliteDatabase
from product_creative.infrastructure.sqlite.repositories import SqliteWorkflowRepository
from product_creative.runtime.workflow_catalog import WorkflowDefinition

with tempfile.TemporaryDirectory(prefix="provider-waiting-") as temp:
    database = SqliteDatabase(Path(temp) / "runtime.sqlite3")
    repository = SqliteWorkflowRepository(database=database)
    engine = DurableWorkflowEngine(repository)
    definition = WorkflowDefinition(
        name="provider_waiting_test",
        version="1",
        actions=("check_video_task_status", "review_generated_result"),
    )
    decision = IntentDecision(
        product_id="provider-waiting-test",
        action="check_video_task_status",
        goal="poll provider",
        modality="video",
        confidence=1,
        source="explicit_action",
    )
    first = engine.begin_step(
        "provider-waiting-test", definition, decision, {"task_id": "task-1"}, "trace-1", True
    )
    waiting = engine.complete_step(first, {"success": True, "normalized_status": "processing"}, True)
    stored = repository.get(first.workflow_id)
    rotated_key = stored.steps[0].idempotency_key
    second = engine.begin_step(
        "provider-waiting-test", definition, decision, {"task_id": "task-1"}, "trace-1", True
    )
    completed = engine.complete_step(second, {"success": True, "normalized_status": "completed"}, True)

checks = {
    "paused_while_processing": waiting["status"] == "paused",
    "same_poll_action": waiting["current_action"] == "check_video_task_status",
    "waiting_reason": waiting["pause_reason"] == "provider_processing",
    "idempotency_rotated": rotated_key != first.idempotency_key and second.idempotency_key == rotated_key,
    "advances_after_completion": completed["current_action"] == "review_generated_result",
}
report = {"success": all(checks.values()), "checks": checks}
print(json.dumps(report, indent=2))
if not report["success"]:
    raise SystemExit(1)
'@

$test | & $python - $repoRoot
exit $LASTEXITCODE
