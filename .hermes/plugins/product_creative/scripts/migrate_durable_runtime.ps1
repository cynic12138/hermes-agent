[CmdletBinding()]
param(
    [string]$SourceRoot = "",
    [string]$BackupRoot = "",
    [switch]$ReindexOnly
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / ".hermes" / "plugins"))
from product_creative.migrations import backup_and_import, reindex_legacy_metadata

source = Path(sys.argv[2]) if sys.argv[2] != "-" else None
backup = Path(sys.argv[3]) if sys.argv[3] != "-" else None
result = reindex_legacy_metadata(source) if sys.argv[4] == "1" else backup_and_import(source, backup)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["success"] else 1)
'@

$sourceArg = if ($SourceRoot) { $SourceRoot } else { "-" }
$backupArg = if ($BackupRoot) { $BackupRoot } else { "-" }
$reindexArg = if ($ReindexOnly) { "1" } else { "0" }
$python | python - $repoRoot $sourceArg $backupArg $reindexArg
exit $LASTEXITCODE
