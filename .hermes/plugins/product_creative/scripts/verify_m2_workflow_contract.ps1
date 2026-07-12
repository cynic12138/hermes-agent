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
    $missingId = "m2-workflow-missing-$stamp"
    $missingStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $missingId)
    $missingNext = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $missingId)

    $productId = "m2-workflow-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "山野冻干蓝莓")
    $createdStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)

    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "山野冻干蓝莓，真实果粒，酸甜清爽，适合办公室轻零食和早餐酸奶搭配。主图希望高级质感，突出真实果粒，不要太促销。"
    )
    $readyStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $readyNext = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBeforeReadOnly = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $summaryReadOnly = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-summary", "--id", $productId)
    $stateHashAfterReadOnly = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $run = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-review-run",
        "--id",
        $productId,
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "3"
    )
    $runStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $runNext = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)
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
    $feedbackStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $feedbackNext = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)

    $proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId)
    $proposalStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $proposalNext = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)

    $apply = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId, "--apply", $proposal.proposal_id)
    $appliedStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $appliedSummary = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-summary", "--id", $productId)

    $passed = [bool](
        $missingStatus.success -and
        ($missingStatus.status -eq "no_product") -and
        ($missingNext.recommended_action.action -eq "create_product") -and
        $create.success -and
        ($createdStatus.status -eq "product_initialized") -and
        $ingest.success -and
        ($readyStatus.status -eq "ready_for_channel_run") -and
        ($readyNext.recommended_action.action -eq "run_channel_review") -and
        ($readyNext.recommended_action.mutates_product_brain -eq $false) -and
        ($stateHashBeforeReadOnly -eq $stateHashAfterReadOnly) -and
        $summaryReadOnly.summary.Contains("Recommended next action") -and
        $run.success -and
        ($runStatus.status -eq "channel_run_ready_for_review") -and
        ($runNext.recommended_action.action -eq "record_channel_feedback") -and
        ($runNext.recommended_action.mutates_product_brain -eq $false) -and
        $feedback.success -and
        ($feedbackStatus.status -eq "feedback_recorded") -and
        ($feedbackNext.recommended_action.action -eq "create_evolution_proposal") -and
        ($feedbackNext.recommended_action.mutates_product_brain -eq $false) -and
        $proposal.success -and
        ($proposalStatus.status -eq "proposal_ready_for_confirmation") -and
        ($proposalNext.recommended_action.action -eq "apply_evolution_proposal") -and
        ($proposalNext.recommended_action.requires_explicit_confirmation -eq $true) -and
        ($proposalNext.recommended_action.mutates_product_brain -eq $true) -and
        $apply.success -and
        ($appliedStatus.status -eq "brain_updated") -and
        $appliedSummary.summary.Contains("Workflow status: brain_updated") -and
        ($appliedStatus.safety.proposal_apply_requires_explicit_user_confirmation -eq $true)
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        statuses = @(
            $missingStatus.status,
            $createdStatus.status,
            $readyStatus.status,
            $runStatus.status,
            $feedbackStatus.status,
            $proposalStatus.status,
            $appliedStatus.status
        )
        next_actions = @(
            $missingNext.recommended_action.action,
            $readyNext.recommended_action.action,
            $runNext.recommended_action.action,
            $feedbackNext.recommended_action.action,
            $proposalNext.recommended_action.action
        )
        read_only_status_unchanged_state = ($stateHashBeforeReadOnly -eq $stateHashAfterReadOnly)
        channel_review_run = $run.files.json
        channel_feedback = $feedback.files.json
        proposal_id = $proposal.proposal_id
        proposal_path = $proposal.proposal_path
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
