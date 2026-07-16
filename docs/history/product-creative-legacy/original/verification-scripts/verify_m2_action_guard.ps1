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
    $missingId = "m2-guard-missing-$stamp"
    $missingCreateGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $missingId, "--action", "create_product"
    )
    $missingApplyGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $missingId, "--action", "apply_evolution_proposal", "--confirmed"
    )

    $productId = "m2-guard-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "山野冻干蓝莓")
    $runBeforeIngestGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "run_channel_review"
    )
    $ingestGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "ingest_product_source"
    )

    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "山野冻干蓝莓，真实果粒，酸甜清爽，适合办公室轻零食和早餐酸奶搭配。主图希望高级质感，突出真实果粒，不要太促销。"
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBeforeGuard = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $runGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "run_channel_review"
    )
    $stateHashAfterGuard = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $run = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-review-run",
        "--id",
        $productId,
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "3"
    )
    $proposalBeforeFeedbackGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "create_evolution_proposal"
    )
    $feedbackGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "record_channel_feedback"
    )

    $runPayload = Read-JsonFile -Path $run.files.json
    $channelArtifactId = $runPayload.artifacts.channel_content.id
    $bestVariant = [string]$runPayload.summary.best_variant
    $feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-feedback",
        "--id",
        $productId,
        "--artifact",
        $channelArtifactId,
        "--variant",
        $bestVariant,
        "--selected",
        "--rating",
        "5",
        "--allow-evolve",
        "--note",
        "这个版本更像真实分享，保留真实果粒记忆点，广告感可以继续降低。",
        "--like-reason",
        "真实分享语气",
        "--dislike-reason",
        "广告感仍可降低",
        "--channel-fit",
        "5",
        "--factuality",
        "5",
        "--tone-fit",
        "5",
        "--actionability",
        "4"
    )
    $proposalGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "create_evolution_proposal"
    )
    $proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId)
    $applyUnconfirmedGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "apply_evolution_proposal", "--proposal", $proposal.proposal_id
    )
    $applyWrongProposalGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "apply_evolution_proposal", "--proposal", "proposal-wrong", "--confirmed"
    )
    $applyConfirmedGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "apply_evolution_proposal", "--proposal", $proposal.proposal_id, "--confirmed"
    )
    $apply = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "evolve", "--id", $productId, "--apply", $proposal.proposal_id
    )
    $applyAfterAppliedGuard = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "action-guard", "--id", $productId, "--action", "apply_evolution_proposal", "--proposal", $proposal.proposal_id, "--confirmed"
    )

    $passed = [bool](
        $missingCreateGuard.success -and
        $missingCreateGuard.allowed -and
        (-not $missingApplyGuard.allowed) -and
        $create.success -and
        (-not $runBeforeIngestGuard.allowed) -and
        $ingestGuard.allowed -and
        $ingest.success -and
        $runGuard.allowed -and
        ($runGuard.mutates_confirmed_product_brain -eq $false) -and
        ($stateHashBeforeGuard -eq $stateHashAfterGuard) -and
        $run.success -and
        (-not $proposalBeforeFeedbackGuard.allowed) -and
        $feedbackGuard.allowed -and
        $feedback.success -and
        $proposalGuard.allowed -and
        ($proposalGuard.mutates_confirmed_product_brain -eq $false) -and
        $proposal.success -and
        (-not $applyUnconfirmedGuard.allowed) -and
        $applyUnconfirmedGuard.requires_explicit_confirmation -and
        $applyUnconfirmedGuard.mutates_confirmed_product_brain -and
        (-not $applyWrongProposalGuard.allowed) -and
        $applyConfirmedGuard.allowed -and
        $applyConfirmedGuard.confirmed -and
        $applyConfirmedGuard.mutates_product_brain -and
        $apply.success -and
        $applyAfterAppliedGuard.allowed -and
        ($applyAfterAppliedGuard.reason -like "*idempotent replay*")
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        missing_create_allowed = $missingCreateGuard.allowed
        run_before_ingest_allowed = $runBeforeIngestGuard.allowed
        run_after_ingest_allowed = $runGuard.allowed
        guard_read_only_state_unchanged = ($stateHashBeforeGuard -eq $stateHashAfterGuard)
        proposal_before_feedback_allowed = $proposalBeforeFeedbackGuard.allowed
        feedback_allowed = $feedbackGuard.allowed
        proposal_allowed = $proposalGuard.allowed
        apply_unconfirmed_allowed = $applyUnconfirmedGuard.allowed
        apply_wrong_proposal_allowed = $applyWrongProposalGuard.allowed
        apply_confirmed_allowed = $applyConfirmedGuard.allowed
        apply_after_applied_allowed = $applyAfterAppliedGuard.allowed
        proposal_id = $proposal.proposal_id
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
