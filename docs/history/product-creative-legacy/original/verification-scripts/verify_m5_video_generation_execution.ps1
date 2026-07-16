param(
    [string]$ProductId = ""
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot "..\..\..\..")).Path
$Tool = Join-Path $ScriptRoot "product_creative.ps1"

function Invoke-ProductCreative {
    param([string[]]$CommandArgs)

    $json = & $Tool @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "product_creative.ps1 failed: $($CommandArgs -join ' ')`n$json"
    }
    return ($json | ConvertFrom-Json)
}

function Get-LocalEnvValue {
    param([string]$Name)

    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ($value) {
        return $value
    }
    $value = [Environment]::GetEnvironmentVariable($Name, "User")
    if ($value) {
        return $value
    }
    return ""
}

Push-Location $RepoRoot
try {
    if (-not $ProductId) {
        $ProductId = "m5-video-exec-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    }

    $imagePath = Join-Path $env:TEMP "$ProductId.png"
    $tinyPng = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    [IO.File]::WriteAllBytes($imagePath, [Convert]::FromBase64String($tinyPng))

    Invoke-ProductCreative -CommandArgs @("create", "--id", $ProductId, "--name", "M5 视频执行验证产品") | Out-Null
    Invoke-ProductCreative -CommandArgs @("ingest", "--id", $ProductId, "--text", "M5 验证产品：清爽果蜜饮品，适合夏日饮用，主线验证视频生成执行闭环。") | Out-Null
    $asset = Invoke-ProductCreative -CommandArgs @("asset-register", "--id", $ProductId, "--path", $imagePath, "--role", "current_main_image", "--usage", "product_reference", "--usage", "video_first_frame")
    Invoke-ProductCreative -CommandArgs @("asset-bind-url", "--id", $ProductId, "--asset", $asset.material_id, "--url", "https://ark-project.tos-cn-beijing.volces.com/doc_image/r2v_tea_pic1.jpg", "--usage", "video_first_frame", "--note", "M5 verification provider-accessible reference URL") | Out-Null
    $analysis = Invoke-ProductCreative -CommandArgs @("image-analyze", "--id", $ProductId, "--asset", $asset.material_id, "--provider", "mock-vision")
    Invoke-ProductCreative -CommandArgs @("visual-align", "--id", $ProductId, "--analysis", $analysis.analysis_id) | Out-Null
    Invoke-ProductCreative -CommandArgs @("material-card-rebuild", "--id", $ProductId) | Out-Null
    $intent = Invoke-ProductCreative -CommandArgs @("video-intent", "--id", $ProductId, "--message", "用当前主图和素材库生成今天的抖音视频")
    $brief = Invoke-ProductCreative -CommandArgs @("video-brief", "--id", $ProductId, "--intent", $intent.intent_id)
    $review = Invoke-ProductCreative -CommandArgs @("video-brief-review", "--id", $ProductId, "--brief", $brief.brief_id)
    $revision = Invoke-ProductCreative -CommandArgs @("video-brief-revise", "--id", $ProductId, "--brief", $brief.brief_id, "--patch", $review.editable_patch.patch_id, "--confirmed", "--note", "M5 verification confirmed video brief")
    $payload = Invoke-ProductCreative -CommandArgs @("video-generate", "--id", $ProductId, "--brief", $revision.brief_id, "--provider", "volcengine-ark-video")
    $reference = Invoke-ProductCreative -CommandArgs @("video-reference-readiness", "--id", $ProductId, "--payload", $payload.payload_id)
    if (-not $reference.ready_for_provider) {
        throw "Expected video reference readiness to pass."
    }

    $mockJob = Invoke-ProductCreative -CommandArgs @("generation-job", "--id", $ProductId, "--payload", $payload.payload_id, "--provider", "volcengine-ark-video", "--mode", "mock")
    if (-not $mockJob.result.result_id) {
        throw "Expected mock video generation job to create a generated_videos result artifact."
    }

    $liveStatus = "skipped_missing_key"
    $policyStatus = "skipped_missing_key"
    if (Get-LocalEnvValue "PRODUCT_CREATIVE_ARK_API_KEY") {
        $live = Invoke-ProductCreative -CommandArgs @("live-readiness", "--id", $ProductId, "--provider", "volcengine-ark-video", "--kind", "video", "--payload", $payload.payload_id)
        $liveStatus = $live.status
        if (-not $live.ready_for_live) {
            throw "Expected live-readiness to pass when PRODUCT_CREATIVE_ARK_API_KEY is configured."
        }
        $policy = Invoke-ProductCreative -CommandArgs @("video-execution-policy", "--id", $ProductId, "--payload", $payload.payload_id, "--provider", "volcengine-ark-video", "--confirmed", "--note", "M5 verification execution boundary only; no live task submitted")
        $policyStatus = $policy.status
        if ($policy.status -ne "approved") {
            throw "Expected confirmed video execution policy to be approved."
        }
    }

    Invoke-ProductCreative -CommandArgs @("artifact-manifest", "--id", $ProductId) | Out-Null

    [pscustomobject]@{
        success = $true
        product_id = $ProductId
        intent_id = $intent.intent_id
        brief_id = $brief.brief_id
        revised_brief_id = $revision.brief_id
        payload_id = $payload.payload_id
        reference_status = $reference.status
        mock_job_id = $mockJob.job_id
        mock_result_id = $mockJob.result.result_id
        live_readiness_status = $liveStatus
        policy_status = $policyStatus
    } | ConvertTo-Json -Depth 5
}
finally {
    Pop-Location
}
