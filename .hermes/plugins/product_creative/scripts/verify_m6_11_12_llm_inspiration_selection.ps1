param(
    [string]$ProductId = "m6-llm-inspiration-selection-test",
    [switch]$RunLlm
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProductCreative = Join-Path $ScriptRoot "product_creative.ps1"

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

Invoke-ProductCreative -CommandArgs @("create", "--id", $ProductId, "--name", "M6 LLM Inspiration Selection Test") | Out-Null
Invoke-ProductCreative -CommandArgs @(
    "ingest",
    "--id", $ProductId,
    "--text", "A bottled honey dew drink for testing external inspiration selection. Keep inspiration separate from confirmed product facts."
) | Out-Null

$xhsSnapshot = Invoke-ProductCreative -CommandArgs @(
    "external-source",
    "--id", $ProductId,
    "--provider", "manual",
    "--mode", "dry_run",
    "--channel", "xiaohongshu",
    "--query", "honey drink xiaohongshu inspiration",
    "--text", "小红书笔记：蜂蜜露饮品适合午后轻负担补水场景，标题强调清甜、仪式感、姐妹分享。避免功效承诺。",
    "--limit", "1"
)
Assert-True ($xhsSnapshot.snapshot.channel -eq "xiaohongshu") "XHS snapshot channel was not saved."

$douyinSnapshot = Invoke-ProductCreative -CommandArgs @(
    "external-source",
    "--id", $ProductId,
    "--provider", "manual",
    "--mode", "dry_run",
    "--channel", "douyin",
    "--query", "honey drink douyin inspiration",
    "--text", "抖音脚本文案：前三秒用冰块入杯和蜂蜜拉丝做钩子，中段展示开盖、倒入、举杯，结尾用今日清甜补水收束。避免医疗功效。",
    "--limit", "1"
)
Assert-True ($douyinSnapshot.snapshot.channel -eq "douyin") "Douyin snapshot channel was not saved."

$xhsCandidates = Invoke-ProductCreative -CommandArgs @(
    "inspiration-candidates",
    "--id", $ProductId,
    "--snapshot", $xhsSnapshot.snapshot_id,
    "--goal", "Mine XHS note inspiration.",
    "--max-candidates", "3"
)
Assert-True ($xhsCandidates.candidate_count -gt 0) "No XHS candidates were produced."

$douyinCandidates = Invoke-ProductCreative -CommandArgs @(
    "inspiration-candidates",
    "--id", $ProductId,
    "--snapshot", $douyinSnapshot.snapshot_id,
    "--goal", "Mine Douyin video hook inspiration.",
    "--max-candidates", "3"
)
Assert-True ($douyinCandidates.candidate_count -gt 0) "No Douyin candidates were produced."

$xhsPack = Invoke-ProductCreative -CommandArgs @(
    "inspiration-pack",
    "--id", $ProductId,
    "--target", "xiaohongshu-seeding-note",
    "--goal", "Select XHS-only primary inspiration.",
    "--limit", "1"
)
Assert-True ($xhsPack.inspiration_pack.target_channel -eq "xiaohongshu") "XHS pack did not infer target channel."
$xhsSelected = @($xhsPack.inspiration_pack.candidates)[0]
Assert-True ($xhsSelected.channel -eq "xiaohongshu") "XHS pack selected a non-XHS primary candidate."
Assert-True ($xhsSelected.selection_role -eq "primary") "XHS pack candidate was not marked primary."

$douyinPack = Invoke-ProductCreative -CommandArgs @(
    "inspiration-pack",
    "--id", $ProductId,
    "--target", "douyin-short-video-script",
    "--goal", "Select Douyin-only primary inspiration.",
    "--limit", "1"
)
Assert-True ($douyinPack.inspiration_pack.target_channel -eq "douyin") "Douyin pack did not infer target channel."
$douyinSelected = @($douyinPack.inspiration_pack.candidates)[0]
Assert-True ($douyinSelected.channel -eq "douyin") "Douyin pack selected a non-Douyin primary candidate."
Assert-True ($douyinSelected.selection_role -eq "primary") "Douyin pack candidate was not marked primary."

$llmPack = $null
if ($RunLlm) {
    $llmPack = Invoke-ProductCreative -CommandArgs @(
        "llm-inspiration-pack",
        "--id", $ProductId,
        "--snapshot", $xhsSnapshot.snapshot_id,
        "--goal", "Use Hermes DeepSeek to deeply summarize XHS inspiration. Do not treat sources as product facts.",
        "--target", "xiaohongshu-seeding-note",
        "--channel", "xiaohongshu",
        "--max-items", "1"
    )
    Assert-True ($llmPack.status -eq "review_required") "LLM inspiration pack should require review."
    Assert-True (-not [string]::IsNullOrWhiteSpace($llmPack.llm.call_mode)) "LLM call mode was not recorded."
    Assert-True ($llmPack.llm_inspiration_pack.review_contract.must_be_reviewed_by_user -eq $true) "LLM review contract is missing."
}

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    xhs_snapshot_id = $xhsSnapshot.snapshot_id
    douyin_snapshot_id = $douyinSnapshot.snapshot_id
    xhs_pack_id = $xhsPack.pack_id
    xhs_pack_channel = $xhsPack.inspiration_pack.target_channel
    douyin_pack_id = $douyinPack.pack_id
    douyin_pack_channel = $douyinPack.inspiration_pack.target_channel
    llm_called = [bool]$RunLlm
    llm_pack_id = if ($llmPack) { $llmPack.pack_id } else { "" }
    external_call_performed = $false
    note = "M6.11-M6.12 contract verified. Use -RunLlm to perform a real Hermes LLM call."
} | ConvertTo-Json -Depth 8
