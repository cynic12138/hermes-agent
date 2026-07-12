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
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-video-intent-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-video-intent-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "周十五蜂蜜露")
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "周十五蜂蜜露，清爽果蜜饮品，适合夏日饮用、办公室补水和短视频种草。"
    )

    $emptyIntent = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-intent",
        "--id",
        $productId,
        "--message",
        "帮我生成当前产品的今日视频"
    )
    $emptySteps = @($emptyIntent.video_intent.recommended_steps)

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

    $needsAnalysisIntent = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-intent",
        "--id",
        $productId,
        "--message",
        "用这张主图帮我做一个抖音短视频"
    )
    $needsAnalysisSteps = @($needsAnalysisIntent.video_intent.recommended_steps)

    $analysis = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-analyze",
        "--id",
        $productId,
        "--asset",
        $asset.material_id
    )

    $needsAlignmentIntent = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-intent",
        "--id",
        $productId,
        "--message",
        "用这张主图帮我做一个抖音短视频"
    )
    $needsAlignmentSteps = @($needsAlignmentIntent.video_intent.recommended_steps)

    $alignment = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "visual-align",
        "--id",
        $productId,
        "--analysis",
        $analysis.analysis_id,
        "--note",
        "这张主图后续优先作为图生视频首帧参考。"
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBeforeIntent = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $finalIntent = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
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
    $stateHashAfterIntent = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $finalSteps = @($finalIntent.video_intent.recommended_steps)

    $stateHashBeforeConversation = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $conversationPlan = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "conversation-adapter",
        "--id",
        $productId,
        "--message",
        "用这张主图帮我做一个抖音短视频"
    )
    $stateHashAfterConversation = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $workflowExecution = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "用这张主图帮我做一个抖音短视频"
    )
    $stateHashAfterWorkflowExecution = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $intentInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $finalIntent.intent_id }).Count -eq 1

    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $emptyIntent.success -and
        ($emptyIntent.video_intent.intent.type -eq "today_video") -and
        ($emptyIntent.status -eq "waiting_for_user_input") -and
        ($emptySteps[0].step -eq "register_material_asset") -and
        $asset.success -and
        $needsAnalysisIntent.success -and
        ($needsAnalysisIntent.video_intent.intent.type -eq "image_to_video") -and
        ($needsAnalysisIntent.status -eq "needs_preparation") -and
        ($needsAnalysisSteps[0].step -eq "analyze_image") -and
        ($needsAnalysisIntent.video_intent.selected_material.material_id -eq $asset.material_id) -and
        $analysis.success -and
        $needsAlignmentIntent.success -and
        ($needsAlignmentSteps[0].step -eq "visual_align") -and
        ($needsAlignmentIntent.video_intent.related_artifacts.image_analysis_id -eq $analysis.analysis_id) -and
        $alignment.success -and
        $finalIntent.success -and
        ($finalIntent.video_intent.schema_version -eq "product_creative.video_intent.v2.17") -and
        ($finalIntent.status -eq "ready_for_video_brief") -and
        ($finalIntent.video_intent.intent.platform -eq "douyin") -and
        ($finalIntent.video_intent.selected_material.material_id -eq $asset.material_id) -and
        ($finalIntent.video_intent.readiness.has_material -eq $true) -and
        ($finalIntent.video_intent.readiness.has_image_analysis -eq $true) -and
        ($finalIntent.video_intent.readiness.has_visual_alignment -eq $true) -and
        ($finalIntent.video_intent.related_artifacts.visual_alignment_id -eq $alignment.alignment_id) -and
        ($finalSteps[-1].step -eq "create_image_to_video_brief") -and
        ($finalIntent.video_intent.safety.direct_write_to_product_brain -eq $false) -and
        ($stateHashBeforeIntent -eq $stateHashAfterIntent) -and
        ($conversationPlan.interpreted_intent.action -eq "resolve_video_intent") -and
        ($conversationPlan.executes_tools -eq $false) -and
        ($conversationPlan.plan.ready_to_execute -eq $true) -and
        ($conversationPlan.plan.steps[0].tool -eq "product_video_intent") -and
        ($conversationPlan.plan.steps[0].args_template.message -eq "用这张主图帮我做一个抖音短视频") -and
        ($stateHashBeforeConversation -eq $stateHashAfterConversation) -and
        $workflowExecution.success -and
        ($workflowExecution.executed -eq $true) -and
        ($workflowExecution.plan.steps[0].action -eq "resolve_video_intent") -and
        ($workflowExecution.result.video_intent.intent.type -eq "image_to_video") -and
        ($workflowExecution.result.status -eq "ready_for_video_brief") -and
        ($workflowExecution.post_status.evidence.latest_video_intent.id -eq $workflowExecution.result.intent_id) -and
        ($stateHashBeforeConversation -eq $stateHashAfterWorkflowExecution) -and
        $intentInManifest
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        material_id = $asset.material_id
        analysis_id = $analysis.analysis_id
        alignment_id = $alignment.alignment_id
        empty_status = $emptyIntent.status
        needs_analysis_step = $needsAnalysisSteps[0].step
        needs_alignment_step = $needsAlignmentSteps[0].step
        final_intent_id = $finalIntent.intent_id
        final_status = $finalIntent.status
        final_step = $finalSteps[-1].step
        conversation_action = $conversationPlan.interpreted_intent.action
        workflow_execute_action = $workflowExecution.plan.steps[0].action
        workflow_execute_intent_id = $workflowExecution.result.intent_id
        state_unchanged_by_video_intent = ($stateHashBeforeIntent -eq $stateHashAfterIntent)
        state_unchanged_by_conversation_video = ($stateHashBeforeConversation -eq $stateHashAfterWorkflowExecution)
        video_intent_in_manifest = $intentInManifest
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
