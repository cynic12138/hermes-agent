[CmdletBinding()]
param()

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

function Read-JsonFile {
    param([string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$previousDisableLlm = $env:PRODUCT_CREATIVE_DISABLE_LLM
$env:PRODUCT_CREATIVE_DISABLE_LLM = "1"

try {
    $productId = "m2-review-run-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "山野冻干蓝莓")
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "山野冻干蓝莓，真实果粒，酸甜清爽，适合办公室轻零食和早餐酸奶搭配。主图希望高级质感，突出真实果粒，不要太促销。"
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBefore = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $run = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-review-run",
        "--id",
        $productId,
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "3"
    )

    $stateHashAfter = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $runPayload = Read-JsonFile -Path $run.files.json
    $reviewPath = Join-Path $base $runPayload.artifacts.channel_review_package.path
    $reviewPayload = Read-JsonFile -Path $reviewPath
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $manifestTypes = @($manifest.manifest.artifacts | ForEach-Object { $_.artifact_type })
    $indexPath = Join-Path $base "structured\channel_review_run_index.jsonl"
    $indexText = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8

    $runCommand = $runPayload.next_actions.record_selected_feedback.command
    $reviewCommand = $reviewPayload.next_actions.record_selected_feedback.command
    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $run.success -and
        ($runPayload.schema_version -eq "product_creative.channel_review_run.v2.8") -and
        ($runPayload.status -eq "ready_for_human_review") -and
        ($runPayload.target -eq "xiaohongshu-seeding-note") -and
        ($runPayload.variants_requested -eq 3) -and
        ($runPayload.mutates_product_brain -eq $false) -and
        ($stateHashBefore -eq $stateHashAfter) -and
        ($runPayload.artifacts.channel_content.path) -and
        ($runPayload.artifacts.channel_evaluation.path) -and
        ($runPayload.artifacts.channel_review_package.path) -and
        ($runPayload.artifacts.manifest.path) -and
        ($runCommand.Contains("channel-feedback")) -and
        ($reviewCommand.Contains("channel-feedback")) -and
        ($reviewPayload.next_actions.record_selected_feedback.suggested_variant -eq $runPayload.summary.best_variant) -and
        ($manifestTypes -contains "channel_content") -and
        ($manifestTypes -contains "channel_evaluation") -and
        ($manifestTypes -contains "channel_review_package") -and
        ($manifestTypes -contains "channel_review_run") -and
        (-not ($manifestTypes -contains "channel_feedback")) -and
        $indexText.Contains($runPayload.channel_review_run_id)
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        channel_review_run = $run.files.json
        channel_review_markdown = $run.files.markdown
        channel_content = $runPayload.artifacts.channel_content.path
        channel_evaluation = $runPayload.artifacts.channel_evaluation.path
        channel_review_package = $runPayload.artifacts.channel_review_package.path
        best_variant = $runPayload.summary.best_variant
        state_unchanged = ($stateHashBefore -eq $stateHashAfter)
        manifest = $manifest.files.json
    } | ConvertTo-Json -Depth 8

    if (-not $passed) {
        exit 1
    }
}
finally {
    if ($null -eq $previousDisableLlm) {
        Remove-Item Env:\PRODUCT_CREATIVE_DISABLE_LLM -ErrorAction SilentlyContinue
    }
    else {
        $env:PRODUCT_CREATIVE_DISABLE_LLM = $previousDisableLlm
    }
}
