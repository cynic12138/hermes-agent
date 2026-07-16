[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Get-PowerShellExe {
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) {
        return $pwsh.Source
    }
    return (Get-Command powershell -ErrorAction Stop).Source
}

function Invoke-JsonScript {
    param(
        [string]$ScriptPath,
        [string[]]$InputArgs = @()
    )

    $ps = Get-PowerShellExe
    $output = & $ps -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @InputArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Script failed ($LASTEXITCODE): $ScriptPath $($InputArgs -join ' ')`n$($output | Out-String)"
    }
    return (($output | Out-String).Trim() | ConvertFrom-Json)
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$previousDisableLlm = $env:PRODUCT_CREATIVE_DISABLE_LLM
$env:PRODUCT_CREATIVE_DISABLE_LLM = "1"
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-video-provider-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-video-provider-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "周十五蜂蜜露")
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "周十五蜂蜜露，清爽果蜜饮品，适合夏日饮用、办公室补水和短视频种草。主图希望清爽自然，突出真实饮用场景。"
    )
    $asset = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "asset-register",
        "--id",
        $productId,
        "--path",
        $tempImage,
        "--role",
        "current_main_image",
        "--description",
        "用户上传的当前产品主图",
        "--usage",
        "video_first_frame"
    )
    $analysis = Invoke-JsonScript -ScriptPath $runner -InputArgs @("image-analyze", "--id", $productId, "--asset", $asset.material_id)
    $alignment = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "visual-align",
        "--id",
        $productId,
        "--analysis",
        $analysis.analysis_id,
        "--note",
        "这张主图后续优先作为图生视频首帧参考。"
    )
    $intent = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-intent",
        "--id",
        $productId,
        "--message",
        "用这张主图帮我做一个抖音短视频",
        "--asset",
        $asset.material_id,
        "--theme",
        "夏日清爽开瓶"
    )
    $brief = Invoke-JsonScript -ScriptPath $runner -InputArgs @("video-brief", "--id", $productId, "--intent", $intent.intent_id)

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBeforeProvider = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $payload = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "video-generate",
        "--id",
        $productId,
        "--brief",
        $brief.brief_id,
        "--provider",
        "volcengine-ark-video"
    )
    $validation = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "provider-validate",
        "--id",
        $productId,
        "--payload",
        $payload.payload_id,
        "--provider",
        "volcengine-ark-video"
    )
    $job = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "generation-job",
        "--id",
        $productId,
        "--payload",
        $payload.payload_id,
        "--provider",
        "volcengine-ark-video",
        "--mode",
        "mock"
    )

    $stateHashAfterProvider = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)

    $draft = $payload.payload.request.provider_request_draft
    $body = $draft.body
    $content = @($body.content)
    $unresolved = @($draft.unresolved_reference_assets)
    $warnings = @($validation.warnings)
    $jobUnresolved = @($job.job.provider_request.unresolved_reference_assets)
    $payloadInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $payload.payload_id -and $_.artifact_type -eq "provider_payload" }).Count -eq 1
    $jobInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $job.job_id -and $_.artifact_type -eq "generation_job" }).Count -eq 1
    $resultInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $job.job.result_id -and $_.artifact_type -eq "generation_result" }).Count -eq 1

    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $asset.success -and
        $analysis.success -and
        $alignment.success -and
        $intent.success -and
        $brief.success -and
        $payload.success -and
        ($payload.provider -eq "volcengine-ark-video") -and
        ($payload.external_call_performed -eq $false) -and
        ($payload.payload.request.prompt_adapter.schema_version -eq "product_creative.video_prompt_adapter.v2.20") -and
        ($draft.schema_version -eq "product_creative.ark_video_task_payload.v2.20") -and
        ($draft.api_family -eq "volcengine_ark_contents_generations_tasks") -and
        ($draft.method -eq "POST") -and
        ($draft.endpoint -eq "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks") -and
        ($body.model -eq "doubao-seedance-2-0-mini-260615") -and
        ($body.ratio -eq "9:16") -and
        ($body.duration -eq 10) -and
        ($body.watermark -eq $false) -and
        ($body.generate_audio -eq $true) -and
        ($content.Count -ge 2) -and
        ($content[0].type -eq "text") -and
        ($content[1].type -eq "image_url") -and
        ($content[1].role -eq "reference_image") -and
        ($draft.body_ready_for_live -eq $true) -and
        ($unresolved.Count -eq 0) -and
        ($draft.material_execution_inputs[0].asset_id -eq $asset.material_id) -and
        ($draft.material_execution_inputs[0].input_kind -eq "data_url") -and
        $validation.success -and
        ($validation.status -eq "valid") -and
        ($warnings.Count -eq 0) -and
        $job.success -and
        ($job.mode -eq "mock") -and
        ($job.provider -eq "volcengine-ark-video") -and
        ($job.external_call_performed -eq $false) -and
        ($job.job.provider_request.provider_body_draft.model -eq "doubao-seedance-2-0-mini-260615") -and
        ($job.job.provider_request.body_ready_for_live -eq $true) -and
        ($jobUnresolved.Count -eq 0) -and
        ($stateHashBeforeProvider -eq $stateHashAfterProvider) -and
        $payloadInManifest -and
        $jobInManifest -and
        $resultInManifest
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        brief_id = $brief.brief_id
        payload_id = $payload.payload_id
        provider = $payload.provider
        adapter_schema = $payload.payload.request.prompt_adapter.schema_version
        ark_body_model = $body.model
        ark_body_ready_for_live = $draft.body_ready_for_live
        unresolved_reference_count = $unresolved.Count
        validation_status = $validation.status
        validation_warning_count = $warnings.Count
        job_id = $job.job_id
        result_id = $job.job.result_id
        state_unchanged = ($stateHashBeforeProvider -eq $stateHashAfterProvider)
        payload_in_manifest = $payloadInManifest
        job_in_manifest = $jobInManifest
        result_in_manifest = $resultInManifest
    } | ConvertTo-Json -Depth 8

    if (-not $passed) {
        exit 1
    }
}
finally {
    Remove-Item -LiteralPath $tempImage -Force -ErrorAction SilentlyContinue
    if ($null -eq $previousDisableLlm) {
        Remove-Item Env:\PRODUCT_CREATIVE_DISABLE_LLM -ErrorAction SilentlyContinue
    }
    else {
        $env:PRODUCT_CREATIVE_DISABLE_LLM = $previousDisableLlm
    }
}
