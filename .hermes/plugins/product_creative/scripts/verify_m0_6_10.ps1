[CmdletBinding()]
param(
    [string]$ProductId = "m025-verify-20260703-145418",
    [string]$Artifact = "",
    [int]$Variant = 1,
    [string]$Preset = "xiaohongshu-cover",
    [string]$Provider = "volcengine-ark-image",
    [switch]$SkipLive
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

function Get-StateHash {
    param([string]$Base)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Base "structured\product_state.json")).Hash
}

if (-not $SkipLive) {
    if (-not [Environment]::GetEnvironmentVariable("PRODUCT_CREATIVE_ARK_API_KEY", "Process") -and
        -not [Environment]::GetEnvironmentVariable("PRODUCT_CREATIVE_ARK_API_KEY", "User")) {
        throw "PRODUCT_CREATIVE_ARK_API_KEY is required for live M0.6.10 verification. Use -SkipLive only for non-live checks."
    }
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$base = Join-Path $repoRoot (".hermes\product_creative\products\" + $ProductId)

if (-not (Test-Path -LiteralPath $base)) {
    $verifyM03 = Join-Path $PSScriptRoot "verify_m0_3.ps1"
    $m03 = Invoke-JsonScript -ScriptPath $verifyM03 -InputArgs @("-AllowFallback")
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

$stateBeforeRun = Get-StateHash -Base $base
$liveCallCount = 0
if ($SkipLive) {
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
}
else {
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
        $Provider,
        "--mode",
        "live",
        "--count",
        "1"
    )
    $liveCallCount = 1
}
$stateAfterRun = Get-StateHash -Base $base
$stateChangedByRun = $stateBeforeRun -ne $stateAfterRun
$runPayload = Get-Content -LiteralPath $run.files.json -Raw -Encoding UTF8 | ConvertFrom-Json

$firstJob = @($runPayload.jobs)[0]
$resultPath = if ($firstJob.result_path) { Join-Path $base $firstJob.result_path } else { "" }
if (-not $resultPath -or -not (Test-Path -LiteralPath $resultPath)) {
    $resultPath = Get-LatestJsonPath -Folder (Join-Path $base "artifacts\generated_images") -Filter {
        param($payload)
        return [bool](((-not $SkipLive) -and $payload.external_call_performed -or $SkipLive) -and $payload.status -eq "completed")
    }
}
if (-not $resultPath) {
    throw "No generated image result available for feedback verification."
}

$feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "result-feedback",
    "--id",
    $ProductId,
    "--result",
    $resultPath,
    "--note",
    "M0.6.7 structured feedback prefers clear subject, clean composition, 高级质感, 不要太促销.",
    "--selected",
    "--rating",
    "5",
    "--allow-evolve",
    "--subject-clarity",
    "5",
    "--product-recognizability",
    "5",
    "--composition",
    "4",
    "--style-fit",
    "5",
    "--copy-fit",
    "4",
    "--issue",
    "verification structured learning",
    "--dislike-reason",
    "avoid generated text"
)
$feedbackPayload = Get-Content -LiteralPath $feedback.files.json -Raw -Encoding UTF8 | ConvertFrom-Json

$proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "evolve",
    "--id",
    $ProductId
)
$proposalPayload = Get-Content -LiteralPath $proposal.proposal_path -Raw -Encoding UTF8 | ConvertFrom-Json
$stateBeforeApply = Get-StateHash -Base $base
$apply = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "evolve",
    "--id",
    $ProductId,
    "--apply",
    $proposal.proposal_id
)
$stateAfterApply = Get-StateHash -Base $base
$stateChangedByApply = $stateBeforeApply -ne $stateAfterApply

