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
$verifyM05 = Join-Path $PSScriptRoot "verify_m0_5.ps1"
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

$m05 = Invoke-JsonScript -ScriptPath $verifyM05 -InputArgs $verifyArgs
$ProductId = $m05.product_id
$base = Join-Path (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path (".hermes\product_creative\products\" + $ProductId)
$statePath = Join-Path $base "structured\product_state.json"
$stateBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash

$providerList = Invoke-JsonScript -ScriptPath $runner -InputArgs @("provider-list")
$imageValidation = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "provider-validate",
    "--id",
    $ProductId,
    "--payload",
    $m05.image_payload,
    "--provider",
    $Provider
)
$imageJob = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "generation-job",
    "--id",
    $ProductId,
    "--payload",
    $m05.image_payload,
    "--provider",
    $Provider,
    "--mode",
    "mock"
)
$videoJob = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "generation-job",
    "--id",
    $ProductId,
    "--payload",
    $m05.video_payload,
    "--provider",
    $Provider,
    "--mode",
    "mock"
)
$stateAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$stateChanged = $stateBefore -ne $stateAfter

$imageJobPayload = Get-Content -LiteralPath $imageJob.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$videoJobPayload = Get-Content -LiteralPath $videoJob.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$imageResultPayload = Get-Content -LiteralPath $imageJob.result_files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$videoResultPayload = Get-Content -LiteralPath $videoJob.result_files.json -Raw -Encoding UTF8 | ConvertFrom-Json

$providerOk = $providerList.success -and @($providerList.providers).Count -gt 0
$validationOk = $imageValidation.success -and
    $imageValidation.validation.schema_version -eq "product_creative.provider_validation.v0.5.1" -and
    $imageValidation.status -eq "valid"
$imageJobOk = $imageJob.success -and
    $imageJobPayload.schema_version -eq "product_creative.generation_job.v0.5.1" -and
    $imageJobPayload.status -eq "mocked" -and
    -not $imageJobPayload.external_call_performed -and
    $imageResultPayload.schema_version -eq "product_creative.generation_result.v0.5.1" -and
    $imageResultPayload.status -eq "mocked" -and
    -not $imageResultPayload.external_call_performed
$videoJobOk = $videoJob.success -and
    $videoJobPayload.schema_version -eq "product_creative.generation_job.v0.5.1" -and
    $videoJobPayload.status -eq "mocked" -and
    -not $videoJobPayload.external_call_performed -and
    $videoResultPayload.schema_version -eq "product_creative.generation_result.v0.5.1" -and
    $videoResultPayload.status -eq "mocked" -and
    -not $videoResultPayload.external_call_performed
$filesOk = (Test-Path -LiteralPath $imageJob.files.markdown) -and
    (Test-Path -LiteralPath $videoJob.files.markdown) -and
    (Test-Path -LiteralPath $imageJob.result_files.markdown) -and
    (Test-Path -LiteralPath $videoJob.result_files.markdown)
$passed = [bool]($m05.success -and $providerOk -and $validationOk -and $imageJobOk -and $videoJobOk -and $filesOk -and -not $stateChanged)

[pscustomobject]@{
    success = $passed
    product_id = $ProductId
    provider = $Provider
    provider_count = $providerList.count
    validation_id = $imageValidation.validation_id
    validation_status = $imageValidation.status
    image_job = $imageJob.files.json
    video_job = $videoJob.files.json
    image_result = $imageJob.result_files.json
    video_result = $videoJob.result_files.json
    image_job_schema = $imageJobPayload.schema_version
    video_job_schema = $videoJobPayload.schema_version
    image_result_schema = $imageResultPayload.schema_version
    video_result_schema = $videoResultPayload.schema_version
    image_external_call_performed = $imageJobPayload.external_call_performed -or $imageResultPayload.external_call_performed
    video_external_call_performed = $videoJobPayload.external_call_performed -or $videoResultPayload.external_call_performed
    product_state_changed_by_generation_job = $stateChanged
} | ConvertTo-Json -Depth 6

if (-not $passed) {
    exit 1
}
