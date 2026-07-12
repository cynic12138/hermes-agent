[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import ast
import json
import sqlite3
import sys
from pathlib import Path

repo = Path(sys.argv[1])
plugin = repo / ".hermes" / "plugins" / "product_creative"
sys.path.insert(0, str(repo / ".hermes" / "plugins"))

from product_creative.capabilities.registry import action_descriptors, capability_registry, workflow_fragments
from product_creative.cli import CLI_COMMAND_NAMES
from product_creative.tool_catalog import PRODUCT_TOOL_SPECS

failures = []
for removed in [
    plugin / "capabilities" / "legacy.py",
    plugin / "runtime" / "workflow_state_machine.py",
    plugin / "runtime" / "actions" / "__init__.py",
    plugin / "runtime" / "workflows" / "__init__.py",
    plugin / "compatibility" / "legacy_tools.py",
]:
    if removed.exists():
        failures.append(f"legacy_source_exists:{removed.relative_to(plugin)}")

registry = capability_registry()
actions = action_descriptors()
if len(registry) != 9 or len(actions) != 51 or len(workflow_fragments()) != 10:
    failures.append("capability_registry_count")
for name, capability in registry.items():
    executor = plugin / "capabilities" / name / "executor.py"
    descriptor = plugin / "capabilities" / name / "descriptor.py"
    if not executor.exists() or not descriptor.exists() or not capability.actions:
        failures.append(f"incomplete_capability:{name}")

tool_names = [item.name for item in PRODUCT_TOOL_SPECS]
if len(tool_names) != 84 or len(set(tool_names)) != 84 or len(CLI_COMMAND_NAMES) != 84:
    failures.append("public_surface_count")

for relative in [
    Path("application/command_bus.py"),
    Path("application/policy.py"),
    Path("durable_workflow/engine.py"),
    Path("runtime/guard.py"),
    Path("runtime/planning.py"),
]:
    path = plugin / relative
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            source = ast.get_source_segment(path.read_text(encoding="utf-8-sig"), node) or ""
            compares_literal = any(isinstance(comparator, ast.Constant) for comparator in node.comparators)
            if compares_literal and ("action ==" in source or "command ==" in source):
                failures.append(f"central_action_branch:{relative}:{node.lineno}")

for folder in [plugin / "application", plugin / "brain"]:
    for path in folder.rglob("*.py"):
        text = path.read_text(encoding="utf-8-sig")
        for forbidden in ["import sqlite3", "import requests", "import urllib.request"]:
            if forbidden in text:
                failures.append(f"forbidden_dependency:{path.relative_to(plugin)}:{forbidden}")

state_text = (plugin / "runtime" / "state.py").read_text(encoding="utf-8-sig")
evidence_text = (plugin / "runtime" / "evidence.py").read_text(encoding="utf-8-sig")
if "FileSystemWorkflowRepository" in state_text or "glob(" in evidence_text or "read_text(" in evidence_text:
    failures.append("runtime_reads_legacy_state")

db_path = repo / ".hermes" / "product_creative" / "runtime.sqlite3"
connection = sqlite3.connect(db_path)
connection.row_factory = sqlite3.Row
try:
    migrations = connection.execute("SELECT COUNT(*) count FROM schema_migrations").fetchone()["count"]
    failed_imports = connection.execute("SELECT COUNT(*) count FROM legacy_imports WHERE status='failed'").fetchone()["count"]
    completed_imports = connection.execute("SELECT COUNT(*) count FROM legacy_imports WHERE status='completed'").fetchone()["count"]
    tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
finally:
    connection.close()
required_tables = {
    "workflow_instances", "workflow_steps", "workflow_events", "command_receipts",
    "outbox_events", "provider_tasks", "rule_candidates", "writeback_proposals",
    "product_brain_versions", "generation_snapshots", "artifact_records", "material_records",
    "legacy_imports", "migration_backups", "product_leases",
}
if migrations != 9 or required_tables - tables:
    failures.append("sqlite_schema_incomplete")
if completed_imports < 147 or failed_imports:
    failures.append("legacy_migration_incomplete")

report = {
    "success": not failures,
    "schema_version": "product_creative.final_runtime_architecture_check.v1",
    "counts": {
        "capabilities": len(registry),
        "actions": len(actions),
        "workflows": len(workflow_fragments()),
        "tools": len(tool_names),
        "cli_commands": len(CLI_COMMAND_NAMES),
        "migrations": migrations,
        "completed_legacy_imports": completed_imports,
    },
    "failures": failures,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["success"] else 1)
'@

$python | python - $repoRoot
exit $LASTEXITCODE
