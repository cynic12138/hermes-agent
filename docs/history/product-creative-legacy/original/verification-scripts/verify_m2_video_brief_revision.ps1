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
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-video-revision-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-video-revision-$stamp"
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

    $brief = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-brief", "--id", $productId, "--intent", $intent.intent_id)
    $nextAfterBrief = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)
    $review = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-brief-review", "--id", $productId, "--brief", $brief.brief_id)
    $nextAfterReview = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)
    $blockedBuild = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-plan", "--id", $productId, "--action", "build_video_provider_payload")
    $blockedRevision = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-plan", "--id", $productId, "--action", "revise_video_brief")
    $readyRevision = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-plan", "--id", $productId, "--action", "revise_video_brief", "--confirmed")

    $patchPath = $review.editable_patch.json
    $patchDoc = Get-Content -LiteralPath $patchPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $patchDoc.story_updates.pacing = "前2秒突出开瓶清爽感，随后进入真实饮用场景，尾帧保持产品和手部动作清楚。"
    $patchDoc.shot_updates[0].caption = "开瓶就很清爽"
    $patchDoc.shot_updates[1].action = "镜头聚焦手部打开产品，出现清爽水汽和轻微推近，只表达清爽饮用感。"
    $patchDoc.shot_updates[1].audio = "开瓶声和轻快鼓点同步，避免复杂旁白。"
    $patchDoc.confirmation.confirmed = $true
    $patchDoc.confirmation.note = "确认采用更强的开瓶清爽开场。"
    $patchDoc | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $patchPath -Encoding UTF8

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
        "确认采用更强的开瓶清爽开场。"
    )
    $nextAfterRevision = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)
    $buildPlan = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-plan", "--id", $productId, "--action", "build_video_provider_payload")
    $buildExecute = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-execute", "--id", $productId, "--action", "build_video_provider_payload")

    $stateHashAfter = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $patchInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $review.editable_patch.patch_id -and $_.artifact_type -eq "video_brief_patch" }).Count -eq 1
    $revisionInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $revision.brief_id -and $_.artifact_type -eq "video_brief" }).Count -eq 1
    $payloadInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $buildExecute.result.payload_id -and $_.artifact_type -eq "provider_payload" }).Count -eq 1

    $revisedStoryboard = @($revision.brief.story.storyboard)
    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $asset.success -and
        $analysis.success -and
        $alignment.success -and
        $intent.success -and
        $brief.success -and
        ($nextAfterBrief.recommended_action.action -eq "review_video_brief") -and
        $review.success -and
        ($review.editable_patch.patch_id -like "video-brief-patch-*") -and
        (Test-Path -LiteralPath $patchPath) -and
        ($nextAfterReview.recommended_action.action -eq "revise_video_brief") -and
        ($blockedBuild.status -eq "blocked_by_guard") -and
        ($blockedRevision.status -eq "blocked_for_confirmation") -and
        ($readyRevision.ready_to_execute -eq $true) -and
        $revision.success -and
        ($revision.brief.schema_version -eq "product_creative.video_brief.v2.28") -and
        ($revision.source_brief_id -eq $brief.brief_id) -and
        ($revision.status -eq "confirmed_for_provider_payload") -and
        ($revision.confirmed_for_provider_payload -eq $true) -and
        ($revision.brief.revision.source_patch_id -eq $review.editable_patch.patch_id) -and
        ($revisedStoryboard[0].caption -eq "开瓶就很清爽") -and
        ($revisedStoryboard[1].action -like "*清爽水汽*") -and
        ($revision.brief.generation_contract.prompt -like "*开瓶就很清爽*") -and
        ($nextAfterRevision.recommended_action.action -eq "build_video_provider_payload") -and
        ($buildPlan.ready_to_execute -eq $true) -and
        $buildExecute.success -and
        ($buildExecute.executed -eq $true) -and
        ($buildExecute.result.payload.source_brief_id -eq $revision.brief_id) -and
        ($stateHashBefore -eq $stateHashAfter) -and
        $patchInManifest -and
        $revisionInManifest -and
        $payloadInManifest
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        source_brief_id = $brief.brief_id
        review_package_id = $review.review_package_id
        patch_id = $review.editable_patch.patch_id
        revised_brief_id = $revision.brief_id
        revised_status = $revision.status
        next_after_review = $nextAfterReview.recommended_action.action
        next_after_revision = $nextAfterRevision.recommended_action.action
        blocked_build_status = $blockedBuild.status
        blocked_revision_status = $blockedRevision.status
        build_payload_id = $buildExecute.result.payload_id
        state_unchanged = ($stateHashBefore -eq $stateHashAfter)
        patch_in_manifest = $patchInManifest
        revision_in_manifest = $revisionInManifest
        payload_in_manifest = $payloadInManifest
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
