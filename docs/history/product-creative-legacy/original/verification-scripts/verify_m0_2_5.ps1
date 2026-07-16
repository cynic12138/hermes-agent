[CmdletBinding()]
param(
    [string]$ProductId = "",
    [string]$Name = "新疆吊干杏",
    [string]$Text = "新疆吊干杏，自然成熟，口感清甜，有果香，适合作为办公室零食和送礼。目标风格：高级、可信、克制，不要过度促销，不要夸大功效。",
    [int]$Variants = 3,
    [switch]$AllowFallback
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
}

function Get-PowerShellExe {
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) {
        return $pwsh.Source
    }
    $powershell = Get-Command powershell -ErrorAction Stop
    return $powershell.Source
}

function Invoke-ProductCreativeJson {
    param([string[]]$InputArgs)

    $runner = Join-Path $PSScriptRoot "product_creative.ps1"
    $ps = Get-PowerShellExe
    $output = & $ps -NoProfile -ExecutionPolicy Bypass -File $runner @InputArgs
    if ($LASTEXITCODE -ne 0) {
        throw "product_creative runner failed ($LASTEXITCODE): $($InputArgs -join ' ')`n$($output | Out-String)"
    }
    $text = ($output | Out-String).Trim()
    return ($text | ConvertFrom-Json)
}

function Get-BrainHashes {
    param(
        [string]$ProductDir,
        [string[]]$Files
    )

    $hashes = @{}
    foreach ($rel in $Files) {
        $path = Join-Path $ProductDir $rel
        if (Test-Path -LiteralPath $path) {
            $hashes[$rel] = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
        }
    }
    return $hashes
}

function Compare-Hashes {
    param(
        [hashtable]$Before,
        [hashtable]$After
    )

    $changed = @()
    foreach ($key in $Before.Keys) {
        if (-not $After.ContainsKey($key) -or $Before[$key] -ne $After[$key]) {
            $changed += $key
        }
    }
    return $changed
}

if (-not $ProductId) {
    $ProductId = "m025-verify-" + (Get-Date -Format "yyyyMMdd-HHmmss")
}

if ($Variants -lt 1) {
    $Variants = 1
}
if ($Variants -gt 5) {
    $Variants = 5
}

$repoRoot = Get-RepoRoot
$productDir = Join-Path $repoRoot (".hermes\product_creative\products\" + $ProductId)
$brainFiles = @(
    "structured\product_state.json",
    "wiki\product\Product.md",
    "wiki\product\selling-points.md",
    "wiki\channels\ecommerce.md",
    "wiki\channels\douyin.md"
)

$create = Invoke-ProductCreativeJson @("create", "--id", $ProductId, "--name", $Name)
$ingest = Invoke-ProductCreativeJson @("ingest", "--id", $ProductId, "--text", $Text)
$before = Get-BrainHashes -ProductDir $productDir -Files $brainFiles
$generated = Invoke-ProductCreativeJson @("generate", "--id", $ProductId, "--target", "product-copy-pack", "--variants", ([string]$Variants))
$after = Get-BrainHashes -ProductDir $productDir -Files $brainFiles
$changed = Compare-Hashes -Before $before -After $after

$artifact = Get-Content -LiteralPath $generated.artifact_json -Raw -Encoding UTF8 | ConvertFrom-Json
$variantCount = @($artifact.variants).Count
$generationMethod = [string]$artifact.generation_method
$groundingStatus = [string]$artifact.grounding_audit.status
$groundingWarningCount = [int]$artifact.grounding_audit.warning_count
$llmProvider = [string]$artifact.llm.provider
$llmModel = [string]$artifact.llm.model

$methodOk = $generationMethod -eq "llm"
if ($AllowFallback -or $env:PRODUCT_CREATIVE_ENABLE_LLM -ne "1") {
    $methodOk = $generationMethod -in @("llm", "rule-fallback")
}
$groundingOk = $groundingStatus -eq "passed_lite_audit" -and $groundingWarningCount -eq 0
$brainOk = @($changed).Count -eq 0
$variantOk = $variantCount -eq $Variants
$passed = [bool]($create.success -and $ingest.success -and $generated.success -and $methodOk -and $groundingOk -and $brainOk -and $variantOk)

$summary = [pscustomobject]@{
    success = $passed
    product_id = $ProductId
    artifact_json = $generated.artifact_json
    artifact_markdown = $generated.artifact_markdown
    generation_method = $generationMethod
    fallback_reason = [string]$artifact.fallback_reason
    llm_provider = $llmProvider
    llm_model = $llmModel
    grounding_status = $groundingStatus
    grounding_warning_count = $groundingWarningCount
    variant_count = $variantCount
    product_brain_changed_by_generate = @($changed)
    checks = [pscustomobject]@{
        create_success = [bool]$create.success
        ingest_success = [bool]$ingest.success
        generate_success = [bool]$generated.success
        method_ok = $methodOk
        grounding_ok = $groundingOk
        product_brain_ok = $brainOk
        variant_count_ok = $variantOk
    }
}

$summary | ConvertTo-Json -Depth 6

if (-not $passed) {
    exit 1
}
