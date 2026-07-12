[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
@'
import importlib
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
plugin = repo / ".hermes" / "plugins" / "product_creative"
sys.path.insert(0, str(plugin.parent))

expected = {
    "product_creative.capabilities.product.workspace_service": ["create_product", "resolve_product_workspace"],
    "product_creative.capabilities.product.ingestion_service": ["ingest_product"],
    "product_creative.capabilities.product.context_service": ["context_pack"],
    "product_creative.capabilities.learning.feedback_repository": ["record_feedback", "read_result_feedback_entries", "read_channel_feedback_entries"],
    "product_creative.capabilities.learning.writeback_service": ["evolve_product", "apply_proposal"],
    "product_creative.capabilities.material.asset_service": ["register_material_asset", "list_material_assets"],
}
failures = []
count = 0
for module_name, names in expected.items():
    module = importlib.import_module(module_name)
    for name in names:
        count += 1
        if not callable(getattr(module, name, None)):
            failures.append(f"{module_name}.{name}")
for legacy in ("store_workspace.py", "store_ingestion.py", "store_feedback.py", "store_evolution.py", "materials.py"):
    if (plugin / legacy).exists():
        failures.append(f"legacy module remains: {legacy}")
report = {"success": not failures, "schema_version": "product_creative.product_brain_boundary_check.v3", "counts": {"service_functions": count}, "failures": failures}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["success"] else 1)
'@ | python - $repoRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
