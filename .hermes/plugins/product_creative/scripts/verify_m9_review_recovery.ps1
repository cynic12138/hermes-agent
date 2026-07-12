[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$test = @'
import json
import importlib.util
import sys
import tempfile
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / ".hermes" / "plugins"))

from product_creative.application.command_bus import command_bus
from product_creative.application.console_queries import ProductCreativeConsoleQueries
from product_creative.contracts.durable import CommandEnvelope
from product_creative.infrastructure.sqlite.database import runtime_database, runtime_database_path
from product_creative.workspace import workspace_scope
from fastapi import FastAPI
from fastapi.testclient import TestClient

checks = []

def confirmed_action(command, product_id, payload):
    first = command_bus().dispatch(CommandEnvelope(command=command, product_id=product_id, payload=payload))
    checks.append(first.error_code == "CONFIRMATION_REQUIRED" and bool(first.output.get("confirmation_id")))
    confirmed_payload = {**payload, "confirmed": True, "confirmation_id": first.output["confirmation_id"], "reason": "m9 verification"}
    return command_bus().dispatch(CommandEnvelope(command=command, product_id=product_id, confirmed=True, payload=confirmed_payload))

with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
    roots = [Path(first), Path(second)]
    paths = []
    for index, root in enumerate(roots):
        with workspace_scope(root):
            database = runtime_database()
            paths.append(runtime_database_path())
            with database.read_session() as connection:
                checks.append(connection.execute("SELECT MAX(version) value FROM schema_migrations").fetchone()["value"] == 9)
                columns = {row["name"] for row in connection.execute("PRAGMA table_info(confirmations)")}
                checks.append({"decision", "actor", "expected_version", "result_json", "updated_at"} <= columns)
            product_id = f"product-{index}"
            product = root / ".hermes" / "product_creative" / "products" / product_id
            product.mkdir(parents=True)
            with database.transaction() as connection:
                now = "2026-01-01T00:00:00+00:00"
                connection.execute("INSERT INTO products(product_id,workspace_path,created_at,updated_at) VALUES(?,?,?,?)", (product_id,str(product),now,now))
                connection.execute("INSERT INTO product_brain_versions(brain_version_id,product_id,version,state_json,content_hash,status,created_at,change_kind,trace_id) VALUES(?,?,1,'{}','x','current',?,'initial','')", (f"brain-{index}",product_id,now))
                connection.execute("INSERT INTO writeback_proposals(proposal_id,product_id,status,risk_level,payload_json,created_at,updated_at) VALUES(?,?, 'proposed','medium',?,?,?)", (f"proposal-{index}",product_id,json.dumps({"proposal_id":f"proposal-{index}","product_id":product_id,"status":"proposed","updates":[]}),now,now))
            confirmed = confirmed_action("product_proposal_decide", product_id, {"product_id":product_id,"proposal_id":f"proposal-{index}","decision":"reject","expected_version":1})
            checks.append(confirmed.success)
            if index == 0:
                rollback = confirmed_action("product_brain_rollback", product_id, {"product_id":product_id,"target_version":1,"expected_version":1})
                checks.append(rollback.success and rollback.output["brain_version"]["version"] == 2)
                with database.transaction() as connection:
                    rule = {"rule_id":"rule-0","product_id":product_id,"status":"candidate","scope":"product_brain","target_path":"tone","risk_level":"level_2","sample_size":1,"confidence":0.5}
                    connection.execute("INSERT INTO rule_candidates(rule_id,product_id,conflict_key,scope,target_path,status,risk_level,sample_size,confidence,payload_json,created_at,updated_at) VALUES('rule-0',?,'tone','product_brain','tone','candidate','level_2',1,0.5,?,?,?)", (product_id,json.dumps(rule),now,now))
                    connection.execute("INSERT INTO workflow_instances(workflow_id,product_id,definition,definition_version,trace_id,status,current_step,intent_json,pause_reason,created_at,updated_at,version) VALUES('workflow-0',?,'test','1','trace-0','failed',0,'{}','failed',?,?,1)", (product_id,now,now))
                    connection.execute("INSERT INTO workflow_steps(workflow_id,position,step_id,action,status,args_json,output_json,attempt,idempotency_key,error_code,error_message) VALUES('workflow-0',0,'step-0','test_action','failed','{}','{}',1,'workflow-0:0','TEST','failed')")
                    connection.execute("INSERT INTO provider_tasks(provider_task_id,product_id,workflow_id,step_id,provider,kind,external_task_id,idempotency_key,status,request_json,response_json,created_at,updated_at,attempt) VALUES('provider-task-0',?,'workflow-0','step-0','mock','image','external-0','provider-key-0','completed','{}','{}',?,?,1)", (product_id,now,now))
                revoked = confirmed_action("product_rule_revoke", product_id, {"product_id":product_id,"rule_id":"rule-0"})
                checks.append(revoked.success and revoked.output["rule"]["status"] == "revoked")
                retried = confirmed_action("product_workflow_retry", product_id, {"product_id":product_id,"workflow_id":"workflow-0","expected_version":1})
                checks.append(retried.success and retried.output["status"] == "paused" and retried.output["version"] == 2)
                cancelled = confirmed_action("product_workflow_cancel", product_id, {"product_id":product_id,"workflow_id":"workflow-0","expected_version":2})
                checks.append(cancelled.success and cancelled.output["status"] == "cancelled" and cancelled.output["version"] == 3)
                refreshed = confirmed_action("product_provider_task_refresh", product_id, {"product_id":product_id,"provider_task_id":"provider-task-0"})
                checks.append(refreshed.success and refreshed.output["status"] == "completed" and refreshed.output["refreshed"])
                with database.read_session() as connection:
                    event_types = [row["event_type"] for row in connection.execute("SELECT event_type FROM workflow_events WHERE workflow_id='workflow-0' ORDER BY sequence")]
                    audit_count = connection.execute("SELECT COUNT(*) value FROM recovery_events WHERE product_id=?", (product_id,)).fetchone()["value"]
                checks.append(event_types == ["workflow.retry_requested", "workflow.cancelled"] and audit_count == 6)
            products = ProductCreativeConsoleQueries().products()
            checks.append([item["product_id"] for item in products] == [product_id])
    checks.append(paths[0] != paths[1] and all(path.is_relative_to(root) for path, root in zip(paths, roots)))

    api_path = repo / ".hermes" / "plugins" / "product_creative" / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location("product_creative_m9_api_test", api_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/product_creative")
    client = TestClient(app)
    base_url = "/api/plugins/product_creative/v1"
    checks.append(client.get(f"{base_url}/health").status_code == 422)
    checks.append(client.get(f"{base_url}/health", headers={"X-Hermes-Workspace-Root": first}).status_code == 200)
    checks.append(client.get(f"{base_url}/media/not-a-record", headers={"X-Hermes-Workspace-Root": first}).status_code == 404)

report = {"success": all(checks), "schema_version": "product_creative.m9_review_recovery_check.v1", "checks": len(checks), "passed": sum(checks)}
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["success"] else 1)
'@

$test | python - $repoRoot
exit $LASTEXITCODE
