[CmdletBinding()]
param(
    [string]$ProductId = "m025-verify-20260703-145418",
    [string]$Artifact = "",
    [string]$LiveResult = "",
    [int]$Variant = 1,
    [string]$Preset = "xiaohongshu-cover"
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

function Get-LatestJsonPath {
    param(
        [string]$Folder,
        [scriptblock]$Filter
    )

    if (-not (Test-Path -LiteralPath $Folder)) {
        return ""
    }
    $matches = @()
    foreach ($file in Get-ChildItem -LiteralPath $Folder -Filter "*.json" | Sort-Object LastWriteTime) {
        try {
            $payload = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        catch {
            continue
        }
        if (& $Filter $payload) {
            $matches += $file.FullName
        }
    }
    if ($matches.Count -eq 0) {
        return ""
    }
    return $matches[-1]
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$base = Join-Path $repoRoot (".hermes\product_creative\products\" + $ProductId)

if (-not (Test-Path -LiteralPath $base)) {
    $verifyM03 = Join-Path $PSScriptRoot "verify_m0_3.ps1"
    $m03 = Invoke-JsonScript -ScriptPath $verifyM03
    $ProductId = $m03.product_id
    $Artifact = $m03.artifact_json
    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $ProductId)
}

if (-not $Artifact) {
    $Artifact = Get-LatestJsonPath -Folder (Join-Path $base "artifacts\copy") -Filter {
        param($payload)
        return [string]$payload.artifact_id -like "copy-pack-*"
    }
}
if (-not $Artifact) {
    throw "No copy-pack artifact found for $ProductId."
}

if (-not $LiveResult) {
    $LiveResult = Get-LatestJsonPath -Folder (Join-Path $base "artifacts\generated_images") -Filter {
        param($payload)
        return [bool]($payload.external_call_performed -and $payload.status -eq "completed")
    }
}
if (-not $LiveResult) {
    throw "No existing live image result found for $ProductId. Run verify_m0_6_image_live.ps1 once or pass -LiveResult."
}

$statePath = Join-Path $base "structured\product_state.json"
$stateBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash

$run = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "creative-run",
    "--id",
    $ProductId,
    "--artifact",
    $Artifact,
    "--variant",
    ([string]$Variant),
    "--preset",
    $Preset,
    "--provider",
    "generic",
    "--mode",
    "mock",
    "--count",
    "2"
)

$runPayload = Get-Content -LiteralPath $run.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$comparisonPath = Join-Path $base $runPayload.artifacts.comparison_package.path
$comparisonPayload = Get-Content -LiteralPath $comparisonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$imageBriefPath = Join-Path $base $runPayload.artifacts.image_brief.path

$adaptedPayload = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "image-generate",
    "--id",
    $ProductId,
    "--brief",
    $imageBriefPath,
    "--provider",
    "volcengine-ark-image"
)
$adaptedPayloadDoc = Get-Content -LiteralPath $adaptedPayload.files.json -Raw -Encoding UTF8 | ConvertFrom-Json

$qa = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "image-qa",
    "--id",
    $ProductId,
    "--result",
    $LiveResult
)

$feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "result-feedback",
    "--id",
    $ProductId,
    "--result",
    $LiveResult,
    "--note",
    "M0.6.3 selected live image for evolution proposal.",
    "--selected",
    "--rating",
    "5",
    "--allow-evolve",
    "--issue",
    "verification selected result"
)

$proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "evolve",
    "--id",
    $ProductId
)

$manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "artifact-manifest",
    "--id",
    $ProductId
)

$stateAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $statePath).Hash
$stateChanged = $stateBefore -ne $stateAfter
$passed = [bool](
    $run.success -and
    $runPayload.schema_version -eq "product_creative.creative_run.v0.6.6" -and
    $runPayload.count -eq 2 -and
    $runPayload.external_call_count -eq 0 -and
    $comparisonPayload.schema_version -eq "product_creative.comparison_package.v0.6.4" -and
    $comparisonPayload.count -eq 2 -and
    $adaptedPayload.success -and
    $adaptedPayloadDoc.request.prompt_adapter.schema_version -eq "product_creative.prompt_adapter.v0.6.5" -and
    $adaptedPayloadDoc.request.prompt_adapter.provider -eq "volcengine-ark-image" -and
    $adaptedPayloadDoc.external_call_performed -eq $false -and
    $qa.success -and
    $qa.qa.schema_version -eq "product_creative.image_qa.v0.6.2" -and
    $feedback.success -and
    $feedback.eligible_for_evolution_proposal -and
    $proposal.success -and
    $proposal.proposal.source_result_id -and
    $manifest.success -and
    -not $stateChanged
)

[pscustomobject]@{
    success = $passed
    product_id = $ProductId
    live_call_count = 0
    copy_pack = $Artifact
    reused_live_result = $LiveResult
    creative_run = $run.files.json
    creative_run_status = $runPayload.status
    comparison_package = $comparisonPath
    adapted_provider_payload = $adaptedPayload.files.json
    image_qa = $qa.files.json
    image_qa_status = $qa.status
    result_feedback = $feedback.files.json
    evolution_proposal = $proposal.proposal_path
    manifest = $manifest.files.json
    product_state_changed_by_m0_6_5 = $stateChanged
} | ConvertTo-Json -Depth 8

if (-not $passed) {
    exit 1
}
