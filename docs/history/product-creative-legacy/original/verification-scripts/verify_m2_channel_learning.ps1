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
    $productId = "m2-learning-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "山野冻干蓝莓")
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "山野冻干蓝莓，真实果粒，酸甜清爽，适合办公室轻零食和早餐酸奶搭配。主图希望高级质感，突出真实果粒，不要太促销。"
    )

    $generateBefore = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "generate",
        "--id",
        $productId,
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "2"
    )
    $evaluate = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-evaluate",
        "--id",
        $productId,
        "--artifact",
        $generateBefore.artifact_json
    )
    $feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-feedback",
        "--id",
        $productId,
        "--artifact",
        $generateBefore.artifact_json,
        "--variant",
        "2",
        "--selected",
        "--rating",
        "5",
        "--allow-evolve",
        "--note",
        "标题方向不错，正文广告感再弱一点，更像真实分享，保留真实果粒这个记忆点。",
        "--like-reason",
        "真实分享语气",
        "--like-reason",
        "真实果粒记忆点清楚",
        "--dislike-reason",
        "广告感偏强",
        "--issue",
        "avoid hard sell",
        "--channel-fit",
        "5",
        "--factuality",
        "5",
        "--tone-fit",
        "5",
        "--actionability",
        "4"
    )
    $proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId)
    $proposalPayload = Read-JsonFile -Path $proposal.proposal_path
    $apply = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "evolve",
        "--id",
        $productId,
        "--apply",
        $proposal.proposal_id
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $state = Read-JsonFile -Path $statePath
    $generateAfter = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "generate",
        "--id",
        $productId,
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "1"
    )
    $afterPayload = Read-JsonFile -Path $generateAfter.artifact_json
    $lint = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-lint", "--id", $productId)
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)

    $proposalPaths = @($proposalPayload.updates | ForEach-Object { $_.path })
    $proposalTypes = @($proposalPayload.updates | ForEach-Object { $_.update_type })
    $proposalPages = @($proposalPayload.target_pages)
    $afterText = ($afterPayload | ConvertTo-Json -Depth 20)
    $manifestTypes = @($manifest.manifest.artifacts | ForEach-Object { $_.artifact_type })

    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $generateBefore.success -and
        $evaluate.success -and
        $evaluate.summary.overall_score -gt 0 -and
        $feedback.success -and
        $feedback.eligible_for_evolution_proposal -and
        $proposal.success -and
        ($proposalPaths -contains "learning.channel_preferences") -and
        ($proposalTypes -contains "channel_preference") -and
        ($proposalPages -contains "product/brand-voice.md") -and
        @($proposalPayload.source_ids).Count -gt 0 -and
        $apply.success -and
        @($state.learning.channel_preferences).Count -gt 0 -and
        $afterText.Contains("真实分享") -and
        $lint.success -and
        ($manifestTypes -contains "channel_evaluation") -and
        ($manifestTypes -contains "channel_feedback")
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        generated_before = $generateBefore.artifact_json
        channel_evaluation = $evaluate.files.json
        channel_feedback = $feedback.files.json
        proposal_id = $proposal.proposal_id
        proposal_path = $proposal.proposal_path
        proposal_paths = $proposalPaths
        proposal_target_pages = $proposalPages
        generated_after = $generateAfter.artifact_json
        channel_preferences = @($state.learning.channel_preferences)
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
