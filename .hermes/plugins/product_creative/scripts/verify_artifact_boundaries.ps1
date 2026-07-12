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
    "product_creative.capabilities.review.manifest_service": ["rebuild_artifact_manifest"],
    "product_creative.capabilities.review.image_qa_service": ["qa_image_result"],
    "product_creative.capabilities.review.review_package_service": ["create_review_package", "create_comparison_package"],
    "product_creative.capabilities.review.channel_review_service": ["create_channel_review_package"],
    "product_creative.capabilities.learning.feedback_service": ["record_result_feedback", "record_channel_feedback", "record_video_brief_feedback"],
}
failures = []
count = 0
for module_name, names in expected.items():
    module = importlib.import_module(module_name)
    for name in names:
        count += 1
        if not callable(getattr(module, name, None)):
            failures.append(f"{module_name}.{name}")
for legacy in ("artifacts.py", "artifact_manifest.py", "artifact_feedback.py"):
    if (plugin / legacy).exists():
        failures.append(f"legacy module remains: {legacy}")
report = {"success": not failures, "schema_version": "product_creative.artifact_boundary_check.v2", "counts": {"service_functions": count}, "failures": failures}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["success"] else 1)
'@ | python - $repoRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
