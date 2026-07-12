[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / ".hermes" / "plugins"))

from product_creative.contracts.models import IntentDecision
from product_creative.durable_workflow.engine import DurableWorkflowEngine
from product_creative.infrastructure.mock_provider import MockProviderGateway
from product_creative.infrastructure.outbox_worker import OutboxWorker
from product_creative.infrastructure.sqlite.database import SqliteDatabase
import product_creative.infrastructure.sqlite.database as database_module
from product_creative.infrastructure.sqlite.repositories import (
    OptimisticVersionConflict,
    SqliteActionReceiptRepository,
    SqliteOutboxRepository,
    SqliteProviderTaskRepository,
    SqliteWorkflowRepository,
)
from product_creative.migrations.legacy import backup_and_import, export_legacy_layout
from product_creative.runtime.workflow_catalog import WorkflowDefinition


checks = {}
with tempfile.TemporaryDirectory(prefix="product-creative-durable-") as td:
    root = Path(td)
    db_path = root / "runtime.sqlite3"
    db = SqliteDatabase(db_path)
    db.initialize()
    with db.read_session() as connection:
        versions = [row["version"] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    checks["migration_versions"] = versions
    assert versions == list(range(1, 9)), versions

    original_migrations = database_module.MIGRATIONS
    database_module.MIGRATIONS = original_migrations + ((999, "injected_failure", "CREATE TABLE should_rollback(x); INVALID SQL;"),)
    try:
        try:
            SqliteDatabase(root / "failed.sqlite3")
            raise AssertionError("injected migration did not fail")
        except Exception:
            pass
        failed = SqliteDatabase.__new__(SqliteDatabase)
        failed.path = (root / "failed.sqlite3").resolve()
        connection = failed._connect()
        try:
            assert connection.execute("SELECT name FROM sqlite_master WHERE name='should_rollback'").fetchone() is None
            assert connection.execute("SELECT version FROM schema_migrations WHERE version=999").fetchone() is None
        finally:
            connection.close()
    finally:
        database_module.MIGRATIONS = original_migrations
    checks["migration_rollback"] = True

    workflow_repo = SqliteWorkflowRepository(database=db)
    engine = DurableWorkflowEngine(workflow_repo, lease_seconds=1)
    decision = IntentDecision(product_id="p1", action="test_action", goal="test", confidence=1, source="explicit_action")
    definition = WorkflowDefinition("test_workflow", "1", ("test_action",))
    handle = engine.begin_step("p1", definition, decision, {"value": 1}, "trace-1", True)
    with db.read_session() as connection:
        row = connection.execute("SELECT status FROM workflow_steps WHERE workflow_id=?", (handle.workflow_id,)).fetchone()
        event = connection.execute("SELECT event_type FROM workflow_events WHERE workflow_id=? ORDER BY sequence DESC LIMIT 1", (handle.workflow_id,)).fetchone()
    assert row["status"] == "running" and event["event_type"] == "workflow.step_started"
    first = workflow_repo.get(handle.workflow_id)
    stale = workflow_repo.get(handle.workflow_id)
    first.pause_reason = "one"
    first.updated_at = "2026-01-01T00:00:01+00:00"
    workflow_repo.save(first)
    try:
        stale.pause_reason = "stale"
        stale.updated_at = "2026-01-01T00:00:02+00:00"
        workflow_repo.save(stale)
        raise AssertionError("optimistic conflict not raised")
    except OptimisticVersionConflict:
        pass
    engine.complete_step(handle, {"success": True}, True)
    checks["workflow_before_side_effect"] = True
    checks["optimistic_conflict"] = True

    lease_results = []
    barrier = threading.Barrier(2)
    def lease_attempt(owner):
        barrier.wait()
        lease_results.append(workflow_repo.acquire_product_lease("concurrent-product", owner, 2))
    threads = [threading.Thread(target=lease_attempt, args=(f"owner-{i}",)) for i in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sorted(lease_results) == [False, True], lease_results
    checks["single_product_lease"] = True

    receipts = SqliteActionReceiptRepository("receipt-product", database=db)
    receipt_key = receipts.key("confirm", {"pack": "pack-one"})
    first_claim = receipts.claim("confirm", receipt_key, {"pack": "pack-one"})
    second_claim = receipts.claim("confirm", receipt_key, {"pack": "pack-one"})
    assert first_claim["claimed"] and not second_claim["claimed"]
    with db.transaction() as connection:
        connection.execute(
            "UPDATE command_receipts SET updated_at='2000-01-01T00:00:00+00:00' WHERE receipt_key=?",
            (receipt_key,),
        )
    recovered_claim = receipts.claim("confirm", receipt_key, {"pack": "pack-one"}, stale_after_seconds=1)
    assert recovered_claim["claimed"] and recovered_claim["recovered"]
    receipts.save("confirm", receipt_key, {"idempotency_values": {"pack": "pack-one"}, "result": {"success": True, "entry_id": "entry-one"}})
    completed_claim = receipts.claim("confirm", receipt_key, {"pack": "pack-one"})
    assert not completed_claim["claimed"] and completed_claim["status"] == "completed"
    assert completed_claim["result"]["entry_id"] == "entry-one"
    checks["receipt_crash_recovery"] = True

    outbox = SqliteOutboxRepository(db)
    tasks = SqliteProviderTaskRepository(db)
    timeout_id = outbox.enqueue(
        product_id="p1", topic="provider.image", idempotency_key="timeout-key",
        payload={"provider": "mock", "kind": "image", "inject_failure": "timeout"},
    )
    timeout_result = OutboxWorker(MockProviderGateway(db), outbox, tasks, "timeout-worker").run_once(timeout_id)
    assert not timeout_result["success"] and outbox.get(timeout_id)["status"] == "retry"

    stable_id = outbox.enqueue(
        product_id="p1", topic="provider.image", idempotency_key="stable-key",
        payload={"provider": "mock", "kind": "image"},
    )
    gateway = MockProviderGateway(db)
    delivered = OutboxWorker(gateway, outbox, tasks, "worker-one").run_once(stable_id)
    assert delivered["success"] and gateway.calls["stable-key"] == 1
    with db.transaction() as connection:
        connection.execute("UPDATE outbox_events SET status='retry', result_json='{}', available_at=0 WHERE outbox_id=?", (stable_id,))
    recovered = OutboxWorker(gateway, outbox, tasks, "worker-two").run_once(stable_id)
    assert recovered["success"] and recovered["recovered"] and gateway.calls["stable-key"] == 1
    checks["outbox_retry"] = True
    checks["provider_exactly_once"] = True

    products = root / "legacy-products"
    product = products / "legacy-one"
    (product / "structured").mkdir(parents=True)
    (product / "artifacts" / "copy").mkdir(parents=True)
    (product / "structured" / "product_state.json").write_text(
        json.dumps({"product_id": "legacy-one", "name": "Legacy", "sources": [], "learning": {}}), encoding="utf-8"
    )
    (product / "artifacts" / "copy" / "copy-one.json").write_text(
        json.dumps({"artifact_id": "copy-one", "product_id": "legacy-one"}), encoding="utf-8"
    )
    migration_db = SqliteDatabase(root / "migration.sqlite3")
    imported = backup_and_import(products, root / "legacy-backup", migration_db)
    repeated = backup_and_import(products, root / "legacy-backup", migration_db)
    exported = export_legacy_layout("legacy-one", root / "legacy-export", migration_db)
    assert imported["success"] and repeated["results"][0]["status"] == "already_imported"
    assert exported["exported_records"] == 2
    checks["legacy_migration"] = True

    restart_db = root / "restart.sqlite3"
    handle_file = root / "restart-handle.json"
    common = f"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, {str(repo / '.hermes' / 'plugins')!r})
from product_creative.contracts.models import IntentDecision
from product_creative.durable_workflow.engine import DurableWorkflowEngine
from product_creative.infrastructure.sqlite.database import SqliteDatabase
from product_creative.infrastructure.sqlite.repositories import SqliteWorkflowRepository
from product_creative.runtime.workflow_catalog import WorkflowDefinition
db=SqliteDatabase(Path({str(restart_db)!r}))
repo=SqliteWorkflowRepository(database=db)
engine=DurableWorkflowEngine(repo, lease_seconds=1)
decision=IntentDecision(product_id='restart-product',action='restart-action',goal='restart',confidence=1,source='explicit_action')
definition=WorkflowDefinition('restart-workflow','1',('restart-action',))
"""
    first_process = common + f"""
h=engine.begin_step('restart-product',definition,decision,{{}},'restart-trace',True)
Path({str(handle_file)!r}).write_text(json.dumps({{'workflow_id':h.workflow_id}}),encoding='utf-8')
os._exit(17)
"""
    result = subprocess.run([sys.executable, "-c", first_process], check=False)
    assert result.returncode == 17 and handle_file.exists()
    time.sleep(1.2)
    second_process = common + """
h=engine.begin_step('restart-product',definition,decision,{},'new-trace',True)
summary=engine.complete_step(h,{'success':True},True)
instances=repo.list('restart-product')
assert len(instances)==1 and instances[0].status.value=='succeeded' and instances[0].steps[0].attempt==2
print(json.dumps(summary))
"""
    subprocess.run([sys.executable, "-c", second_process], check=True, capture_output=True, text=True)
    checks["process_restart"] = True

    migration_db.initialize()
    del migration_db
    os.remove(root / "migration.sqlite3")
    checks["windows_connection_release"] = True

report = {"success": True, "schema_version": "product_creative.durable_runtime_check.v1", "checks": checks}
print(json.dumps(report, ensure_ascii=False, indent=2))
'@

$python | python - $repoRoot
exit $LASTEXITCODE
