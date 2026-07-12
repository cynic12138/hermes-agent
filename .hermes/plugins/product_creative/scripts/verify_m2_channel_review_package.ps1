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
    $productId = "m2-review-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "山野冻干蓝莓")
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "山野冻干蓝莓，真实果粒，酸甜清爽，适合办公室轻零食和早餐酸奶搭配。主图希望高级质感，突出真实果粒，不要太促销。"
    )

    $generate = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "generate",
        "--id",
        $productId,
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "3"
    )
    $evaluate = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-evaluate",
        "--id",
        $productId,
        "--artifact",
        $generate.artifact_json
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBefore = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $review = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-review-package",
        "--id",
        $productId,
        "--artifact",
        $generate.artifact_json
    )

    $stateHashAfter = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $reviewPayload = Read-JsonFile -Path $review.files.json
    $reviewMarkdown = Get-Content -LiteralPath $review.files.markdown -Raw -Encoding UTF8
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $manifestTypes = @($manifest.manifest.artifacts | ForEach-Object { $_.artifact_type })

    $firstItem = @($reviewPayload.items)[0]
    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $generate.success -and
        $evaluate.success -and
        $review.success -and
        ($reviewPayload.schema_version -eq "product_creative.channel_review_package.v2.7") -and
        ($reviewPayload.status -eq "ready_for_channel_review") -and
        ($reviewPayload.source_artifact_id -eq $generate.artifact_id) -and
        ($reviewPayload.source_evaluation_id -eq $evaluate.evaluation_id) -and
        ($reviewPayload.summary.best_variant -eq $evaluate.summary.best_variant) -and
        ($reviewPayload.summary.evaluation_status -eq $evaluate.summary.status) -and
        (@($reviewPayload.items).Count -eq 3) -and
        ($firstItem.feedback_command.Contains("channel-feedback")) -and
        ($reviewMarkdown.Contains("channel-feedback")) -and
        ($reviewPayload.mutates_product_brain -eq $false) -and
        ($stateHashBefore -eq $stateHashAfter) -and
        ($manifestTypes -contains "channel_review_package")
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        generated_channel_content = $generate.artifact_json
        channel_evaluation = $evaluate.files.json
        channel_review_package = $review.files.json
        channel_review_markdown = $review.files.markdown
        best_variant = $reviewPayload.summary.best_variant
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
