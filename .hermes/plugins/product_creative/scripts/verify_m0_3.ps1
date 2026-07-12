[CmdletBinding()]
param(
    [switch]$AllowFallback
)

$ErrorActionPreference = "Stop"

function Get-PowerShellExe {
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) {
        return $pwsh.Source
    }
    return (Get-Command powershell -ErrorAction Stop).Source
}

function Invoke-JsonScript {
    param(
        [string]$ScriptPath,
        [string[]]$InputArgs = @()
    )

    $ps = Get-PowerShellExe
    $output = & $ps -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @InputArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Script failed ($LASTEXITCODE): $ScriptPath $($InputArgs -join ' ')`n$($output | Out-String)"
    }
    return (($output | Out-String).Trim() | ConvertFrom-Json)
}

$verifyM025 = Join-Path $PSScriptRoot "verify_m0_2_5.ps1"
$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$m025Args = @()
if ($AllowFallback) {
    $m025Args += "-AllowFallback"
}

$generated = Invoke-JsonScript -ScriptPath $verifyM025 -InputArgs $m025Args
$statePath = Join-Path (Split-Path (Split-Path (Split-Path $generated.artifact_json -Parent) -Parent) -Parent) "structured\product_state.json"
$stateBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$evaluation = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "evaluate",
    "--id",
    $generated.product_id,
    "--artifact",
    $generated.artifact_json
)
$stateAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$stateChanged = $stateBefore -ne $stateAfter

$passed = [bool](
    $generated.success -and
    $evaluation.success -and
    -not $stateChanged -and
    $evaluation.summary.overall_score -gt 0 -and
    $evaluation.summary.status
)

[pscustomobject]@{
    success = $passed
    product_id = $generated.product_id
    artifact_json = $generated.artifact_json
    evaluation_json = $evaluation.evaluation_json
    evaluation_markdown = $evaluation.evaluation_markdown
    generation_method = $generated.generation_method
    llm_provider = $generated.llm_provider
    llm_model = $generated.llm_model
    evaluation_status = $evaluation.summary.status
    overall_score = $evaluation.summary.overall_score
    best_variant = $evaluation.summary.best_variant
    product_state_changed_by_evaluate = $stateChanged
} | ConvertTo-Json -Depth 6

if (-not $passed) {
    exit 1
}
