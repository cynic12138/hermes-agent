[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$OutputDirectory)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path
$pluginRoot = Join-Path $repoRoot ".hermes\plugins\product_creative"
$output = [IO.Path]::GetFullPath($OutputDirectory)

if (Test-Path -LiteralPath $output) { Remove-Item -LiteralPath $output -Recurse -Force }
New-Item -ItemType Directory -Path $output | Out-Null

$tracked = git -C $repoRoot ls-files --cached --others --exclude-standard -- ".hermes/plugins/product_creative"
foreach ($entry in $tracked) {
    if ($entry -match '(^|/)(__pycache__|\.pytest_cache|runtime_data)(/|$)' -or $entry -match '\.(pyc|sqlite3|db)$') { continue }
    $relative = $entry.Substring(".hermes/plugins/product_creative/".Length)
    $source = Join-Path $repoRoot ($entry -replace '/', '\')
    $target = Join-Path $output ($relative -replace '/', '\')
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $target
}

Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination (Join-Path $output "LICENSE")
$sourceCommit = (git -C $repoRoot rev-parse HEAD).Trim()
@{ source_repository = "cynic12138/hermes-agent"; source_commit = $sourceCommit; generated_at = [DateTime]::UtcNow.ToString("o") } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output "SOURCE.json") -Encoding utf8

$forbidden = Get-ChildItem -LiteralPath $output -Recurse -File | Where-Object {
    $_.Name -match '\.(sqlite3|db|pyc)$' -or $_.FullName -match '__pycache__|\.hermes[\\/]product_creative[\\/]products'
}
if ($forbidden) { throw "Distribution contains forbidden runtime files: $($forbidden.FullName -join ', ')" }

Write-Output $output
