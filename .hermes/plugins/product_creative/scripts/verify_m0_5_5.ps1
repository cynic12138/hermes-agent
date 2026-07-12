[CmdletBinding()]
param(
    [string]$ProductId = "",
    [string]$Artifact = "",
    [int]$Variant = 1,
    [string]$Preset = "xiaohongshu-cover",
    [string]$Provider = "generic"
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

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$verifyM051 = Join-Path $PSScriptRoot "verify_m0_5_1.ps1"
$verifyArgs = @(
    "-Variant",
    ([string]$Variant),
    "-Preset",
    $Preset,
    "-Provider",
    $Provider
)
if ($ProductId) {
    $verifyArgs += @("-ProductId", $ProductId)
}
if ($Artifact) {
    $verifyArgs += @("-Artifact", $Artifact)
}

$m051 = Invoke-JsonScript -ScriptPath $verifyM051 -InputArgs $verifyArgs
$ProductId = $m051.product_id
$base = Join-Path (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path (".hermes\product_creative\products\" + $ProductId)
$m051ImageJob = Get-Content -LiteralPath $m051.image_job -Raw -Encoding UTF8 | ConvertFrom-Json
$imagePayloadPath = Join-Path $base $m051ImageJob.source_payload_path
$statePath = Join-Path $base "structured\product_state.json"
$stateBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash

$initialManifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "artifact-manifest",
    "--id",
    $ProductId
)
$review = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "review-package",
    "--id",
    $ProductId,
    "--job",
    $m051.image_job
)
$feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "result-feedback",
    "--id",
    $ProductId,
    "--result",
    $m051.image_result,
    "--note",
    "M0.5.4 contract verification feedback.",
    "--rating",
    "4",
    "--issue",
    "mock result only"
)
$readiness = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "live-readiness",
    "--id",
    $ProductId,
    "--provider",
    $Provider,
    "--kind",
    "image",
    "--payload",
    $imagePayloadPath
)
$finalManifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "artifact-manifest",
    "--id",
    $ProductId
)
$stateAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$stateChanged = $stateBefore -ne $stateAfter

$reviewPayload = Get-Content -LiteralPath $review.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$feedbackPayload = Get-Content -LiteralPath $feedback.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$readinessPayload = Get-Content -LiteralPath $readiness.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$manifestPayload = Get-Content -LiteralPath $finalManifest.files.json -Raw -Encoding UTF8 | ConvertFrom-Json

$manifestOk = $initialManifest.success -and
    $finalManifest.success -and
    $manifestPayload.schema_version -eq "product_creative.artifact_manifest.v0.5.2" -and
    $finalManifest.artifact_count -ge $initialManifest.artifact_count -and
    (Test-Path -LiteralPath $finalManifest.files.jsonl)
$reviewOk = $review.success -and
    $reviewPayload.schema_version -eq "product_creative.review_package.v0.5.3" -and
    $reviewPayload.status -eq "ready_for_review" -and
    (Test-Path -LiteralPath $review.files.markdown)
$feedbackOk = $feedback.success -and
    $feedbackPayload.schema_version -eq "product_creative.result_feedback.v7.3" -and
    $feedbackPayload.status -eq "recorded" -and
    -not $feedbackPayload.eligible_for_evolution_proposal -and
    (Test-Path -LiteralPath $feedback.files.markdown)
$readinessOk = $readiness.success -and
    $readinessPayload.schema_version -eq "product_creative.live_readiness.v0.5.5" -and
    $readinessPayload.status -eq "blocked" -and
    -not $readinessPayload.ready_for_live -and
    -not $readinessPayload.external_call_performed -and
    (Test-Path -LiteralPath $readiness.files.markdown)
$passed = [bool]($m051.success -and $manifestOk -and $reviewOk -and $feedbackOk -and $readinessOk -and -not $stateChanged)

[pscustomobject]@{
    success = $passed
    product_id = $ProductId
    provider = $Provider
    initial_manifest_count = $initialManifest.artifact_count
    final_manifest_count = $finalManifest.artifact_count
    manifest_schema = $manifestPayload.schema_version
    review_package = $review.files.json
    feedback = $feedback.files.json
    live_readiness = $readiness.files.json
    review_schema = $reviewPayload.schema_version
    feedback_schema = $feedbackPayload.schema_version
    readiness_schema = $readinessPayload.schema_version
    readiness_status = $readinessPayload.status
    ready_for_live = $readinessPayload.ready_for_live
    external_call_performed = $readinessPayload.external_call_performed
    product_state_changed_by_m0_5_x = $stateChanged
} | ConvertTo-Json -Depth 6

if (-not $passed) {
    exit 1
}
