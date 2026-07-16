param(
    [string]$ProductId = "zhou15-honeydew-m6-real-test",
    [string]$ProductName = "周十五蜂蜜露",
    [string]$ProductText = "周十五蜂蜜露是一款围绕蜂蜜露主题进行内容创作测试的产品。当前测试只验证 Product Brain、外部灵感、LLM 灵感总结和后续生成上下文的链路，不把外部素材当成产品事实。",
    [string]$Query = "蜂蜜饮品",
    [int]$Limit = 2,
    [int]$WaitSeconds = 180,
    [switch]$RunLive,
    [switch]$RequireLive,
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

function Test-Endpoint {
    param([string]$Url)

    try {
        Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 5 | Out-Null
        return $true
    }
    catch {
        return $false
    }
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

$safeLimit = [Math]::Max(1, [Math]::Min($Limit, 3))

Invoke-ProductCreative -CommandArgs @("create", "--id", $ProductId, "--name", $ProductName) | Out-Null
Invoke-ProductCreative -CommandArgs @("ingest", "--id", $ProductId, "--text", $ProductText) | Out-Null

$snapshots = @()
$liveAttempted = $false
$liveItems = 0

if ($RunLive) {
    $xhsHealth = Test-Endpoint -Url "http://127.0.0.1:8787/api/health"
    $douyinHealth = Test-Endpoint -Url "http://127.0.0.1:8000/api/health"
    if ($RequireLive) {
        Assert-True ($xhsHealth -or $douyinHealth) "No XHS or Douyin sidecar endpoint is available."
    }

    if ($xhsHealth) {
        $liveAttempted = $true
        $xhs = Invoke-ProductCreative -CommandArgs @(
            "external-source",
            "--id", $ProductId,
            "--provider", "xiaohongshu-sidecar",
            "--mode", "live",
            "--query", $Query,
            "--limit", "$safeLimit",
            "--wait-seconds", "$WaitSeconds",
            "--auto-browser-cookie"
        )
        $liveItems += [int]$xhs.items_count
        if ($xhs.items_count -gt 0) {
            $snapshots += $xhs
        }
    }

    if ($douyinHealth) {
        $liveAttempted = $true
        $douyin = Invoke-ProductCreative -CommandArgs @(
            "external-source",
            "--id", $ProductId,
            "--provider", "douyin-sidecar",
            "--mode", "live",
            "--query", $Query,
            "--limit", "$safeLimit",
            "--wait-seconds", "$WaitSeconds",
            "--transcribe-limit", "1"
        )
        $liveItems += [int]$douyin.items_count
        if ($douyin.items_count -gt 0) {
            $snapshots += $douyin
        }
    }

    if ($RequireLive) {
        Assert-True ($liveItems -gt 0) "Live sidecars did not return usable items."
    }
}

if ($snapshots.Count -eq 0) {
    $snapshots += Invoke-ProductCreative -CommandArgs @(
        "external-source",
        "--id", $ProductId,
        "--provider", "manual",
        "--mode", "dry_run",
        "--channel", "xiaohongshu",
        "--query", "$Query 小红书",
        "--text", "小红书灵感：用真实饮用场景、清甜口感、午后分享、开瓶仪式感作为种草角度。不得生成医疗、功效或未确认成分承诺。",
        "--limit", "1"
    )
    $snapshots += Invoke-ProductCreative -CommandArgs @(
        "external-source",
        "--id", $ProductId,
        "--provider", "manual",
        "--mode", "dry_run",
        "--channel", "douyin",
        "--query", "$Query 抖音",
        "--text", "抖音灵感：前三秒用冰块、倒饮品、蜂蜜色泽建立视觉钩子，中段突出产品出现和饮用动作，结尾做今日清甜选择。不得生成未确认产品事实。",
        "--limit", "1"
    )
}

$candidateTotal = 0
$packIds = @()
$llmPackIds = @()
foreach ($snapshot in $snapshots) {
    $target = if ($snapshot.snapshot.channel -eq "douyin") { "douyin-short-video-script" } else { "xiaohongshu-seeding-note" }
    if ($RunLlm) {
        $llm = Invoke-ProductCreative -CommandArgs @(
            "llm-inspiration-pack",
            "--id", $ProductId,
            "--snapshot", $snapshot.snapshot_id,
            "--goal", "基于 $ProductName 和外部素材做深度灵感总结。只输出创作灵感，不写入 Product Brain，不当作产品事实。",
            "--target", $target,
            "--channel", $snapshot.snapshot.channel,
            "--max-items", "2"
        )
        Assert-True ($llm.status -eq "review_required") "LLM pack should require user review."
        $llmPackIds += $llm.pack_id
    }
    else {
        $candidates = Invoke-ProductCreative -CommandArgs @(
            "inspiration-candidates",
            "--id", $ProductId,
            "--snapshot", $snapshot.snapshot_id,
            "--goal", "Mine target-specific inspiration for $ProductName.",
            "--max-candidates", "3"
        )
        $candidateTotal += [int]$candidates.candidate_count
        $pack = Invoke-ProductCreative -CommandArgs @(
            "inspiration-pack",
            "--id", $ProductId,
            "--target", $target,
            "--goal", "Package inspiration for $ProductName generation.",
            "--limit", "2"
        )
        Assert-True ($pack.candidate_count -gt 0) "Inspiration pack is empty."
        $packIds += $pack.pack_id
    }
}

$context = Invoke-ProductCreative -CommandArgs @("context", "--id", $ProductId, "--target", "xiaohongshu-seeding-note")
Assert-True ($context.product_id -eq $ProductId) "Context pack product id mismatch."

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    product_name = $ProductName
    live_requested = [bool]$RunLive
    live_attempted = $liveAttempted
    live_items = $liveItems
    snapshots = @($snapshots | ForEach-Object { $_.snapshot_id })
    rule_candidate_count = $candidateTotal
    rule_pack_ids = $packIds
    llm_called = [bool]$RunLlm
    llm_pack_ids = $llmPackIds
    context_product_id = $context.product_id
    external_call_performed = $liveAttempted
    note = "M6.13 real-product workspace validation completed without hard-coding the product into core code."
} | ConvertTo-Json -Depth 8
