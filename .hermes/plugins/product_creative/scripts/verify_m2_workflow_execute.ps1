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

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$previousDisableLlm = $env:PRODUCT_CREATIVE_DISABLE_LLM
$env:PRODUCT_CREATIVE_DISABLE_LLM = "1"

try {
    $missingProductId = "m2-exec-missing-$stamp"
    $missingCreate = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $missingProductId,
        "--action",
        "create_product"
    )
    $missingProductPath = Join-Path $repoRoot (".hermes\product_creative\products\" + $missingProductId)

    $productId = "m2-exec-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--action",
        "create_product",
        "--name",
        "山野冻干蓝莓"
    )
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--action",
        "ingest_product_source",
        "--text",
        "山野冻干蓝莓，真实果粒，酸甜清爽，适合办公室轻零食和早餐酸奶搭配。主图希望高级质感，突出真实果粒，不要太促销。"
    )
    $run = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "帮我生成小红书种草文案",
        "--variants",
        "3"
    )
    $feedbackMessage = "我喜欢第1版，但广告感再弱一点，继续保留真实果粒记忆点。"
    $feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        $feedbackMessage
    )
    $proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBeforeBlockedApply = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $blockedApply = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--action",
        "apply_evolution_proposal",
        "--proposal",
        $proposal.result.proposal_id
    )
    $stateHashAfterBlockedApply = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $apply = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--action",
        "apply_evolution_proposal",
        "--proposal",
        $proposal.result.proposal_id,
        "--confirmed"
    )

    $passed = [bool](
        ($missingCreate.executed -eq $false) -and
        ($missingCreate.plan.status -eq "waiting_for_user_input") -and
        (-not (Test-Path -LiteralPath $missingProductPath)) -and
        ($create.schema_version -eq "product_creative.workflow_execute.v4.9") -and
        ($create.executed -eq $true) -and
        ($create.post_status.status -eq "product_initialized") -and
        ($ingest.executed -eq $true) -and
        ($ingest.post_status.status -eq "ready_for_channel_run") -and
        ($run.plan_source -eq "conversation_adapter") -and
        ($run.executed -eq $true) -and
        ($run.plan.requested_action -eq "run_channel_review") -and
        ($run.plan.steps[0].args_template.target -eq "xiaohongshu-seeding-note") -and
        ($run.post_status.status -eq "channel_run_ready_for_review") -and
        ($feedback.executed -eq $true) -and
        ($feedback.plan.requested_action -eq "record_channel_feedback") -and
        ($feedback.plan.steps[0].args_template.note -eq $feedbackMessage) -and
        ($feedback.post_status.status -eq "feedback_recorded") -and
        ($proposal.executed -eq $true) -and
        ($proposal.plan.requested_action -eq "create_evolution_proposal") -and
        ($proposal.post_status.status -eq "proposal_ready_for_confirmation") -and
        ($blockedApply.executed -eq $false) -and
        ($blockedApply.execution_status -eq "not_executed") -and
        ($blockedApply.plan.status -eq "blocked_for_confirmation") -and
        ($stateHashBeforeBlockedApply -eq $stateHashAfterBlockedApply) -and
        ($apply.executed -eq $true) -and
        ($apply.plan.mutates_product_brain -eq $true) -and
        ($apply.post_status.status -eq "brain_updated")
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        missing_create_executed = $missingCreate.executed
        product_id = $productId
        create_status = $create.post_status.status
        ingest_status = $ingest.post_status.status
        run_action = $run.plan.requested_action
        run_target = $run.plan.steps[0].args_template.target
        feedback_action = $feedback.plan.requested_action
        proposal_action = $proposal.plan.requested_action
        proposal_id = $proposal.result.proposal_id
        blocked_apply_status = $blockedApply.plan.status
        blocked_apply_state_unchanged = ($stateHashBeforeBlockedApply -eq $stateHashAfterBlockedApply)
        final_status = $apply.post_status.status
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
