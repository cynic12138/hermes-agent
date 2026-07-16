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
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m2-align-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m2-align-$stamp"
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
        "video_first_frame"
    )
    $analysis = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-analyze",
        "--id",
        $productId,
        "--asset",
        $asset.material_id
    )

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateHashBeforeAlign = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $alignment = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "visual-align",
        "--id",
        $productId,
        "--analysis",
        $analysis.analysis_id,
        "--note",
        "这张图后续优先作为图生视频首帧参考。"
    )
    $stateHashAfterAlign = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash

    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId)
    $stateHashBeforeApply = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
    $apply = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId, "--apply", $proposal.proposal_id)
    $state = Read-JsonFile -Path $statePath

    $alignmentInManifest = @($manifest.manifest.artifacts | Where-Object { $_.artifact_id -eq $alignment.alignment_id }).Count -eq 1
    $proposalPaths = @($proposal.proposal.target_state_paths)
    $visualPreference = @($state.learning.image_generation_preferences | Where-Object { $_ -like "*$($asset.material_id)*" }).Count -ge 1

    $passed = [bool](
        $create.success -and
        $asset.success -and
        $analysis.success -and
        $alignment.success -and
        ($alignment.alignment.schema_version -eq "product_creative.visual_alignment.v2.16") -and
        ($alignment.eligible_for_evolution_proposal -eq $true) -and
        ($alignment.alignment.brain_write_policy.direct_write_to_product_brain -eq $false) -and
        ($stateHashBeforeAlign -eq $stateHashAfterAlign) -and
        $alignmentInManifest -and
        $proposal.success -and
        ($proposal.proposal.source_alignment_id -eq $alignment.alignment_id) -and
        ($proposalPaths -contains "learning.image_generation_preferences") -and
        ($proposal.proposal.status -eq "proposed") -and
        ($stateHashBeforeApply -eq $stateHashAfterAlign) -and
        $apply.success -and
        ($apply.applied_updates.Count -ge 1) -and
        $visualPreference
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        product_id = $productId
        material_id = $asset.material_id
        analysis_id = $analysis.analysis_id
        alignment_id = $alignment.alignment_id
        alignment_eligible = $alignment.eligible_for_evolution_proposal
        visual_align_state_unchanged = ($stateHashBeforeAlign -eq $stateHashAfterAlign)
        visual_alignment_in_manifest = $alignmentInManifest
        proposal_id = $proposal.proposal_id
        proposal_source_alignment_id = $proposal.proposal.source_alignment_id
        proposal_paths = $proposalPaths
        applied_update_count = $apply.applied_updates.Count
        visual_preference_applied = $visualPreference
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
