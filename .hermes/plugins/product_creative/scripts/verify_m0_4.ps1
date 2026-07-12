[CmdletBinding()]
param(
    [string]$ProductId = "",
    [string]$Artifact = "",
    [int]$Variant = 1
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
if (-not $ProductId -or -not $Artifact) {
    $verifyM03 = Join-Path $PSScriptRoot "verify_m0_3.ps1"
    $m03 = Invoke-JsonScript -ScriptPath $verifyM03
    $ProductId = $m03.product_id
    $Artifact = $m03.artifact_json
}

$base = Join-Path (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path (".hermes\product_creative\products\" + $ProductId)
$statePath = Join-Path $base "structured\product_state.json"
$stateBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$brief = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "brief",
    "--id",
    $ProductId,
    "--artifact",
    $Artifact,
    "--variant",
    ([string]$Variant),
    "--kind",
    "all"
)
$stateAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$stateChanged = $stateBefore -ne $stateAfter

$imageFiles = @($brief.files | Where-Object { $_.brief_type -eq "image" })
$videoFiles = @($brief.files | Where-Object { $_.brief_type -eq "video" })
$imagePayload = if ($imageFiles.Count -gt 0) {
    Get-Content -LiteralPath $imageFiles[0].json -Raw -Encoding UTF8 | ConvertFrom-Json
}
$videoPayload = if ($videoFiles.Count -gt 0) {
    Get-Content -LiteralPath $videoFiles[0].json -Raw -Encoding UTF8 | ConvertFrom-Json
}

$imageOk = $imagePayload -and
    $imagePayload.schema_version -eq "product_creative.image_brief.v0.4.1" -and
    $imagePayload.source_variant -eq $Variant -and
    $imagePayload.generation_contract.prompt -and
    $imagePayload.source_snapshot.product_state_hash
$videoOk = $videoPayload -and
    $videoPayload.schema_version -eq "product_creative.video_brief.v0.4.1" -and
    $videoPayload.source_variant -eq $Variant -and
    @($videoPayload.story.storyboard).Count -gt 0 -and
    $videoPayload.generation_contract.prompt -and
    $videoPayload.source_snapshot.product_state_hash
$passed = [bool]($brief.success -and $imageOk -and $videoOk -and -not $stateChanged)

[pscustomobject]@{
    success = $passed
    product_id = $ProductId
    artifact = $Artifact
    export_id = $brief.export_id
    count = $brief.count
    image_brief = if ($imageFiles.Count -gt 0) { $imageFiles[0].json } else { "" }
    video_brief = if ($videoFiles.Count -gt 0) { $videoFiles[0].json } else { "" }
    image_schema = if ($imagePayload) { $imagePayload.schema_version } else { "" }
    video_schema = if ($videoPayload) { $videoPayload.schema_version } else { "" }
    image_source_hash_present = [bool]($imagePayload -and $imagePayload.source_snapshot.product_state_hash)
    video_source_hash_present = [bool]($videoPayload -and $videoPayload.source_snapshot.product_state_hash)
    product_state_changed_by_brief = $stateChanged
} | ConvertTo-Json -Depth 6

if (-not $passed) {
    exit 1
}
