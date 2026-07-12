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

function Read-JsonFile {
    param([string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$previousDisableLlm = $env:PRODUCT_CREATIVE_DISABLE_LLM
$env:PRODUCT_CREATIVE_DISABLE_LLM = "1"
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-visual-$stamp"
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
    $list = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "asset-list",
        "--id",
        $productId,
        "--role",
        "current_main_image"
    )
    $library = Invoke-JsonScript -ScriptPath $runner -InputArgs @("material-manifest", "--id", $productId)

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateBeforeAnalyze = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $analysis = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-analyze",
        "--id",
        $productId,
        "--asset",
        $asset.material_id
    )
    $stateAfterAnalyze = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $state = Read-JsonFile -Path $statePath
    $sourceIndexPath = Join-Path $base "structured\source_index.jsonl"
    $sourceIndex = Get-Content -LiteralPath $sourceIndexPath -Raw -Encoding UTF8

    $storedPath = Join-Path $base $asset.asset.stored_path
    $materialInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $asset.material_id }).Count -eq 1
    $analysisInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $analysis.analysis_id }).Count -eq 1

    $passed = [bool](
        $create.success -and
        $asset.success -and
        ($asset.asset.schema_version -eq "product_creative.material_asset.v2.14") -and
        ($asset.asset.role -eq "current_main_image") -and
        ($asset.asset.media.width -eq 1) -and
        ($asset.asset.media.height -eq 1) -and
        (Test-Path -LiteralPath $storedPath) -and
        ($list.asset_count -eq 1) -and
        ($library.asset_count -eq 1) -and
        ($state.assets.current_main_image_id -eq $asset.material_id) -and
        (@($state.assets.materials).Count -eq 1) -and
        ($sourceIndex -like "*material_asset*") -and
        $analysis.success -and
        ($analysis.analysis.schema_version -eq "product_creative.image_analysis.v2.15") -and
        ($analysis.analysis.provider -eq "mock-vision") -and
        ($analysis.analysis.external_call_performed -eq $false) -and
        ($analysis.analysis.brain_write_policy.direct_write_to_product_brain -eq $false) -and
        (@($analysis.analysis.quality_flags) -contains "dimensions_readable") -and
        ($stateBeforeAnalyze -eq $stateAfterAnalyze) -and
        $materialInManifest -and
        $analysisInManifest
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        material_id = $asset.material_id
        material_role = $asset.asset.role
        material_dimensions = "$($asset.asset.media.width)x$($asset.asset.media.height)"
        asset_count = $library.asset_count
        analysis_id = $analysis.analysis_id
        analysis_provider = $analysis.analysis.provider
        analysis_external_call = $analysis.analysis.external_call_performed
        state_unchanged_by_analysis = ($stateBeforeAnalyze -eq $stateAfterAnalyze)
        material_in_artifact_manifest = $materialInManifest
        analysis_in_artifact_manifest = $analysisInManifest
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
