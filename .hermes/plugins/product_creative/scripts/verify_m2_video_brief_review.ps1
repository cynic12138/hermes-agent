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
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-video-brief-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-video-brief-$stamp"
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

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBefore = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $briefPlan = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-plan", "--id", $productId, "--action", "create_video_brief")
    $briefConversation = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "conversation-adapter",
        "--id",
        $productId,
        "--message",
        "生成视频brief"
    )
    $brief = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-brief", "--id", $productId, "--intent", $intent.intent_id)
    $nextAfterBrief = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)
    $reviewPlan = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-plan", "--id", $productId, "--action", "review_video_brief")
    $review = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-brief-review", "--id", $productId, "--brief", $brief.brief_id)
    $workflowReview = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-execute", "--id", $productId, "--action", "review_video_brief")
    $payload = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-generate", "--id", $productId, "--brief", $brief.brief_id, "--provider", "generic")
    $validation = Invoke-JsonScript -ScriptPath $runner -InputArgs @("provider-validate", "--id", $productId, "--payload", $payload.payload_id, "--provider", "generic")

    $stateHashAfter = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $briefInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $brief.brief_id -and $_.artifact_type -eq "video_brief" }).Count -eq 1
    $reviewInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $review.review_package_id -and $_.artifact_type -eq "review_package" }).Count -eq 1
    $workflowReviewInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $workflowReview.result.review_package_id -and $_.artifact_type -eq "review_package" }).Count -eq 1

    $storyboard = @($brief.brief.story.storyboard)
    $sourceAssets = @($brief.brief.source_assets)
    $recommendedSteps = @($intent.video_intent.recommended_steps)
    $firstShot = $storyboard[0]
    $hasRichStoryboard = [bool](
        $firstShot.purpose -and
        $firstShot.action -and
        $firstShot.camera -and
        $firstShot.motion -and
        $firstShot.audio -and
        $firstShot.product_visibility -and
        $firstShot.provider_prompt_segment
    )

    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $asset.success -and
        $analysis.success -and
        $alignment.success -and
        $intent.success -and
        ($intent.status -eq "ready_for_video_brief") -and
        ($recommendedSteps[-1].tool -eq "product_video_brief") -and
        ($briefPlan.ready_to_execute -eq $true) -and
        ($briefPlan.steps[0].tool -eq "product_video_brief") -and
        ($briefConversation.interpreted_intent.action -eq "create_video_brief") -and
        ($briefConversation.executes_tools -eq $false) -and
        $brief.success -and
        ($brief.brief.schema_version -eq "product_creative.video_brief.v2.18") -and
        ($brief.brief.source_intent_id -eq $intent.intent_id) -and
        ($brief.status -eq "ready_for_review") -and
        ($brief.brief.target.platform -eq "douyin") -and
        ($brief.brief.visual_grounding.material_id -eq $asset.material_id) -and
        ($storyboard.Count -ge 4) -and
        $hasRichStoryboard -and
        ($brief.brief.generation_contract.script_quality_contract.prompt_is_primary_video_quality_control -eq $true) -and
        (@($brief.brief.generation_contract.storyboard_prompt_segments).Count -eq $storyboard.Count) -and
        ($brief.brief.generation_contract.prompt -like "*镜头分镜*") -and
        ($brief.brief.generation_contract.prompt -like "*产品要求*") -and
        ($sourceAssets.Count -eq 1) -and
        ($sourceAssets[0].asset_id -eq $asset.material_id) -and
        ($brief.brief.generation_contract.prompt -like "*周十五蜂蜜露*") -and
        ($brief.brief.brain_write_policy.direct_write_to_product_brain -eq $false) -and
        ($nextAfterBrief.recommended_action.action -eq "review_video_brief") -and
        ($reviewPlan.ready_to_execute -eq $true) -and
        ($reviewPlan.steps[0].tool -eq "product_video_brief_review_package") -and
        $review.success -and
        ($review.review_package.schema_version -eq "product_creative.video_brief_review_package.v2.19") -and
        ($review.review_package.source_brief_id -eq $brief.brief_id) -and
        ($review.review_package.external_call_performed -eq $false) -and
        ($review.review_package.mutates_product_brain -eq $false) -and
        (@($review.review_package.review_checklist).Count -ge 5) -and
        $workflowReview.success -and
        ($workflowReview.executed -eq $true) -and
        ($workflowReview.plan.steps[0].action -eq "review_video_brief") -and
        $payload.success -and
        ($payload.brief_type -eq "video") -and
        ($payload.payload.request.storyboard.Count -ge 4) -and
        $validation.success -and
        ($validation.status -eq "valid") -and
        ($stateHashBefore -eq $stateHashAfter) -and
        $briefInManifest -and
        $reviewInManifest -and
        $workflowReviewInManifest
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        intent_id = $intent.intent_id
        brief_id = $brief.brief_id
        review_package_id = $review.review_package_id
        workflow_review_package_id = $workflowReview.result.review_package_id
        payload_id = $payload.payload_id
        validation_status = $validation.status
        storyboard_count = $storyboard.Count
        rich_storyboard = $hasRichStoryboard
        next_after_brief = $nextAfterBrief.recommended_action.action
        brief_plan_action = $briefPlan.steps[0].action
        review_plan_action = $reviewPlan.steps[0].action
        state_unchanged = ($stateHashBefore -eq $stateHashAfter)
        brief_in_manifest = $briefInManifest
        review_in_manifest = $reviewInManifest
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