$imageBriefPath = Join-Path $base $runPayload.artifacts.image_brief.path
$adaptedPayload = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "image-generate",
    "--id",
    $ProductId,
    "--brief",
    $imageBriefPath,
    "--provider",
    $Provider
)
$adaptedPayloadDoc = Get-Content -LiteralPath $adaptedPayload.files.json -Raw -Encoding UTF8 | ConvertFrom-Json
$learningSnapshot = $adaptedPayloadDoc.request.prompt_adapter.learning_snapshot

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$multiA = "m0610-general-a-$stamp"
$multiB = "m0610-general-b-$stamp"
$createA = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $multiA, "--name", "冷萃咖啡豆")
$ingestA = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "ingest",
    "--id",
    $multiA,
    "--text",
    "冷萃咖啡豆，低酸顺滑，适合办公室冷泡和夏季饮品，视觉偏好干净、专业、不要太促销。"
)
$createB = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $multiB, "--name", "儿童护眼台灯")
$ingestB = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "ingest",
    "--id",
    $multiB,
    "--text",
    "儿童护眼台灯，光线柔和，适合学习桌和睡前阅读，强调安全、稳定、家长可信。"
)
$stateAPath = Join-Path $repoRoot ".hermes\product_creative\products\$multiA\structured\product_state.json"
$stateBPath = Join-Path $repoRoot ".hermes\product_creative\products\$multiB\structured\product_state.json"
$stateA = Get-Content -LiteralPath $stateAPath -Raw -Encoding UTF8 | ConvertFrom-Json
$stateB = Get-Content -LiteralPath $stateBPath -Raw -Encoding UTF8 | ConvertFrom-Json

$proposalUpdatePaths = @($proposalPayload.updates | ForEach-Object { $_.path })
$passed = [bool](
    $run.success -and
    $runPayload.schema_version -eq "product_creative.creative_run.v0.6.6" -and
    (-not $stateChangedByRun) -and
    ($SkipLive -or ($runPayload.mode -eq "live" -and $runPayload.external_call_count -eq 1)) -and
    $feedback.success -and
    $feedbackPayload.schema_version -eq "product_creative.result_feedback.v7.3" -and
    $feedbackPayload.average_quality_score -ge 4 -and
    $feedbackPayload.eligible_for_evolution_proposal -and
    $proposal.success -and
    ($proposalUpdatePaths -contains "learning.image_generation_preferences") -and
    ($proposalUpdatePaths -contains "learning.successful_patterns") -and
    ($proposalUpdatePaths -contains "learning.failed_patterns") -and
    $apply.success -and
    $stateChangedByApply -and
    $adaptedPayload.success -and
    $adaptedPayloadDoc.request.prompt_adapter.schema_version -eq "product_creative.prompt_adapter.v0.6.5" -and
    @($learningSnapshot.image_generation_preferences).Count -gt 0 -and
    @($learningSnapshot.successful_patterns).Count -gt 0 -and
    @($learningSnapshot.failed_patterns).Count -gt 0 -and
    $createA.success -and
    $ingestA.success -and
    $createB.success -and
    $ingestB.success -and
    $stateA.product_id -ne $stateB.product_id -and
    $stateA.name -ne $stateB.name -and
    $stateA.basic.brief -ne $stateB.basic.brief
)

[pscustomobject]@{
    success = $passed
    product_id = $ProductId
    live_call_count = $liveCallCount
    creative_run = $run.files.json
    creative_run_mode = $runPayload.mode
    creative_run_external_call_count = $runPayload.external_call_count
    result_for_feedback = $resultPath
    structured_feedback = $feedback.files.json
    average_quality_score = $feedbackPayload.average_quality_score
    evolution_proposal = $proposal.proposal_path
    applied_updates = @($apply.applied_updates).Count
    adapted_provider_payload = $adaptedPayload.files.json
    learning_snapshot_counts = [pscustomobject]@{
        image_generation_preferences = @($learningSnapshot.image_generation_preferences).Count
        successful_patterns = @($learningSnapshot.successful_patterns).Count
        failed_patterns = @($learningSnapshot.failed_patterns).Count
    }
    product_state_changed_by_creative_run = $stateChangedByRun
    product_state_changed_by_apply = $stateChangedByApply
    multiproduct = [pscustomobject]@{
        product_a = $multiA
        product_b = $multiB
        independent_state = [bool]($stateA.product_id -ne $stateB.product_id -and $stateA.basic.brief -ne $stateB.basic.brief)
    }
} | ConvertTo-Json -Depth 8

if (-not $passed) {
    exit 1
}
