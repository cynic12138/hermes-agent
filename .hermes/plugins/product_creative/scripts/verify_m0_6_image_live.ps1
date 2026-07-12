[CmdletBinding()]
param(
    [string]$ProductId = "",
    [string]$Artifact = "",
    [int]$Variant = 1,
    [string]$Preset = "xiaohongshu-cover",
    [string]$Provider = "volcengine-ark-image"
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

if (-not [Environment]::GetEnvironmentVariable("PRODUCT_CREATIVE_ARK_API_KEY", "Process") -and
    -not [Environment]::GetEnvironmentVariable("PRODUCT_CREATIVE_ARK_API_KEY", "User")) {
    throw "PRODUCT_CREATIVE_ARK_API_KEY is required for M0.6 live image verification."
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
if (-not $ProductId -or -not $Artifact) {
    $verifyM03 = Join-Path $PSScriptRoot "verify_m0_3.ps1"
    $m03 = Invoke-JsonScript -ScriptPath $verifyM03
    $ProductId = $m03.product_id
    $Artifact = $m03.artifact_json
}

$base = Join-Path (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path (".hermes\product_creative\products\" + $ProductId)
$statePath = Join-Path $base "structured\product_state.json"

$brief = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "brief",
    "--id",
    $ProductId,
    "--artifact",
    $Artifact,
    "--variant",
    ([string]$Variant),
    "--kind",
    "image",
    "--preset",
    $Preset
)
$imageFiles = @($brief.files | Where-Object { $_.brief_type -eq "image" })
if ($imageFiles.Count -lt 1) {
    throw "No image brief was generated."
}

$payload = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "image-generate",
    "--id",
    $ProductId,
    "--brief",
    $imageFiles[0].json,
    "--provider",
    $Provider
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
    $payload.files.json
)
if (-not $readiness.ready_for_live) {
    throw "Provider is not ready for live image generation: $($readiness.blockers -join '; ')"
}

$stateBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$job = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "generation-job",
    "--id",
    $ProductId,
    "--payload",
    $payload.files.json,
    "--provider",
    $Provider,
    "--mode",
    "live"
)
$stateAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$stateChanged = $stateBefore -ne $stateAfter

$jobPayload = Get-Content -LiteralPath $job.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$resultPayload = Get-Content -LiteralPath $job.result_files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$imageOutputRel = $resultPayload.outputs[0].path
$imageOutput = Join-Path $base $imageOutputRel

$review = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "review-package",
    "--id",
    $ProductId,
    "--job",
    $job.files.json
)
$feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "result-feedback",
    "--id",
    $ProductId,
    "--result",
    $job.result_files.json,
    "--note",
    "M0.6 live image verification feedback placeholder.",
    "--rating",
    "4",
    "--issue",
    "live verification only"
)
$manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "artifact-manifest",
    "--id",
    $ProductId
)

$imageExists = Test-Path -LiteralPath $imageOutput
$imageBytes = if ($imageExists) { (Get-Item -LiteralPath $imageOutput).Length } else { 0 }
$passed = [bool](
    $brief.success -and
    $payload.success -and
    $readiness.ready_for_live -and
    $job.success -and
    $jobPayload.schema_version -eq "product_creative.generation_job.v0.5.1" -and
    $jobPayload.status -eq "completed" -and
    $jobPayload.external_call_performed -and
    $resultPayload.schema_version -eq "product_creative.generation_result.v0.5.1" -and
    $resultPayload.status -eq "completed" -and
    $resultPayload.external_call_performed -and
    $imageExists -and
    $imageBytes -gt 0 -and
    $review.success -and
    $feedback.success -and
    $manifest.success -and
    -not $stateChanged
)

[pscustomobject]@{
    success = $passed
    product_id = $ProductId
    provider = $Provider
    preset = $Preset
    live_call_count = 1
    image_brief = $imageFiles[0].json
    provider_payload = $payload.files.json
    readiness = $readiness.files.json
    generation_job = $job.files.json
    image_result = $job.result_files.json
    image_file = $imageOutput
    image_bytes = $imageBytes
    review_package = $review.files.json
    result_feedback = $feedback.files.json
    manifest = $manifest.files.json
    job_status = $jobPayload.status
    result_status = $resultPayload.status
    external_call_performed = $jobPayload.external_call_performed -and $resultPayload.external_call_performed
    product_state_changed_by_live_image = $stateChanged
} | ConvertTo-Json -Depth 6

if (-not $passed) {
    exit 1
}
