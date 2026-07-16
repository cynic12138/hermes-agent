param(
  [string]$ProductId = "jindouya-jinyinhuayouzi-20260709-demo",
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
    ".hermes\plugins\product_creative\schemas.py" `
    ".hermes\plugins\product_creative\workflow.py"

  $adapter = Invoke-ProductCreativeJson @(
    "conversation-adapter",
    "--id", $ProductId,
    "--message", "用当前主图做一个夏日清爽动漫故事推广视频，主图不能变"
  )
  if ($adapter.interpreted_intent.action -ne "compose_exact_main_video") {
    throw "conversation adapter did not route to compose_exact_main_video"
  }
  $inferredTemplate = $adapter.plan.steps[0].args_template.template
  if ($inferredTemplate -ne "summer_refresh") {
    throw "conversation adapter did not infer summer_refresh template"
  }

  $workflowExecution = Invoke-ProductCreativeJson @(
    "workflow-execute",
    "--id", $ProductId,
    "--message", "用当前主图做一个怕添加痛点解决动漫故事推广视频，主图不能变，$($Duration)秒 $($Fps)fps"
  )
  if (-not $workflowExecution.executed) {
    throw "workflow-execute did not execute compose_exact_main_video"
  }
  if ($workflowExecution.plan.requested_action -ne "compose_exact_main_video") {
    throw "workflow-execute did not choose compose_exact_main_video"
  }
  if ($workflowExecution.plan.steps[0].args_template.template -ne "problem_solution") {
    throw "workflow-execute did not infer problem_solution template"
  }
  $exact = $workflowExecution.result
  if (-not $exact.success) {
    throw "workflow exact-main-video failed"
  }
  if ($exact.result.template -ne "problem_solution") {
    throw "workflow exact-main-video did not use requested template"
  }
  if ($exact.result.main_image_policy.locked -ne $true) {
    throw "main image policy is not locked"
  }
  if ($exact.result.external_call_performed -ne $false) {
    throw "exact-main-video must not perform external calls"
  }
  if (-not (Test-Path -LiteralPath $exact.files.video)) {
    throw "composed video file was not created: $($exact.files.video)"
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
    "--title", "M8 closeout 总览包"
  )
  if (-not $overview.success) {
    throw "task overview package failed"
  }

  $feedback = Invoke-ProductCreativeJson @(
    "result-feedback",
    "--id", $ProductId,
    "--result", $exact.result_id,
    "--note", "通过：主图固定正确，剧情围绕产品展开；后续保持主图不重绘，只在外部做动漫故事动效。",
    "--selected",
    "--rating", "5",
    "--allow-evolve",
    "--like-reason", "主图固定不重绘",
    "--like-reason", "剧情围绕产品展开",
    "--product-recognizability", "5",
    "--motion-quality", "4",
    "--scene-fit", "5",
    "--factuality", "5"
  )
  if (-not $feedback.eligible_for_evolution_proposal) {
    throw "M8 feedback should be eligible for reviewable evolution proposal"
  }

  $evaluation = Invoke-ProductCreativeJson @(
    "result-evaluate",
    "--id", $ProductId,
    "--result", $exact.result_id,
    "--feedback", $feedback.feedback_id
  )
  if (-not $evaluation.success) {
    throw "result-evaluate failed"
  }
  if ($evaluation.evaluation.mutates_product_brain -ne $false) {
    throw "result evaluation must not directly mutate Product Brain"
  }
  if ([int]$evaluation.proposed_update_count -lt 1) {
    throw "result evaluation did not produce reviewable learning candidates"
  }

  [pscustomobject]@{
    success = $true
    product_id = $ProductId
    routed_action = $adapter.interpreted_intent.action
    inferred_template = $inferredTemplate
    workflow_action = $workflowExecution.plan.requested_action
    result_id = $exact.result_id
    result_template = $exact.result.template
    video = $exact.files.video
    preview_gif = $exact.files.preview_gif
    review_package_id = $review.result_review_package_id
    task_overview_package_id = $overview.task_overview_package_id
    feedback_id = $feedback.feedback_id
    result_evaluation_id = $evaluation.result_evaluation_id
    proposed_update_count = $evaluation.proposed_update_count
    external_call_performed = $false
  } | ConvertTo-Json -Depth 8
}
finally {
  Pop-Location
}
