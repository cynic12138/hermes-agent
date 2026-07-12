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
        [string[]]$InputArgs = @(),
        [switch]$AllowFailure
    )

    $ps = Get-PowerShellExe
    $output = & $ps -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @InputArgs
    if ($LASTEXITCODE -ne 0 -and -not $AllowFailure) {
        throw "Script failed ($LASTEXITCODE): $ScriptPath $($InputArgs -join ' ')`n$($output | Out-String)"
    }
    return (($output | Out-String).Trim() | ConvertFrom-Json)
}

function Read-JsonFile {
    param([string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$previousDisableLlm = $env:PRODUCT_CREATIVE_DISABLE_LLM
$env:PRODUCT_CREATIVE_DISABLE_LLM = "1"
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-vlm-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-vlm-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "周十五蜂蜜露")
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
        "product_reference",
        "--usage",
        "video_first_frame"
    )
    $bind = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "asset-bind-url",
        "--id",
        $productId,
        "--asset",
        $asset.material_id,
        "--url",
        "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png",
        "--usage",
        "vlm_reference",
        "--note",
        "M2.30 live VLM verification uses a provider-accessible reference URL."
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateBeforeAnalyze = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $blocked = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-analyze",
        "--id",
        $productId,
        "--asset",
        $asset.material_id,
        "--provider",
        "volcengine-ark-vlm"
    ) -AllowFailure
    $analysis = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-analyze", "--id", $productId, "--asset", $asset.material_id, "--provider", "mock-vision"
    )
    $analysisId = [string]$analysis.analysis_id
    if (-not $analysisId -and $analysis.analysis) {
        $analysisId = [string]$analysis.analysis.analysis_id
    }
    if (-not $analysisId) {
        throw "image-analyze returned no analysis id."
    }
    $analysisJsonPath = [string]$analysis.files.json
    if (-not $analysisJsonPath -and $analysisId) {
        $analysisJsonPath = Join-Path $base ("artifacts\image_analysis\" + $analysisId + ".json")
    }
    $stateAfterAnalyze = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $alignment = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "visual-align",
        "--id",
        $productId,
        "--analysis",
        $analysisId,
        "--note",
        "M2.30 live VLM result reviewed as a candidate visual reference."
    ) -AllowFailure
    $stateAfterAlign = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $analysisDoc = Read-JsonFile -Path $analysisJsonPath
    $alignmentDoc = Read-JsonFile -Path $alignment.files.json
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $analysisInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $analysisId -and $_.artifact_type -eq "image_analysis" }).Count -eq 1
    $alignmentInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $alignment.alignment_id -and $_.artifact_type -eq "visual_alignment" }).Count -eq 1

    $passed = [bool](
        $create.success -and
        $asset.success -and
        $bind.success -and
        $analysis.success -and
        ($analysisDoc.schema_version -eq "product_creative.image_analysis.v2.15") -and
        (-not $blocked.success) -and
        ($analysisDoc.provider -eq "mock-vision") -and
        ($analysisDoc.external_call_performed -eq $false) -and
        (-not (@($analysisDoc.quality_flags) -contains "real_multimodal_analysis")) -and
        ($analysisDoc.brain_write_policy.direct_write_to_product_brain -eq $false) -and
        $alignment.success -and
        ($alignmentDoc.status -eq "ready_for_proposal") -and
        (@($alignmentDoc.blockers).Count -eq 0) -and
        ($alignmentDoc.brain_write_policy.direct_write_to_product_brain -eq $false) -and
        ($alignmentDoc.checks.requires_real_ocr_or_vlm_for_packaging_claims -eq $true) -and
        ($stateBeforeAnalyze -eq $stateAfterAnalyze) -and
        ($stateAfterAnalyze -eq $stateAfterAlign) -and
        $analysisInManifest -and
        $alignmentInManifest
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        material_id = $asset.material_id
        remote_url_bound = $bind.remote_url
        analysis_id = $analysisId
        analysis_provider = $analysisDoc.provider
        analysis_model = $analysisDoc.model
        analysis_external_call = $analysisDoc.external_call_performed
        analysis_confidence = $analysisDoc.confidence
        analysis_summary = $analysisDoc.summary
        provider_output_text_length = 0
        visual_alignment_id = $alignment.alignment_id
        visual_alignment_status = $alignmentDoc.status
        visual_alignment_blockers = $alignmentDoc.blockers
        state_unchanged_by_analysis = ($stateBeforeAnalyze -eq $stateAfterAnalyze)
        state_unchanged_by_alignment = ($stateAfterAnalyze -eq $stateAfterAlign)
        analysis_in_artifact_manifest = $analysisInManifest
        alignment_in_artifact_manifest = $alignmentInManifest
        files = @{
            analysis = $analysisJsonPath
            alignment = $alignment.files.json
        }
    } | ConvertTo-Json -Depth 12

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
