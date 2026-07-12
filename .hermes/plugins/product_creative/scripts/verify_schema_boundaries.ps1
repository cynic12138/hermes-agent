[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import ast
import importlib
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
plugin = repo / ".hermes" / "plugins" / "product_creative"
sys.path.insert(0, str(plugin.parent))

from product_creative.capabilities.registry import command_descriptors

failures = []
schema_count = 0
for capability in ("content", "image", "inspiration", "learning", "material", "product", "review", "video"):
    schema_path = plugin / "capabilities" / capability / "schemas.py"
    command_path = plugin / "capabilities" / capability / "commands.py"
    if not schema_path.exists():
        failures.append(f"missing capability schema module: {capability}")
        continue
    tree = ast.parse(schema_path.read_text(encoding="utf-8-sig"))
    assigned = {
        target.id
        for node in tree.body if isinstance(node, ast.Assign)
        for target in node.targets if isinstance(target, ast.Name) and target.id.endswith("_SCHEMA")
    }
    schema_count += len(assigned)
    command_text = command_path.read_text(encoding="utf-8-sig")
    if "from . import schemas" not in command_text:
        failures.append(f"{capability}/commands.py does not import local schemas")
    module = importlib.import_module(f"product_creative.capabilities.{capability}.schemas")
    for descriptor in command_descriptors().values():
        if descriptor.capability != capability:
            continue
        matching = [name for name in assigned if getattr(module, name, None) is descriptor.schema]
        if not matching:
            failures.append(f"{descriptor.name} schema is not owned by {capability}")

for legacy in ("schema_definitions.py", "schema_material.py", "schema_runtime.py"):
    if (plugin / legacy).exists():
        failures.append(f"legacy central schema module remains: {legacy}")

report = {
    "success": not failures and schema_count == 78,
    "schema_version": "product_creative.schema_boundary_check.v2",
    "counts": {"capability_schemas": schema_count, "commands": len(command_descriptors())},
    "failures": failures,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["success"] else 1)
'@

$python | python - $repoRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
