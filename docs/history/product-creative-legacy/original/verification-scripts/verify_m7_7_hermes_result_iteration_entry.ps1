param(
    [string]$ProductId = "jindouya-jinyinhuayouzi-20260709-demo",
    [string]$ResultId = "",
    [int]$MaxTurns = 4,
    [switch]$RunChat
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot "..\..\..\..")).Path
$ProductCreative = Join-Path $ScriptRoot "product_creative.ps1"
$StartHermes = Join-Path $ScriptRoot "start_hermes_product_creative_dev.ps1"
$ProductRoot = Join-Path $RepoRoot ".hermes\product_creative\products\$ProductId"

function Invoke-ProductCreative {
    param([string[]]$CommandArgs)

    $raw = & $ProductCreative @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "product_creative.ps1 failed: $($CommandArgs -join ' ')"
    }
    return ($raw | Out-String | ConvertFrom-Json)
}

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Get-LatestResultId {
    foreach ($folder in @("generated_images", "generated_videos")) {
        $dir = Join-Path $ProductRoot "artifacts\$folder"
        if (Test-Path -LiteralPath $dir) {
            $latest = Get-ChildItem -LiteralPath $dir -Filter "*-result-*.json" -File |
                Sort-Object LastWriteTime |
                Select-Object -Last 1
            if ($latest) {
                return [System.IO.Path]::GetFileNameWithoutExtension($latest.Name)
            }
        }
    }
    return ""
}

Assert-True (Test-Path -LiteralPath $ProductRoot) "Product workspace does not exist: $ProductRoot"

if ([string]::IsNullOrWhiteSpace($ResultId)) {
    $ResultId = Get-LatestResultId
}
Assert-True (-not [string]::IsNullOrWhiteSpace($ResultId)) "No generated result was found."

$reviewMessage = "针对产品 $ProductId，请审阅生成结果 $ResultId，先生成结果审阅包，不要直接写入 Product Brain。"
$evaluateMessage = "针对产品 $ProductId，请评估生成结果 $ResultId，从结果学习但只生成建议，等待我确认。"

$reviewAdapter = Invoke-ProductCreative -CommandArgs @("conversation-adapter", "--id", $ProductId, "--message", $reviewMessage)
Assert-True ($reviewAdapter.interpreted_intent.action -eq "review_generated_result") "Conversation adapter did not infer review_generated_result."

$evaluateAdapter = Invoke-ProductCreative -CommandArgs @("conversation-adapter", "--id", $ProductId, "--message", $evaluateMessage)
Assert-True ($evaluateAdapter.interpreted_intent.action -eq "evaluate_generated_result") "Conversation adapter did not infer evaluate_generated_result."

$guard = Invoke-ProductCreative -CommandArgs @("action-guard", "--id", $ProductId, "--action", "review_generated_result")
Assert-True ($guard.allowed -eq $true) "Action guard blocked review_generated_result."

$plan = Invoke-ProductCreative -CommandArgs @("workflow-plan", "--id", $ProductId, "--action", "review_generated_result")
Assert-True ($plan.steps[0].tool -eq "product_result_review_package") "Workflow plan did not route to product_result_review_package."

$previewRaw = & $StartHermes -Query $reviewMessage -MaxTurns $MaxTurns -Yolo -PrintCommand
if ($LASTEXITCODE -ne 0) {
    throw "start_hermes_product_creative_dev.ps1 -PrintCommand failed."
}
$preview = ($previewRaw | Out-String | ConvertFrom-Json)
Assert-True ($preview.command -match "hermes_cli.main") "Hermes chat command does not call hermes_cli.main."
Assert-True ($preview.command -match "product_creative") "Hermes chat command does not enable product_creative."

$chatExitCode = $null
if ($RunChat) {
    & $StartHermes -Query $reviewMessage -MaxTurns $MaxTurns -Yolo -Quiet
    $chatExitCode = $LASTEXITCODE
    Assert-True ($chatExitCode -eq 0) "Hermes chat validation exited with code $chatExitCode."
}

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    result_id = $ResultId
    inferred_review_action = $reviewAdapter.interpreted_intent.action
    inferred_evaluate_action = $evaluateAdapter.interpreted_intent.action
    action_guard_allowed = $guard.allowed
    workflow_tool = $plan.steps[0].tool
    hermes_command_preview_ok = $true
    run_chat = [bool]$RunChat
    chat_exit_code = $chatExitCode
    external_call_performed = $false
} | ConvertTo-Json -Depth 8
