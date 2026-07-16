param(
    [string]$ProductId = "m6-hermes-chat-inspiration-test",
    [string]$ProductName = "M6 Hermes Chat Inspiration Test",
    [string]$SnapshotId = "",
    [int]$MaxTurns = 6,
    [switch]$RunChat
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProductCreative = Join-Path $ScriptRoot "product_creative.ps1"
$StartHermes = Join-Path $ScriptRoot "start_hermes_product_creative_dev.ps1"

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

Invoke-ProductCreative -CommandArgs @("create", "--id", $ProductId, "--name", $ProductName) | Out-Null
Invoke-ProductCreative -CommandArgs @(
    "ingest",
    "--id", $ProductId,
    "--text", "Workspace for validating Hermes chat entry into M6 external inspiration and LLM summary flow."
) | Out-Null

if ([string]::IsNullOrWhiteSpace($SnapshotId)) {
    $snapshot = Invoke-ProductCreative -CommandArgs @(
        "external-source",
        "--id", $ProductId,
        "--provider", "manual",
        "--mode", "dry_run",
        "--channel", "xiaohongshu",
        "--query", "chat inspiration fixture",
        "--text", "小红书灵感：用清甜饮品日常场景做内容，不把外部素材当产品事实。",
        "--limit", "1"
    )
    $SnapshotId = $snapshot.snapshot_id
}

$llmMessage = "针对产品 $ProductId，请基于外部灵感 snapshot $SnapshotId，用 DeepSeek 做小红书 LLM 深度总结灵感，生成后停下让我审阅，不要沉淀到灵感库。"
$confirmMessage = "我确认沉淀灵感到灵感库，备注：已人工审阅，作为创作灵感使用，不作为产品事实。"

$adapter = Invoke-ProductCreative -CommandArgs @(
    "conversation-adapter",
    "--id", $ProductId,
    "--message", $llmMessage
)
Assert-True ($adapter.interpreted_intent.action -eq "create_llm_inspiration_pack") "Conversation adapter did not infer create_llm_inspiration_pack."

$confirmAdapter = Invoke-ProductCreative -CommandArgs @(
    "conversation-adapter",
    "--id", $ProductId,
    "--message", $confirmMessage,
    "--confirmed"
)
Assert-True ($confirmAdapter.interpreted_intent.action -eq "confirm_inspiration_library_entry") "Conversation adapter did not infer confirm_inspiration_library_entry."
Assert-True ($confirmAdapter.interpreted_intent.confirmed -eq $true) "Conversation adapter did not preserve explicit confirmation."

$previewRaw = & $StartHermes -Query $llmMessage -MaxTurns $MaxTurns -Yolo -PrintCommand
if ($LASTEXITCODE -ne 0) {
    throw "start_hermes_product_creative_dev.ps1 -PrintCommand failed."
}
$preview = ($previewRaw | Out-String | ConvertFrom-Json)
Assert-True ($preview.command -match "hermes_cli.main") "Hermes chat command does not call hermes_cli.main."
Assert-True ($preview.command -match "product_creative") "Hermes chat command does not enable product_creative toolset/skill."

$chatExitCode = $null
if ($RunChat) {
    & $StartHermes -Query $llmMessage -MaxTurns $MaxTurns -Yolo -Quiet
    $chatExitCode = $LASTEXITCODE
    Assert-True ($chatExitCode -eq 0) "Hermes chat validation exited with code $chatExitCode."
}

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    snapshot_id = $SnapshotId
    inferred_llm_action = $adapter.interpreted_intent.action
    inferred_confirm_action = $confirmAdapter.interpreted_intent.action
    print_command_valid = $true
    hermes_home = $preview.hermes_home
    run_chat = [bool]$RunChat
    chat_exit_code = $chatExitCode
    external_call_performed = $false
    note = "M6.15 Hermes chat entry verified. Use -RunChat for an actual Hermes CLI conversation run."
} | ConvertTo-Json -Depth 8
