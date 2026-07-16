param(
    [string]$ProductId = "m6-material-inspiration-test"
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

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

Invoke-ProductCreative -CommandArgs @("create", "--id", $ProductId, "--name", "M6 Honey Dew Test") | Out-Null
Invoke-ProductCreative -CommandArgs @(
    "ingest",
    "--id", $ProductId,
    "--text", "A bottled honey dew beverage for ecommerce copy, image prompt, and short video planning tests. It should feel fresh, gentle, and giftable."
) | Out-Null

$assetDir = Join-Path $ProductRoot "tmp"
New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
$assetPath = Join-Path $assetDir "m6-tiny-main-image.png"
$pngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
[System.IO.File]::WriteAllBytes($assetPath, [Convert]::FromBase64String($pngBase64))

$asset = Invoke-ProductCreative -CommandArgs @(
    "asset-register",
    "--id", $ProductId,
    "--path", $assetPath,
    "--role", "current_main_image",
    "--description", "Tiny local image used for M6 MaterialResolver verification.",
    "--usage", "product_reference",
    "--usage", "video_first_frame"
)
Assert-True ($asset.success -eq $true) "Material registration failed."

$resolved = Invoke-ProductCreative -CommandArgs @(
    "material-resolve",
    "--id", $ProductId,
    "--material", $asset.material_id,
    "--provider", "volcengine-ark-video",
    "--role", "reference_image",
    "--usage", "video_provider_payload"
)
Assert-True ($resolved.ready_for_provider -eq $true) "MaterialResolver did not produce provider-ready input."
Assert-True ($resolved.input_kind -eq "data_url") "Expected local image to resolve as data_url."

$snapshot = Invoke-ProductCreative -CommandArgs @(
    "external-source",
    "--id", $ProductId,
    "--provider", "manual",
    "--mode", "dry_run",
    "--query", "fresh honey beverage inspiration",
    "--text", "Hook: a fresh morning honey drink moment. Scene: chilled bottle, golden light, clean ingredient feeling. Angle: gentle daily ritual, not medical efficacy.",
    "--limit", "3"
)
Assert-True ($snapshot.success -eq $true) "External source snapshot failed."
Assert-True ($snapshot.items_count -gt 0) "External source snapshot has no items."

$candidates = Invoke-ProductCreative -CommandArgs @(
    "inspiration-candidates",
    "--id", $ProductId,
    "--snapshot", $snapshot.snapshot_id,
    "--goal", "Create ecommerce copy and image prompt inspiration.",
    "--max-candidates", "3"
)
Assert-True ($candidates.success -eq $true) "Inspiration candidate mining failed."
Assert-True ($candidates.candidate_count -gt 0) "No inspiration candidates were produced."

$pack = Invoke-ProductCreative -CommandArgs @(
    "inspiration-pack",
    "--id", $ProductId,
    "--goal", "Use as non-product-fact creative inspiration.",
    "--target", "xiaohongshu-seeding-note",
    "--limit", "3"
)
Assert-True ($pack.success -eq $true) "Inspiration pack creation failed."
Assert-True ($pack.candidate_count -gt 0) "Inspiration pack has no items."

$workflow = Invoke-ProductCreative -CommandArgs @(
    "workflow-run",
    "--id", $ProductId,
    "--message", "帮我整理灵感包用于小红书种草文案",
    "--max-steps", "3"
)
Assert-True ($workflow.success -eq $true) "M6 workflow-run failed."

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    material_id = $asset.material_id
    material_input_id = $resolved.execution_input_id
    material_input_kind = $resolved.input_kind
    source_snapshot_id = $snapshot.snapshot_id
    inspiration_candidates = $candidates.candidate_count
    inspiration_pack_id = $pack.pack_id
    workflow_run_id = $workflow.workflow_run_id
    external_call_performed = $false
    note = "M6 offline MaterialResolver and inspiration loop verified without platform sidecar calls."
} | ConvertTo-Json -Depth 8
