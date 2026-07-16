param(
  [string]$ProductId = "jindouya-jinyinhuayouzi-20260709-demo",
  [string]$AssetId = "",
  [int]$Duration = 3,
  [int]$Fps = 8
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cli = Join-Path $scriptDir "product_creative.ps1"

function Invoke-ProductCreativeJson {
  param([string[]]$CommandArgs)
  $raw = & $cli @CommandArgs
  if ($LASTEXITCODE -ne 0) {
    throw "product_creative.ps1 failed: $raw"
  }
  return ($raw | ConvertFrom-Json)
}

Push-Location (Resolve-Path (Join-Path $scriptDir "..\..\..\.."))
try {
  python -m py_compile `
    ".hermes\plugins\product_creative\capabilities\video\exact_video_service.py" `
    ".hermes\plugins\product_creative\capabilities\review\task_overview_service.py" `
    ".hermes\plugins\product_creative\capabilities\learning\result_evaluation_service.py" `
    ".hermes\plugins\product_creative\cli.py" `
    ".hermes\plugins\product_creative\tools.py" `
    ".hermes\plugins\product_creative\workflow.py"

  $adapter = Invoke-ProductCreativeJson @(
    "conversation-adapter",
    "--id", $ProductId,
    "--message", "用当前主图生成一个动漫故事推广视频，主图不能变"
  )
  if ($adapter.interpreted_intent.action -ne "compose_exact_main_video") {
    throw "conversation adapter did not route to compose_exact_main_video"
  }

  $exactArgs = @(
    "exact-main-video",
    "--id", $ProductId,
    "--theme", "M8验证：固定主图的动漫故事推广视频",
    "--duration", "$Duration",
    "--fps", "$Fps"
  )
  if ($AssetId.Trim()) {
    $exactArgs += @("--asset", $AssetId)
  }
  $exact = Invoke-ProductCreativeJson $exactArgs
  if (-not $exact.success) {
    throw "exact-main-video failed"
  }
  if ($exact.result.main_image_policy.locked -ne $true) {
    throw "main image policy is not locked"
  }
  if ($exact.result.external_call_performed -ne $false) {
    throw "exact-main-video must not perform external calls"
  }
  $videoPath = $exact.files.video
  if (-not (Test-Path -LiteralPath $videoPath)) {
    throw "composed video file was not created: $videoPath"
  }

  $review = Invoke-ProductCreativeJson @(
    "result-review-package",
    "--id", $ProductId,
    "--result", $exact.result_id
  )
  if (-not $review.package.product_identity_review.main_image_locked) {
    throw "result review package did not expose main image lock review"
  }

  $overview = Invoke-ProductCreativeJson @(
    "task-overview-package",
    "--id", $ProductId,
    "--result", $exact.result_id,
    "--title", "M8验证总览包"
  )
  if (-not $overview.success) {
    throw "task overview package failed"
  }

  [pscustomobject]@{
    success = $true
    product_id = $ProductId
    routed_action = $adapter.interpreted_intent.action
    result_id = $exact.result_id
    video = $exact.files.video
    preview_gif = $exact.files.preview_gif
    review_package_id = $review.result_review_package_id
    task_overview_package_id = $overview.task_overview_package_id
    external_call_performed = $false
  } | ConvertTo-Json -Depth 8
}
finally {
  Pop-Location
}
