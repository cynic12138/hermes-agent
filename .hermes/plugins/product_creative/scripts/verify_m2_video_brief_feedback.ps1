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
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-video-feedback-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-video-feedback-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "周十五蜂蜜露")
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "周十五蜂蜜露，清爽果蜜饮品，适合夏日饮用、办公室补水和短视频种草。主图希望清爽自然，突出真实饮用场景。"
    )
    $asset = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "asset-register",
        "--id",
        $productId,
        "--path",
        $tempImage,
        "--role",
        "current_main_image",
        "--description",
        "用户上传的当前产品主图",
        "--usage",
        "video_first_frame"
    )
    $analysis = Invoke-JsonScript -ScriptPath $runner -InputArgs @("image-analyze", "--id", $productId, "--asset", $asset.material_id)
    $alignment = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "visual-align",
        "--id",
        $productId,
        "--analysis",
        $analysis.analysis_id,
        "--note",
        "这张主图后续优先作为图生视频首帧参考。"
    )
    $intent = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-intent",
        "--id",
        $productId,
        "--message",
        "用这张主图帮我做一个抖音短视频",
        "--asset",
        $asset.material_id,
        "--theme",
        "夏日清爽开瓶"
    )
    $brief = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-brief", "--id", $productId, "--intent", $intent.intent_id)
    $review = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-brief-review", "--id", $productId, "--brief", $brief.brief_id)
    $revision = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-brief-revise",
        "--id",
        $productId,
        "--brief",
        $brief.brief_id,
        "--patch",
        $review.editable_patch.patch_id,
        "--confirmed",
        "--note",
        "确认脚本可以进入反馈学习。"
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBeforeFeedback = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $feedbackPlan = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-plan", "--id", $productId, "--action", "record_video_brief_feedback")
    $feedbackConversation = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "conversation-adapter",
        "--id",
        $productId,
        "--message",
        "这个分镜很好，记住开瓶清爽开场和每个镜头都回到产品主体的结构"
    )
    $feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-brief-feedback",
        "--id",
        $productId,
        "--brief",
        $revision.brief_id,
        "--selected",
        "--rating",
        "5",
        "--allow-evolve",
        "--note",
        "这个分镜很好，记住开瓶清爽开场和每个镜头都回到产品主体的结构",
        "--like-reason",
        "开瓶清爽开场",
        "--like-reason",
        "每个镜头都回到产品主体",
        "--hook-strength",
        "5",
        "--storyboard-clarity",
        "5",
        "--product-grounding",
        "5",
        "--prompt-specificity",
        "5",
        "--channel-fit",
        "5",
        "--factuality",
        "5"
    )
    $stateHashAfterFeedback = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $feedbackStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $feedbackNext = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)
    $proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId)
    $proposalStatus = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $blockedApply = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-plan", "--id", $productId, "--action", "apply_evolution_proposal", "--proposal", $proposal.proposal_id)
    $apply = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-execute", "--id", $productId, "--action", "apply_evolution_proposal", "--proposal", $proposal.proposal_id, "--confirmed")
    $stateAfterApply = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json

    $intent2 = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-intent",
        "--id",
        $productId,
        "--message",
        "继续用这张主图做一个今日视频",
        "--asset",
        $asset.material_id,
        "--theme",
        "办公室清爽补水"
    )
    $brief2 = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-brief", "--id", $productId, "--intent", $intent2.intent_id)
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $feedbackInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $feedback.feedback_id -and $_.artifact_type -eq "video_brief_feedback" }).Count -eq 1

    $proposalPaths = @($proposal.proposal.target_state_paths)
    $videoPrefs = @($stateAfterApply.learning.video_script_preferences)
    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $asset.success -and
        $analysis.success -and
        $alignment.success -and
        $intent.success -and
        $brief.success -and
        $review.success -and
        $revision.success -and
        ($revision.status -eq "confirmed_for_provider_payload") -and
        ($feedbackPlan.status -eq "waiting_for_user_input") -and
        ($feedbackPlan.steps[0].tool -eq "product_video_brief_feedback") -and
        ($feedbackConversation.interpreted_intent.action -eq "record_video_brief_feedback") -and
        ($feedbackConversation.executes_tools -eq $false) -and
        $feedback.success -and
        ($feedback.eligible_for_evolution_proposal -eq $true) -and
        ($feedback.feedback.source_brief_id -eq $revision.brief_id) -and
        ($feedback.feedback.average_quality_score -eq 5) -and
        ($stateHashBeforeFeedback -eq $stateHashAfterFeedback) -and
        ($feedbackStatus.status -eq "feedback_recorded") -and
        ($feedbackNext.recommended_action.action -eq "create_evolution_proposal") -and
        $proposal.success -and
        ($proposalPaths -contains "learning.video_script_preferences") -and
        ($proposal.proposal.reason -like "*video script learning*") -and
        ($proposalStatus.status -eq "proposal_ready_for_confirmation") -and
        ($blockedApply.status -eq "blocked_for_confirmation") -and
        $apply.success -and
        ($apply.executed -eq $true) -and
        ($apply.post_status.status -eq "brain_updated") -and
        ($videoPrefs.Count -ge 1) -and
        ($videoPrefs[-1] -like "*开瓶清爽开场*") -and
        $intent2.success -and
        $brief2.success -and
        ($brief2.brief.generation_contract.prompt -like "*已确认视频脚本偏好*") -and
        ($brief2.brief.generation_contract.prompt -like "*开瓶清爽开场*") -and
        $feedbackInManifest
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        source_brief_id = $revision.brief_id
        feedback_id = $feedback.feedback_id
        feedback_eligible = $feedback.eligible_for_evolution_proposal
        proposal_id = $proposal.proposal_id
        proposal_paths = $proposalPaths
        blocked_apply_status = $blockedApply.status
        final_status = $apply.post_status.status
        learned_video_preference_count = $videoPrefs.Count
        next_brief_id = $brief2.brief_id
        next_prompt_used_learning = ($brief2.brief.generation_contract.prompt -like "*已确认视频脚本偏好*")
        state_unchanged_before_apply = ($stateHashBeforeFeedback -eq $stateHashAfterFeedback)
        feedback_in_manifest = $feedbackInManifest
    } | ConvertTo-Json -Depth 8

    if (-not $passed) {
        exit 1
    }
}
finally {
    Remove-Item -LiteralPath $tempImage -Force -ErrorAction SilentlyContinue
    if ($null -eq $previousDisableLlm) {
        Remove-Item Env:\PRODUCT_CREATIVE_DISABLE_LLM -ErrorAction SilentlyContinue
    }
    else {
        $env:PRODUCT_CREATIVE_DISABLE_LLM = $previousDisableLlm
    }
}
