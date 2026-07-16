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
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-workflow-run-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-run-$stamp"
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
        "输入资料",
        "--text",
        "周十五蜂蜜露是一款清爽蜂蜜饮品，主打自然蜜香、轻甜口感和夏季清爽饮用场景。内容生成需避免夸大功效。"
    )

    $materialRun = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-run",
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
        "--max-steps",
        "5"
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateAfterMaterialRun = Read-JsonFile -Path $statePath
    $learningAfterMaterialRun = $stateAfterMaterialRun.learning

    $videoRun = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-run",
        "--id",
        $productId,
        "--message",
        "用这张主图生成今日视频",
        "--max-steps",
        "5"
    )

    $statusAfterVideoRun = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $latestBriefId = $statusAfterVideoRun.evidence.latest_video_brief.id
    $latestBriefPath = Join-Path $base ("artifacts\video_scripts\" + $latestBriefId + ".json")
    $latestBrief = Read-JsonFile -Path $latestBriefPath
    $payloadDir = Join-Path $base "artifacts\provider_payloads"
    $payloadCount = 0
    if (Test-Path -LiteralPath $payloadDir) {
        $payloadCount = @(
            Get-ChildItem -LiteralPath $payloadDir -Filter "*.json" |
            Where-Object { (Read-JsonFile -Path $_.FullName).brief_type -eq "video" }
        ).Count
    }

    $vlmBlocked = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-run",
        "--id",
        $productId,
        "--action",
        "analyze_material_image",
        "--provider",
        "volcengine-ark-vlm",
        "--max-steps",
        "2"
    )
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)

    $materialActions = @($materialRun.executions | ForEach-Object { $_.action })
    $videoActions = @($videoRun.executions | ForEach-Object { $_.action })
    $learningPreferenceCount = 0
    if ($learningAfterMaterialRun -and $learningAfterMaterialRun.image_generation_preferences) {
        $learningPreferenceCount = @($learningAfterMaterialRun.image_generation_preferences).Count
    }
    $materialRunRecord = Read-JsonFile -Path $materialRun.files.json
    $videoRunRecord = Read-JsonFile -Path $videoRun.files.json
    $vlmBlockedRecord = Read-JsonFile -Path $vlmBlocked.files.json
    $materialRunInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $materialRun.workflow_run_id -and $_.artifact_type -eq "workflow_run" }).Count -eq 1
    $videoRunInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $videoRun.workflow_run_id -and $_.artifact_type -eq "workflow_run" }).Count -eq 1
    $vlmBlockedInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $vlmBlocked.workflow_run_id -and $_.artifact_type -eq "workflow_run" }).Count -eq 1

    $passed = [bool](
        ($create.executed -eq $true) -and
        ($ingest.executed -eq $true) -and
        ([string]$materialRun.schema_version -like "product_creative.workflow_run.v*") -and
        ($materialRun.executed_count -eq 4) -and
        ($materialRun.stop_reason -eq "requires_user_input") -and
        (Test-Path -LiteralPath $materialRun.files.json) -and
        (Test-Path -LiteralPath $materialRun.files.markdown) -and
        ($materialRunRecord.workflow_run_id -eq $materialRun.workflow_run_id) -and
        $materialRunInManifest -and
        ($materialActions[0] -eq "register_material_asset") -and
        ($materialActions[1] -eq "analyze_material_image") -and
        ($materialActions[2] -eq "align_visual_analysis") -and
        ($materialActions[3] -eq "rebuild_material_cards") -and
        ($materialRun.recommended_next_action.action -eq "prepare_task_material_pack") -and
        ($learningPreferenceCount -eq 0) -and
        ($videoRun.executed_count -eq 3) -and
        ($videoRunRecord.workflow_run_id -eq $videoRun.workflow_run_id) -and
        $videoRunInManifest -and
        ($videoActions[0] -eq "resolve_video_intent") -and
        ($videoActions[1] -eq "create_video_brief") -and
        ($videoActions[2] -eq "review_video_brief") -and
        ($videoRun.stop_reason -eq "requires_explicit_confirmation") -and
        ($videoRun.recommended_next_action.action -eq "revise_video_brief") -and
        ($latestBrief.status -ne "confirmed_for_provider_payload") -and
        ($payloadCount -eq 0) -and
        ($vlmBlocked.executed_count -eq 0) -and
        ($vlmBlockedRecord.workflow_run_id -eq $vlmBlocked.workflow_run_id) -and
        $vlmBlockedInManifest -and
        ($vlmBlocked.stop_reason -eq "requires_explicit_confirmation") -and
        ($vlmBlocked.execution_contract.executed -eq $false)
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        material_run_actions = $materialActions
        material_run_stop_reason = $materialRun.stop_reason
        material_run_executed_count = $materialRun.executed_count
        learning_image_generation_preferences = $learningPreferenceCount
        video_run_actions = $videoActions
        video_run_stop_reason = $videoRun.stop_reason
        video_run_executed_count = $videoRun.executed_count
        material_run_record = $materialRun.files.json
        video_run_record = $videoRun.files.json
        material_run_in_manifest = $materialRunInManifest
        video_run_in_manifest = $videoRunInManifest
        latest_video_brief_status = $latestBrief.status
        video_provider_payload_count = $payloadCount
        vlm_blocked_stop_reason = $vlmBlocked.stop_reason
        vlm_blocked_executed_count = $vlmBlocked.executed_count
        vlm_blocked_record = $vlmBlocked.files.json
        vlm_blocked_in_manifest = $vlmBlockedInManifest
        final_recommended_action = $videoRun.recommended_next_action.action
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
