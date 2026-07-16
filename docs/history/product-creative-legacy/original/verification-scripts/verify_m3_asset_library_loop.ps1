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

function Has-ArtifactType {
    param(
        [object]$Manifest,
        [string]$Type
    )
    return @($Manifest.manifest.artifacts | Where-Object { $_.artifact_type -eq $Type }).Count -gt 0
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$previousDisableLlm = $env:PRODUCT_CREATIVE_DISABLE_LLM
$env:PRODUCT_CREATIVE_DISABLE_LLM = "1"
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m3-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m3-assets-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "周十五蜂蜜露")
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "周十五蜂蜜露是一款清甜饮品，核心卖点是清爽口感、日常分享、产品主体清晰。内容生成需避免夸大功效。"
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
        "product_reference",
        "--usage",
        "video_first_frame"
    )
    $analysis = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-analyze",
        "--id",
        $productId,
        "--asset",
        $asset.material_id,
        "--provider",
        "mock-vision"
    )
    $alignment = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "visual-align",
        "--id",
        $productId,
        "--analysis",
        $analysis.analysis_id,
        "--note",
        "M3 verification visual alignment"
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateBeforeM3 = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $compat = Invoke-JsonScript -ScriptPath $runner -InputArgs @("material-compat", "--id", $productId)
    $cards = Invoke-JsonScript -ScriptPath $runner -InputArgs @("material-card-rebuild", "--id", $productId)
    $map = Invoke-JsonScript -ScriptPath $runner -InputArgs @("material-library-map", "--id", $productId)
    $pack = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "task-material-pack",
        "--id",
        $productId,
        "--task",
        "video_brief",
        "--channel",
        "douyin",
        "--limit",
        "3"
    )
    $stateAfterPack = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $channel = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "generate",
        "--id",
        $productId,
        "--target",
        "xiaohongshu-seeding-note",
        "--variants",
        "1"
    )
    $copy = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "generate",
        "--id",
        $productId,
        "--target",
        "product-copy-pack",
        "--variants",
        "1"
    )
    $brief = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "brief",
        "--id",
        $productId,
        "--artifact",
        $copy.artifact_id,
        "--kind",
        "video",
        "--preset",
        "douyin-9x16"
    )
    $intent = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-intent",
        "--id",
        $productId,
        "--message",
        "帮我生成当前产品今日视频",
        "--platform",
        "douyin",
        "--theme",
        "今日清爽分享"
    )
    $videoBrief = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-brief",
        "--id",
        $productId,
        "--intent",
        $intent.intent_id
    )
    $stateBeforeFeedback = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "material-feedback",
        "--id",
        $productId,
        "--material",
        $asset.material_id,
        "--task",
        "video_brief",
        "--channel",
        "douyin",
        "--selected",
        "--rating",
        "5",
        "--note",
        "这张主图适合作为视频首帧"
    )
    $packAfterFeedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "task-material-pack",
        "--id",
        $productId,
        "--task",
        "video_brief",
        "--channel",
        "douyin",
        "--limit",
        "3"
    )
    $stateAfterFeedback = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)

    $cardPath = $cards.cards[0].source_files.material_asset
    $mapArtifactJsonExists = Test-Path -LiteralPath $map.files.artifact_json
    $channelJson = Read-JsonFile -Path $channel.artifact_json
    $briefJson = Read-JsonFile -Path $brief.files[0].json
    $videoBriefJson = Read-JsonFile -Path $videoBrief.files.json
    $feedbackReasonApplied = @($packAfterFeedback.task_material_pack.selected_materials[0].reasons | Where-Object { $_ -like "*material feedback adjusted score*" }).Count -gt 0

    $usageCount = 0
    $usageDir = Join-Path $base "artifacts\material_usage"
    if (Test-Path -LiteralPath $usageDir) {
        $usageCount = @(Get-ChildItem -LiteralPath $usageDir -Filter "*.json").Count
    }

    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $asset.success -and
        $analysis.success -and
        $alignment.success -and
        ($compat.material_count -eq 1) -and
        ($compat.materials[0].has_image_analysis -eq $true) -and
        ($compat.materials[0].has_visual_alignment -eq $true) -and
        ($cards.card_count -eq 1) -and
        ($cards.cards[0].schema_version -eq "product_creative.material_card.v3.2") -and
        ($cards.cards[0].readiness.has_image_analysis -eq $true) -and
        ($cards.cards[0].readiness.has_visual_alignment -eq $true) -and
        ($map.card_count -eq 1) -and
        $mapArtifactJsonExists -and
        ($pack.selected_count -eq 1) -and
        ($pack.task_material_pack.selected_materials[0].material_id -eq $asset.material_id) -and
        ($stateBeforeM3 -eq $stateAfterPack) -and
        ($channel.material_context.task_material_pack_id -like "task-material-pack-*") -and
        ($channelJson.material_context.task_material_pack_id -eq $channel.material_context.task_material_pack_id) -and
        ($brief.task_material_pack_id -like "task-material-pack-*") -and
        ($briefJson.source_material_pack.task_material_pack_id -eq $brief.task_material_pack_id) -and
        ($intent.status -eq "ready_for_video_brief") -and
        ($intent.video_intent.related_artifacts.task_material_pack_id -like "task-material-pack-*") -and
        ($videoBrief.brief.visual_grounding.task_material_pack_id -eq $intent.video_intent.related_artifacts.task_material_pack_id) -and
        ($videoBriefJson.source_assets[0].task_material_pack_id -eq $intent.video_intent.related_artifacts.task_material_pack_id) -and
        ($feedback.feedback.brain_write_policy.direct_write_to_product_brain -eq $false) -and
        $feedbackReasonApplied -and
        ($stateBeforeFeedback -eq $stateAfterFeedback) -and
        ($usageCount -ge 3) -and
        (Has-ArtifactType -Manifest $manifest -Type "material_card") -and
        (Has-ArtifactType -Manifest $manifest -Type "material_library_map") -and
        (Has-ArtifactType -Manifest $manifest -Type "task_material_pack") -and
        (Has-ArtifactType -Manifest $manifest -Type "material_usage") -and
        (Has-ArtifactType -Manifest $manifest -Type "material_feedback")
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        material_id = $asset.material_id
        analysis_id = $analysis.analysis_id
        alignment_id = $alignment.alignment_id
        compat_material_count = $compat.material_count
        material_card_count = $cards.card_count
        material_library_map_count = $map.card_count
        task_material_pack_id = $pack.task_material_pack_id
        channel_artifact_id = $channel.artifact_id
        channel_material_pack_id = $channel.material_context.task_material_pack_id
        copy_artifact_id = $copy.artifact_id
        brief_task_material_pack_id = $brief.task_material_pack_id
        video_intent_id = $intent.intent_id
        video_intent_pack_id = $intent.video_intent.related_artifacts.task_material_pack_id
        video_brief_id = $videoBrief.brief_id
        video_brief_pack_id = $videoBrief.brief.visual_grounding.task_material_pack_id
        material_feedback_id = $feedback.feedback_id
        feedback_affects_next_pack = $feedbackReasonApplied
        material_usage_count = $usageCount
        state_unchanged_by_m3 = ($stateBeforeM3 -eq $stateAfterPack -and $stateBeforeFeedback -eq $stateAfterFeedback)
        manifest_has_m3_artifacts = $passed
        card_source_material_path = $cardPath
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
