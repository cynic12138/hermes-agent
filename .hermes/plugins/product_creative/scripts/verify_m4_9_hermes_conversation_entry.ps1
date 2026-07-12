param(
    [switch]$RunHermesChat
)

$ErrorActionPreference = "Stop"

function Invoke-JsonScript {
    param(
        [string]$ScriptPath,
        [string[]]$InputArgs
    )

    $raw = & $ScriptPath @InputArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $ScriptPath $($InputArgs -join ' ')`n$raw"
    }
    return $raw | ConvertFrom-Json
}

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$startChat = Join-Path $PSScriptRoot "start_hermes_product_creative_dev.ps1"
$diagnose = Join-Path $PSScriptRoot "diagnose_hermes_runtime.ps1"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$productId = "m49-dialogue-$stamp"
$productName = "M4.9 Hermes 对话入口测试产品 $stamp"

Push-Location $repoRoot
try {
    $resolved = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workspace-resolve",
        "--query", $productName,
        "--create-if-missing",
        "--suggested-id", $productId,
        "--name", $productName
    )

    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-run",
        "--id", $resolved.selected_product_id,
        "--message", "这是一款 M4.9 验证产品，主打清甜、自然、适合日常饮用，文案表达要真实克制。",
        "--max-steps", "3"
    )

    $channelRun = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-run",
        "--id", $resolved.selected_product_id,
        "--message", "生成 3 个小红书种草文案版本",
        "--max-steps", "2"
    )

    $feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-run",
        "--id", $resolved.selected_product_id,
        "--message", "我选择第 2 版，评分 4 分，喜欢自然真实的表达，后续记住这种克制风格。",
        "--max-steps", "2"
    )

    $feedbackLine = Get-Content ".hermes/product_creative/products/$($resolved.selected_product_id)/structured/channel_feedback.jsonl" | Select-Object -Last 1
    $feedbackRecord = $feedbackLine | ConvertFrom-Json

    $preview = & $startChat -PrintCommand -Query "测试 product_creative 对话入口" -MaxTurns 4 | ConvertFrom-Json
    $runtime = & $diagnose -UseTemporaryEnable -AsJson | ConvertFrom-Json

    $chatText = ""
    if ($RunHermesChat) {
        $chatText = & $startChat -Query "请先调用 product_workspace_resolve 定位 $($resolved.selected_product_id)，再调用 product_workflow_run 查看下一步。不要运行脚本命令。" -MaxTurns 4 -Yolo
        if ($LASTEXITCODE -ne 0) {
            throw "Hermes chat validation failed."
        }
    }

    Assert-Condition ($resolved.success -and $resolved.created -and $resolved.selected_product_id -eq $productId) "workspace-resolve did not create the expected product."
    Assert-Condition ($ingest.executed_count -ge 1) "Natural-language ingest did not execute."
    Assert-Condition ([string]::IsNullOrWhiteSpace($ingest.recommended_next_action.user_next_message) -eq $false) "Ingest next action is missing user_next_message."
    Assert-Condition ($channelRun.post_status.status -eq "channel_run_ready_for_review") "Channel generation did not reach review status."
    Assert-Condition ($feedbackRecord.variant -eq 2) "Feedback variant was not parsed from natural language."
    Assert-Condition ($feedbackRecord.rating -eq 4) "Feedback rating was not parsed from natural language."
    Assert-Condition ($feedbackRecord.selected -eq $true) "Feedback selected flag was not parsed."
    Assert-Condition ($feedbackRecord.eligible_for_evolution_proposal -eq $true) "Feedback did not become eligible for an evolution proposal."
    Assert-Condition ($feedback.recommended_next_action.action -eq "apply_evolution_proposal") "Feedback loop did not stop at proposal apply."
    Assert-Condition ($feedback.recommended_next_action.mutates_product_brain -eq $true) "Proposal apply is not marked as Product Brain mutation."
    Assert-Condition ([string]::IsNullOrWhiteSpace($feedback.recommended_next_action.user_next_message) -eq $false) "Proposal apply next action is missing user_next_message."
    Assert-Condition ($preview.command -like "*hermes_cli.main chat*") "Dev chat command preview is missing Hermes chat invocation."
    Assert-Condition ($preview.command -like "*product_creative,skills*") "Dev chat command preview is missing product_creative toolset."
    Assert-Condition ($runtime.imports_dev_source -eq $true) "Runtime probe is not importing the development source."
    Assert-Condition ($runtime.probe.product_plugin.enabled -eq $true) "Runtime probe did not load product_creative."

    [ordered]@{
        success = $true
        schema_version = "product_creative.verify_m4_9.v1"
        product_id = $resolved.selected_product_id
        workspace_created = $resolved.created
        ingest_executed_count = $ingest.executed_count
        channel_status = $channelRun.post_status.status
        feedback_variant = $feedbackRecord.variant
        feedback_rating = $feedbackRecord.rating
        feedback_selected = $feedbackRecord.selected
        next_action = $feedback.recommended_next_action.action
        next_user_message = $feedback.recommended_next_action.user_next_message
        dev_chat_command_preview_ok = $true
        runtime_imports_dev_source = $runtime.imports_dev_source
        desktop_exe_exists = $runtime.desktop_exe_exists
        hermes_chat_checked = [bool]$RunHermesChat
        hermes_chat_output = $chatText
    } | ConvertTo-Json -Depth 8
}
finally {
    Pop-Location
}
