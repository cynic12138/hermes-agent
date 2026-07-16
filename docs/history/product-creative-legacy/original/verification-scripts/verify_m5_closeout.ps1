param(
    [string]$ProductId = "m2-video-provider-20260707-144240",
    [string]$VideoTaskId = "video-task-20260708-122312",
    [string]$StatusId = "video-task-status-20260708-123341",
    [string]$ResultId = "video-result-20260708-123335"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot "..\..\..\..")).Path
$ProductRoot = Join-Path $RepoRoot ".hermes\product_creative\products\$ProductId"

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

$taskPath = Join-Path $ProductRoot "artifacts\video_tasks\$VideoTaskId.json"
$statusPath = Join-Path $ProductRoot "artifacts\video_task_status\$StatusId.json"
$resultPath = Join-Path $ProductRoot "artifacts\generated_videos\$ResultId.json"
$videoPath = Join-Path $ProductRoot "artifacts\generated_videos\$ResultId.mp4"
$indexPath = Join-Path $ProductRoot "structured\generated_video_index.jsonl"
$m5DocPath = Join-Path $RepoRoot ".hermes\plugins\product_creative\docs\M5_VIDEO_GENERATION_EXECUTION_ARCHITECTURE.md"
$roadmapPath = Join-Path $RepoRoot ".hermes\plugins\product_creative\docs\PRODUCT_MAINLINE_ROADMAP.md"

$task = Read-JsonFile -Path $taskPath
$status = Read-JsonFile -Path $statusPath
$result = Read-JsonFile -Path $resultPath

Assert-True ($task.video_task_id -eq $VideoTaskId) "Video task id mismatch."
Assert-True ($status.video_task_id -eq $VideoTaskId) "Status does not belong to task."
Assert-True ($result.video_task_id -eq $VideoTaskId) "Result does not belong to task."
Assert-True ($task.remote_task_id -eq $status.remote_task_id -and $task.remote_task_id -eq $result.remote_task_id) "Remote task ids are inconsistent."
Assert-True ($status.normalized_status -eq "completed") "Final status is not completed."
Assert-True ($status.provider_task_status -eq "succeeded") "Provider status is not succeeded."
Assert-True ($result.status -eq "completed") "Generated video result is not completed."
Assert-True (-not [string]::IsNullOrWhiteSpace($result.remote_url)) "Generated video result is missing remote_url."
Assert-True (Test-Path -LiteralPath $videoPath) "Local video file is missing."

$relativePath = "artifacts\generated_videos\$ResultId.mp4"
$output = $result.outputs | Select-Object -First 1
Assert-True ($output.path -eq $relativePath) "Generated video result does not point to the local mp4."
Assert-True ([int64]$output.bytes -eq (Get-Item -LiteralPath $videoPath).Length) "Generated video byte count is inconsistent."
Assert-True ([string]::IsNullOrWhiteSpace($result.download_error)) "Generated video result still contains a download_error."

$indexEntry = Get-Content -LiteralPath $indexPath |
    Where-Object { $_ -match [regex]::Escape($ResultId) } |
    Select-Object -Last 1 |
    ConvertFrom-Json
Assert-True ($null -ne $indexEntry) "Generated video index is missing result id."
Assert-True ($indexEntry.path -eq $relativePath) "Generated video index is missing local path."

$m5Doc = Get-Content -LiteralPath $m5DocPath -Raw
$roadmap = Get-Content -LiteralPath $roadmapPath -Raw
Assert-True ($m5Doc.Contains("final_status_check: $StatusId")) "M5 architecture doc is missing final status check."
Assert-True ($m5Doc.Contains("live_result: $ResultId")) "M5 architecture doc is missing live result id."
Assert-True ($roadmap.Contains("result_id: $ResultId")) "Mainline roadmap is missing final result id."

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    video_task_id = $VideoTaskId
    remote_task_id = $task.remote_task_id
    status_id = $StatusId
    normalized_status = $status.normalized_status
    provider_status = $status.provider_task_status
    result_id = $ResultId
    local_video = $relativePath
    local_video_bytes = (Get-Item -LiteralPath $videoPath).Length
    external_call_performed = $false
    note = "M5 closeout check only; no provider call was performed."
} | ConvertTo-Json -Depth 5
