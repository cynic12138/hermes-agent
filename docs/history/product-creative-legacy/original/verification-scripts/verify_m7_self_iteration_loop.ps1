param(
    [string]$ProductId = "m7-self-iteration-test"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot "..\..\..\..")).Path
$ProductCreative = Join-Path $ScriptRoot "product_creative.ps1"
$ProductRoot = Join-Path $RepoRoot ".hermes\product_creative\products\$ProductId"

function Invoke-ProductCreative {
    param([string[]]$CommandArgs)

    $raw = & $ProductCreative @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "product_creative.ps1 failed: $($CommandArgs -join ' ')"
    }
    return ($raw | Out-String | ConvertFrom-Json)
}

function Read-JsonFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing file: $Path"
    }
    return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
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

Invoke-ProductCreative -CommandArgs @("create", "--id", $ProductId, "--name", "M7 自迭代测试产品") | Out-Null

$sourceText = @"
产品名：M7 自迭代测试产品
主打：清爽口感、冷藏即饮、适合下午茶场景
包装：浅色瓶身，要求画面干净
来源：https://example.com/source-page
FoodTalks 参考资料，仅用于测试过滤，不应该进入生成卖点
本轮生成目标：测试结果评估闭环，不能变成产品事实
"@

Invoke-ProductCreative -CommandArgs @("ingest", "--id", $ProductId, "--text", $sourceText) | Out-Null
$stateExport = Invoke-ProductCreative -CommandArgs @("state-export", "--id", $ProductId)
$state = $stateExport.state
$safeText = (($state.generation_safe.selling_points + @($state.generation_safe.brief)) -join " ")

Assert-True (-not $safeText.Contains("http")) "generation_safe still contains URL text."
Assert-True (-not $safeText.Contains("FoodTalks")) "generation_safe still contains source marker text."
Assert-True (-not $safeText.Contains("本轮生成目标")) "generation_safe still contains test goal text."
Assert-True (($state.generation_safe.selling_points | Measure-Object).Count -ge 1) "generation_safe has no usable selling point."

$resultDir = Join-Path $ProductRoot "artifacts\generated_images"
New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
$resultId = "image-result-m7-fixture"
$resultPath = Join-Path $resultDir "$resultId.json"
$imagePath = Join-Path $resultDir "$resultId.png"
[byte[]]$png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
[System.IO.File]::WriteAllBytes($imagePath, $png)

$fixture = [ordered]@{
    schema_version = "product_creative.generation_result.v0.6.1"
    result_id = $resultId
    job_id = "generation-job-m7-fixture"
    product_id = $ProductId
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    provider = "fixture-provider"
    brief_type = "image"
    mode = "fixture"
    status = "completed"
    external_call_performed = $false
    source_payload_id = ""
    outputs = @(
        [ordered]@{
            type = "image"
            path = "artifacts\generated_images\$resultId.png"
            mime_type = "image/png"
            description = "Fixture image result for M7 self-iteration validation."
        }
    )
    review = [ordered]@{
        requires_human_review = $true
        ready_for_feedback = $true
        notes = "Fixture is ready for feedback."
    }
    summary = "Fixture completed image result."
}
$fixture | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $resultPath -Encoding UTF8

$review = Invoke-ProductCreative -CommandArgs @("result-review-package", "--id", $ProductId, "--result", $resultId)
Assert-True ($review.package.source_result_id -eq $resultId) "Result review package does not reference fixture result."

$feedback = Invoke-ProductCreative -CommandArgs @(
    "result-feedback",
    "--id", $ProductId,
    "--result", $resultId,
    "--selected",
    "--rating", "5",
    "--allow-evolve",
    "--note", "主体清晰，冷藏即饮场景适合，但下一轮要继续保持浅色干净背景。",
    "--like-reason", "浅色干净背景适合产品",
    "--subject-clarity", "5",
    "--product-recognizability", "5",
    "--composition", "4",
    "--style-fit", "5",
    "--copy-fit", "4",
    "--packaging-fidelity", "4",
    "--factuality", "5"
)
Assert-True ($feedback.eligible_for_evolution_proposal -eq $true) "Feedback should be eligible for evolution proposal."

$evaluation = Invoke-ProductCreative -CommandArgs @("result-evaluate", "--id", $ProductId, "--result", $resultId, "--feedback", $feedback.feedback_id)
Assert-True ($evaluation.proposed_update_count -ge 1) "Result evaluation produced no proposed updates."

$proposal = Invoke-ProductCreative -CommandArgs @("evolve", "--id", $ProductId)
$proposalRaw = Get-Content -LiteralPath $proposal.proposal_path -Raw
Assert-True ($proposalRaw.Contains("source_evaluation_id")) "Evolution proposal did not absorb result evaluation."

$apply = Invoke-ProductCreative -CommandArgs @("evolve", "--id", $ProductId, "--apply", $proposal.proposal_id)
Assert-True (($apply.applied_updates | Measure-Object).Count -ge 1) "No proposal updates were applied."

$next = Invoke-ProductCreative -CommandArgs @("generate", "--id", $ProductId, "--target", "ecommerce-main-image-copy", "--variants", "1")
$nextPath = $next.artifact_json
$nextPayload = Read-JsonFile -Path $nextPath
$nextText = $nextPayload | ConvertTo-Json -Depth 20

Assert-True ($nextText.Contains("浅色干净背景") -or $nextText.Contains("冷藏即饮")) "Next generation did not read applied M7 learning."

Invoke-ProductCreative -CommandArgs @("artifact-manifest", "--id", $ProductId) | Out-Null

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    result_id = $resultId
    generation_safe_selling_points = $state.generation_safe.selling_points
    result_review_package = $review.files.json
    result_feedback = $feedback.files.json
    result_evaluation = $evaluation.files.json
    proposal_id = $proposal.proposal_id
    applied_update_count = ($apply.applied_updates | Measure-Object).Count
    next_generation = $next.artifact_json
} | ConvertTo-Json -Depth 8
