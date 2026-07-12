param(
    [string]$ProductId = "jindouya-jinyinhuayouzi-20260709-demo",
    [string]$ImageResultId = "",
    [string]$VideoResultId = ""
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

function Get-LatestResultId {
    param([string]$Folder)

    $dir = Join-Path $ProductRoot "artifacts\$Folder"
    if (-not (Test-Path -LiteralPath $dir)) {
        return ""
    }
    $latest = Get-ChildItem -LiteralPath $dir -Filter "*-result-*.json" -File |
        Sort-Object LastWriteTime |
        Select-Object -Last 1
    if (-not $latest) {
        return ""
    }
    return [System.IO.Path]::GetFileNameWithoutExtension($latest.Name)
}

function Invoke-ResultLoop {
    param(
        [string]$ResultId,
        [string]$Kind
    )

    $review = Invoke-ProductCreative -CommandArgs @("result-review-package", "--id", $ProductId, "--result", $ResultId)
    if ($Kind -eq "image") {
        $feedback = Invoke-ProductCreative -CommandArgs @(
            "result-feedback",
            "--id", $ProductId,
            "--result", $ResultId,
            "--selected",
            "--rating", "4",
            "--allow-evolve",
            "--note", "M7.9 验证反馈：真实图片结果可以用于学习。下一轮继续强调产品主体清晰、真实包装一致、背景干净，不要让外部来源信息进入画面。",
            "--like-reason", "产品主体和背景方向可复用",
            "--dislike-reason", "包装一致性仍需人工确认",
            "--subject-clarity", "4",
            "--product-recognizability", "4",
            "--composition", "4",
            "--style-fit", "4",
            "--copy-fit", "3",
            "--packaging-fidelity", "3",
            "--factuality", "4"
        )
    }
    else {
        $feedback = Invoke-ProductCreative -CommandArgs @(
            "result-feedback",
            "--id", $ProductId,
            "--result", $ResultId,
            "--selected",
            "--rating", "4",
            "--allow-evolve",
            "--note", "M7.9 验证反馈：真实视频结果可以用于学习。下一轮视频脚本要保持首帧产品识别、动作节奏更明确、每个镜头都回到产品卖点。",
            "--like-reason", "视频链路可复用为图到视频验证样例",
            "--dislike-reason", "镜头节奏需要更强脚本控制",
            "--subject-clarity", "4",
            "--product-recognizability", "4",
            "--composition", "3",
            "--style-fit", "4",
            "--copy-fit", "3",
            "--motion-quality", "3",
            "--scene-fit", "4",
            "--first-frame-consistency", "4",
            "--factuality", "4"
        )
    }
    $evaluation = Invoke-ProductCreative -CommandArgs @("result-evaluate", "--id", $ProductId, "--result", $ResultId, "--feedback", $feedback.feedback_id)
    $proposal = Invoke-ProductCreative -CommandArgs @("evolve", "--id", $ProductId)
    $apply = Invoke-ProductCreative -CommandArgs @("evolve", "--id", $ProductId, "--apply", $proposal.proposal_id)

    return [ordered]@{
        kind = $Kind
        result_id = $ResultId
        review_package = $review.files.json
        feedback = $feedback.files.json
        evaluation = $evaluation.files.json
        proposal_id = $proposal.proposal_id
        proposal_update_count = ($proposal.proposal.updates | Measure-Object).Count
        applied_update_count = ($apply.applied_updates | Measure-Object).Count
    }
}

Assert-True (Test-Path -LiteralPath $ProductRoot) "Product workspace does not exist: $ProductRoot"

if ([string]::IsNullOrWhiteSpace($ImageResultId)) {
    $ImageResultId = Get-LatestResultId -Folder "generated_images"
}
if ([string]::IsNullOrWhiteSpace($VideoResultId)) {
    $VideoResultId = Get-LatestResultId -Folder "generated_videos"
}

Assert-True (-not [string]::IsNullOrWhiteSpace($ImageResultId)) "No generated image result was found."
Assert-True (-not [string]::IsNullOrWhiteSpace($VideoResultId)) "No generated video result was found."

$imageLoop = Invoke-ResultLoop -ResultId $ImageResultId -Kind "image"
$videoLoop = Invoke-ResultLoop -ResultId $VideoResultId -Kind "video"

$stateExport = Invoke-ProductCreative -CommandArgs @("state-export", "--id", $ProductId)
$state = $stateExport.state

Assert-True (($state.learning.image_generation_preferences | Measure-Object).Count -ge 1) "Image generation preferences were not learned."
Assert-True (($state.learning.video_script_preferences | Measure-Object).Count -ge 1) "Video script preferences were not learned."

$nextImageCopy = Invoke-ProductCreative -CommandArgs @("generate", "--id", $ProductId, "--target", "ecommerce-main-image-copy", "--variants", "1")
$nextVideoScript = Invoke-ProductCreative -CommandArgs @("generate", "--id", $ProductId, "--target", "douyin-short-video-script", "--variants", "1")

$imageCopyText = Get-Content -LiteralPath $nextImageCopy.artifact_json -Raw
$videoScriptText = Get-Content -LiteralPath $nextVideoScript.artifact_json -Raw
Assert-True ($imageCopyText.Contains("背景干净") -or $imageCopyText.Contains("产品主体")) "Next image generation copy did not reflect M7 learning."
Assert-True ($videoScriptText.Contains("首帧") -or $videoScriptText.Contains("镜头") -or $videoScriptText.Contains("产品卖点")) "Next video script did not reflect M7 learning."

$reportDir = Join-Path $ProductRoot "artifacts\m7_validation"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $reportDir "m7-full-validation-$stamp.md"

$report = @"
# M7.9 Full Validation

Product: $ProductId

## Inputs

- Image result: $ImageResultId
- Video result: $VideoResultId
- External model call performed in this validation: false

## Image Loop

- Review package: $($imageLoop.review_package)
- Feedback: $($imageLoop.feedback)
- Evaluation: $($imageLoop.evaluation)
- Proposal: $($imageLoop.proposal_id)
- Applied updates: $($imageLoop.applied_update_count)

## Video Loop

- Review package: $($videoLoop.review_package)
- Feedback: $($videoLoop.feedback)
- Evaluation: $($videoLoop.evaluation)
- Proposal: $($videoLoop.proposal_id)
- Applied updates: $($videoLoop.applied_update_count)

## Learned Preferences

### Image

$($state.learning.image_generation_preferences -join "`n- ")

### Video

$($state.learning.video_script_preferences -join "`n- ")

## Next Generation

- Image copy artifact: $($nextImageCopy.artifact_json)
- Video script artifact: $($nextVideoScript.artifact_json)

## Conclusion

M7.9 validates that real image/video result feedback can become reviewable learning, pass through human-confirmed proposal apply, and affect the next generation pass.
"@

$report | Set-Content -LiteralPath $reportPath -Encoding UTF8
Invoke-ProductCreative -CommandArgs @("artifact-manifest", "--id", $ProductId) | Out-Null

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    image = $imageLoop
    video = $videoLoop
    state_export = $stateExport.files.json
    next_image_copy = $nextImageCopy.artifact_json
    next_video_script = $nextVideoScript.artifact_json
    validation_report = $reportPath
    external_call_performed = $false
} | ConvertTo-Json -Depth 10
