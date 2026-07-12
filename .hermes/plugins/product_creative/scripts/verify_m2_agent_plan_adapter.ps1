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
    $productId = "m2-plan-$stamp"
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
    $stateHashBeforePlan = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $planWithoutTarget = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-plan",
        "--id",
        $productId,
        "--action",
        "run_channel_review"
    )
    $planWithTarget = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-plan",
        "--id",
        $productId,
        "--action",
        "run_channel_review",
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "3"
    )
    $conversationRun = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "conversation-adapter",
        "--id",
        $productId,
        "--message",
        "帮我生成小红书种草文案",
        "--variants",
        "3"
    )
    $stateHashAfterReadOnlyPlan = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $run = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-review-run",
        "--id",
        $productId,
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "3"
    )
    $runPayload = Read-JsonFile -Path $run.files.json

    $feedbackMessage = "我喜欢第1版，但广告感再弱一点，继续保留真实果粒记忆点。"
    $conversationFeedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "conversation-adapter",
        "--id",
        $productId,
        "--message",
        $feedbackMessage
    )
    $feedbackArgs = $conversationFeedback.plan.steps[0].args_template
    $feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "channel-feedback",
        "--id",
        $productId,
        "--artifact",
        $feedbackArgs.artifact_id,
        "--variant",
        ([string]$feedbackArgs.variant),
        "--selected",
        "--rating",
        ([string]$feedbackArgs.rating),
        "--allow-evolve",
        "--note",
        $feedbackArgs.note,
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
    $proposalPlan = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-plan",
        "--id",
        $productId
    )
    $proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId)
    $stateHashBeforeApplyConversation = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $conversationApply = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "conversation-adapter",
        "--id",
        $productId,
        "--message",
        "确认应用这个 proposal",
        "--proposal",
        $proposal.proposal_id
    )
    $stateHashAfterApplyConversation = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $passed = [bool](
        $create.success -and
        $ingest.success -and
        ($planWithoutTarget.schema_version -eq "product_creative.workflow_plan.v2.11") -and
        ($planWithoutTarget.status -eq "waiting_for_user_input") -and
        (@($planWithoutTarget.steps[0].missing_inputs) -contains "target") -and
        ($planWithTarget.ready_to_execute -eq $true) -and
        ($planWithTarget.steps[0].tool -eq "product_channel_review_run") -and
        ($planWithTarget.steps[0].args_template.target -eq "xiaohongshu-seeding-note") -and
        ($conversationRun.schema_version -eq "product_creative.conversation_adapter.v4.9") -and
        ($conversationRun.executes_tools -eq $false) -and
        ($conversationRun.interpreted_intent.action -eq "run_channel_review") -and
        ($conversationRun.interpreted_intent.target -eq "xiaohongshu-seeding-note") -and
        ($conversationRun.plan.ready_to_execute -eq $true) -and
        ($stateHashBeforePlan -eq $stateHashAfterReadOnlyPlan) -and
        $run.success -and
        ($conversationFeedback.interpreted_intent.action -eq "record_channel_feedback") -and
        ($conversationFeedback.plan.ready_to_execute -eq $true) -and
        ($conversationFeedback.plan.steps[0].args_template.note -eq $feedbackMessage) -and
        ($conversationFeedback.mutates_product_brain -eq $false) -and
        $feedback.success -and
        ($proposalPlan.requested_action -eq "create_evolution_proposal") -and
        ($proposalPlan.ready_to_execute -eq $true) -and
        $proposal.success -and
        ($conversationApply.interpreted_intent.action -eq "apply_evolution_proposal") -and
        ($conversationApply.interpreted_intent.confirmed -eq $true) -and
        ($conversationApply.plan.ready_to_execute -eq $true) -and
        ($conversationApply.plan.mutates_product_brain -eq $true) -and
        ($conversationApply.executes_tools -eq $false) -and
        ($stateHashBeforeApplyConversation -eq $stateHashAfterApplyConversation)
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        plan_without_target_status = $planWithoutTarget.status
        plan_with_target_ready = $planWithTarget.ready_to_execute
        conversation_run_action = $conversationRun.interpreted_intent.action
        conversation_run_target = $conversationRun.interpreted_intent.target
        conversation_feedback_action = $conversationFeedback.interpreted_intent.action
        conversation_feedback_note = $conversationFeedback.plan.steps[0].args_template.note
        proposal_plan_action = $proposalPlan.requested_action
        conversation_apply_ready = $conversationApply.plan.ready_to_execute
        adapter_read_only_state_unchanged = ($stateHashBeforeApplyConversation -eq $stateHashAfterApplyConversation)
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
