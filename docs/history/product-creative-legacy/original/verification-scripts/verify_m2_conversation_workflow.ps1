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
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-conversation-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-conversation-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "创建产品",
        "--name",
        "周十五蜂蜜露"
    )
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "输入资料：周十五蜂蜜露是一款清爽蜂蜜饮品，适合夏季补水和轻负担饮用。",
        "--text",
        "周十五蜂蜜露是一款清爽蜂蜜饮品，强调自然蜜香、轻甜口感、夏季饮用场景。后续主图和短视频都应保持真实、清爽、不夸大功效。"
    )
    $register = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "上传主图作为当前产品视觉参考",
        "--path",
        $tempImage,
        "--role",
        "current_main_image",
        "--description",
        "用户上传的周十五蜂蜜露当前主图",
        "--usage",
        "product_reference",
        "--usage",
        "video_first_frame"
    )
    $nextAfterRegister = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateBeforeAnalyze = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $analyze = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "分析主图"
    )
    $stateAfterAnalyze = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $nextAfterAnalyze = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-next", "--id", $productId)

    $align = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "对齐主图理解，作为后续图片和视频的视觉参考",
        "--note",
        "M2.31 conversation workflow confirms this uploaded image as a candidate visual reference."
    )
    $stateAfterAlign = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $intent = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "用这张主图生成今日视频"
    )
    $brief = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "生成视频brief"
    )
    $review = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-execute",
        "--id",
        $productId,
        "--message",
        "审阅视频brief"
    )
    $summary = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-summary", "--id", $productId)

    $passed = [bool](
        ($create.executed -eq $true) -and
        ($create.schema_version -eq "product_creative.workflow_execute.v4.9") -and
        ($create.plan_source -eq "conversation_adapter") -and
        ($create.plan.requested_action -eq "create_product") -and
        ($ingest.executed -eq $true) -and
        ($ingest.plan.requested_action -eq "ingest_product_source") -and
        ($register.executed -eq $true) -and
        ($register.plan.requested_action -eq "register_material_asset") -and
        ($register.result.material_id) -and
        ($nextAfterRegister.recommended_action.action -eq "analyze_material_image") -and
        ($analyze.executed -eq $true) -and
        ($analyze.plan.requested_action -eq "analyze_material_image") -and
        ($analyze.result.analysis.provider -eq "mock-vision") -and
        ($analyze.result.analysis.external_call_performed -eq $false) -and
        ($nextAfterAnalyze.recommended_action.action -eq "align_visual_analysis") -and
        ($align.executed -eq $true) -and
        ($align.plan.requested_action -eq "align_visual_analysis") -and
        ($align.result.alignment.brain_write_policy.direct_write_to_product_brain -eq $false) -and
        ($stateBeforeAnalyze -eq $stateAfterAnalyze) -and
        ($stateAfterAnalyze -eq $stateAfterAlign) -and
        ($intent.executed -eq $true) -and
        ($intent.plan.requested_action -eq "resolve_video_intent") -and
        ($intent.result.status -eq "ready_for_video_brief") -and
        ($brief.executed -eq $true) -and
        ($brief.plan.requested_action -eq "create_video_brief") -and
        ($review.executed -eq $true) -and
        ($review.plan.requested_action -eq "review_video_brief") -and
        ($summary.success -eq $true)
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        create_action = $create.plan.requested_action
        ingest_action = $ingest.plan.requested_action
        register_action = $register.plan.requested_action
        material_id = $register.result.material_id
        next_after_register = $nextAfterRegister.recommended_action.action
        analyze_action = $analyze.plan.requested_action
        analysis_id = $analyze.result.analysis_id
        analysis_provider = $analyze.result.analysis.provider
        next_after_analyze = $nextAfterAnalyze.recommended_action.action
        align_action = $align.plan.requested_action
        alignment_id = $align.result.alignment_id
        state_unchanged_by_analyze = ($stateBeforeAnalyze -eq $stateAfterAnalyze)
        state_unchanged_by_align = ($stateAfterAnalyze -eq $stateAfterAlign)
        video_intent_id = $intent.result.intent_id
        video_brief_id = $brief.result.brief_id
        video_review_id = $review.result.review_package_id
        final_recommended_action = $summary.recommended_action.action
    } | ConvertTo-Json -Depth 10

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
