[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import hashlib
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / ".hermes" / "plugins"))

from product_creative.cli import CLI_COMMAND_NAMES
from product_creative.tool_catalog import PRODUCT_TOOL_SPECS

payload = {
    "tools": [{"name": item.name, "schema": item.schema} for item in PRODUCT_TOOL_SPECS],
    "cli": list(CLI_COMMAND_NAMES),
}
serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
actual = hashlib.sha256(serialized).hexdigest()
expected = "a08dcd2b152e51fd1ff90b9ff8bb51f8e05c1b561a30c8b12f7b57c0c4c14614"
report = {
    "success": actual == expected and len(payload["tools"]) == 78 and len(payload["cli"]) == 78,
    "schema_version": "product_creative.public_surface_golden.v1",
    "expected_sha256": expected,
    "actual_sha256": actual,
    "tool_count": len(payload["tools"]),
    "cli_count": len(payload["cli"]),
}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["success"] else 1)
'@

$python | python - $repoRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
