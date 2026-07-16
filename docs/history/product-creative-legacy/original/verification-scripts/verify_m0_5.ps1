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
$verifyM041 = Join-Path $PSScriptRoot "verify_m0_4_1.ps1"
$verifyArgs = @(
    "-Variant",
    ([string]$Variant),
    "-Preset",
    $Preset
)
if ($ProductId) {
    $verifyArgs += @("-ProductId", $ProductId)
}
if ($Artifact) {
    $verifyArgs += @("-Artifact", $Artifact)
}

$briefResult = Invoke-JsonScript -ScriptPath $verifyM041 -InputArgs $verifyArgs
$ProductId = $briefResult.product_id
$base = Join-Path (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path (".hermes\product_creative\products\" + $ProductId)
$statePath = Join-Path $base "structured\product_state.json"
$stateBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash

$imageResult = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "image-generate",
    "--id",
    $ProductId,
    "--brief",
    $briefResult.image_brief,
    "--provider",
    $Provider
)
$videoResult = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "video-generate",
    "--id",
    $ProductId,
    "--brief",
    $briefResult.video_brief,
    "--provider",
    $Provider
)
$stateAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$stateChanged = $stateBefore -ne $stateAfter

$imagePayload = Get-Content -LiteralPath $imageResult.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$videoPayload = Get-Content -LiteralPath $videoResult.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$imageOk = $imagePayload.schema_version -eq "product_creative.provider_payload.v0.5" -and
    $imagePayload.mode -eq "dry_run" -and
    -not $imagePayload.external_call_performed -and
    $imagePayload.brief_type -eq "image" -and
    $imagePayload.request.prompt
$videoOk = $videoPayload.schema_version -eq "product_creative.provider_payload.v0.5" -and
    $videoPayload.mode -eq "dry_run" -and
    -not $videoPayload.external_call_performed -and
    $videoPayload.brief_type -eq "video" -and
    $videoPayload.request.prompt -and
    @($videoPayload.request.storyboard).Count -gt 0
$passed = [bool]($briefResult.success -and $imageResult.success -and $videoResult.success -and $imageOk -and $videoOk -and -not $stateChanged)

[pscustomobject]@{
    success = $passed
    product_id = $ProductId
    provider = $Provider
    preset = $Preset
    image_payload = $imageResult.files.json
    video_payload = $videoResult.files.json
    image_markdown = $imageResult.files.markdown
    video_markdown = $videoResult.files.markdown
    image_schema = $imagePayload.schema_version
    video_schema = $videoPayload.schema_version
    image_mode = $imagePayload.mode
    video_mode = $videoPayload.mode
    image_external_call_performed = $imagePayload.external_call_performed
    video_external_call_performed = $videoPayload.external_call_performed
    product_state_changed_by_provider_payload = $stateChanged
} | ConvertTo-Json -Depth 6

if (-not $passed) {
    exit 1
}
