[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [string]$ExpectedVersion = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonArgs = @(
    (Join-Path $scriptDir "export_distribution.py"),
    "--output-directory",
    $OutputDirectory
)
if ($ExpectedVersion) {
    $pythonArgs += @("--expected-version", $ExpectedVersion)
}

& python @pythonArgs
if ($LASTEXITCODE -ne 0) {
    throw "Product Creative distribution export failed"
}
