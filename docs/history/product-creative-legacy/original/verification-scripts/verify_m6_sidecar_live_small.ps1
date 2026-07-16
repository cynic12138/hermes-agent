param(
    [string]$ProductId = "m6-sidecar-live-test",
    [string]$Query = "蜂蜜饮品",
    [int]$Limit = 2,
    [int]$WaitSeconds = 180,
    [switch]$RunLive,
    [switch]$RequireItems
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
Invoke-ProductCreative -CommandArgs @("create", "--id", $ProductId, "--name", "M6 Sidecar Live Test") | Out-Null
Invoke-ProductCreative -CommandArgs @("ingest", "--id", $ProductId, "--text", "A product workspace used only for small M6 live sidecar validation.") | Out-Null

if (-not $RunLive) {
    [pscustomobject]@{
        success = $true
        product_id = $ProductId
        live_requested = $false
        external_call_performed = $false
        note = "Pass -RunLive to perform small XHS/Douyin sidecar collection."
    } | ConvertTo-Json -Depth 6
    exit 0
}

$xhsHealth = Test-Endpoint -Url "http://127.0.0.1:8787/api/health"
$douyinHealth = Test-Endpoint -Url "http://127.0.0.1:8000/api/health"

$xhs = $null
$xhsCandidates = $null
$xhsPack = $null
if ($xhsHealth) {
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
    if ($xhs.items_count -gt 0) {
        $xhsCandidates = Invoke-ProductCreative -CommandArgs @(
            "inspiration-candidates",
            "--id", $ProductId,
            "--snapshot", $xhs.snapshot_id,
            "--goal", "Mine XHS seeding-note inspiration without treating it as product facts.",
            "--max-candidates", "3"
        )
        $xhsPack = Invoke-ProductCreative -CommandArgs @(
            "inspiration-pack",
            "--id", $ProductId,
            "--target", "xiaohongshu-seeding-note",
            "--limit", "3"
        )
    }
}

$douyin = $null
$douyinCandidates = $null
$douyinPack = $null
if ($douyinHealth) {
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
    if ($douyin.items_count -gt 0) {
        $douyinCandidates = Invoke-ProductCreative -CommandArgs @(
            "inspiration-candidates",
            "--id", $ProductId,
            "--snapshot", $douyin.snapshot_id,
            "--goal", "Mine Douyin hook/copy inspiration without treating it as product facts.",
            "--max-candidates", "3"
        )
        $douyinPack = Invoke-ProductCreative -CommandArgs @(
            "inspiration-pack",
            "--id", $ProductId,
            "--target", "douyin-short-video-script",
            "--limit", "3"
        )
    }
}

if ($RequireItems) {
    Assert-True ($xhsHealth -or $douyinHealth) "No sidecar health endpoint is available."
    Assert-True (($xhs -and $xhs.items_count -gt 0) -or ($douyin -and $douyin.items_count -gt 0)) "No live sidecar returned sanitized items."
}

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    query = $Query
    live_requested = $true
    xhs = @{
        health = $xhsHealth
        status = if ($xhs) { $xhs.status } else { "not_run" }
        items_count = if ($xhs) { $xhs.items_count } else { 0 }
        snapshot_id = if ($xhs) { $xhs.snapshot_id } else { "" }
        candidate_count = if ($xhsCandidates) { $xhsCandidates.candidate_count } else { 0 }
        pack_id = if ($xhsPack) { $xhsPack.pack_id } else { "" }
    }
    douyin = @{
        health = $douyinHealth
        status = if ($douyin) { $douyin.status } else { "not_run" }
        items_count = if ($douyin) { $douyin.items_count } else { 0 }
        snapshot_id = if ($douyin) { $douyin.snapshot_id } else { "" }
        candidate_count = if ($douyinCandidates) { $douyinCandidates.candidate_count } else { 0 }
        pack_id = if ($douyinPack) { $douyinPack.pack_id } else { "" }
    }
    external_call_performed = ($xhsHealth -or $douyinHealth)
    credential_policy = "No cookies or API keys are written by Product Creative artifacts."
} | ConvertTo-Json -Depth 8
