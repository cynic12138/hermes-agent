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

function Read-AllWikiText {
    param([string]$ProductBase)

    $parts = @()
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $ProductBase "wiki") -Filter "*.md" -Recurse) {
        $parts += (Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8)
    }
    return ($parts -join "`n")
}

function Read-JsonFile {
    param([string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

$productA = [pscustomobject]@{
    Id = "m1-hardening-a-$stamp"
    Name = "山野冻干蓝莓"
    Text = "山野冻干蓝莓，真实果粒，酸甜清爽，适合办公室轻零食和早餐酸奶搭配。主图希望高级质感，突出真实果粒，不要太促销。"
}
$productB = [pscustomobject]@{
    Id = "m1-hardening-b-$stamp"
    Name = "暖光护眼阅读灯"
    Text = "暖光护眼阅读灯，光线柔和，适合睡前阅读和学习桌使用，强调稳定底座、低频闪和家长可信。"
}

$createA = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productA.Id, "--name", $productA.Name)
$ingestA = Invoke-JsonScript -ScriptPath $runner -InputArgs @("ingest", "--id", $productA.Id, "--text", $productA.Text)
$upgradeA = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-upgrade", "--id", $productA.Id)
$fingerprintA = Invoke-JsonScript -ScriptPath $runner -InputArgs @("fingerprint", "--id", $productA.Id)

$createB = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productB.Id, "--name", $productB.Name)
$ingestB = Invoke-JsonScript -ScriptPath $runner -InputArgs @("ingest", "--id", $productB.Id, "--text", $productB.Text)
$upgradeB = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-upgrade", "--id", $productB.Id)
$fingerprintB = Invoke-JsonScript -ScriptPath $runner -InputArgs @("fingerprint", "--id", $productB.Id)

$baseA = Join-Path $repoRoot (".hermes\product_creative\products\" + $productA.Id)
$baseB = Join-Path $repoRoot (".hermes\product_creative\products\" + $productB.Id)

$feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "feedback",
    "--id",
    $productA.Id,
    "--artifact",
    "manual-copy-pack",
    "--note",
    "更喜欢高级质感，突出真实果粒，不要太促销。",
    "--selected",
    "--variant",
    "1",
    "--rating",
    "5"
)

$proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productA.Id)
$proposalPayload = Read-JsonFile -Path $proposal.proposal_path
$apply = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
    "evolve",
    "--id",
    $productA.Id,
    "--apply",
    $proposal.proposal_id
)

$lintAfterApply = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-lint", "--id", $productA.Id)
$stateExport = Invoke-JsonScript -ScriptPath $runner -InputArgs @("state-export", "--id", $productA.Id)
$contextImage = Invoke-JsonScript -ScriptPath $runner -InputArgs @("context", "--id", $productA.Id, "--target", "image-generation")

$sourceIndexPath = Join-Path $baseA "structured\source_index.jsonl"
$sourceIndexText = if (Test-Path -LiteralPath $sourceIndexPath) {
    Get-Content -LiteralPath $sourceIndexPath -Raw -Encoding UTF8
}
else {
    ""
}

$productPageA = Join-Path $baseA "wiki\product\Product.md"
$originalProductPageA = Get-Content -LiteralPath $productPageA -Raw -Encoding UTF8
try {
    Add-Content -LiteralPath $productPageA -Value "`nM1 guard probe: $($productB.Id)`n" -Encoding UTF8
    $guardProbe = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-lint", "--id", $productA.Id)
}
finally {
    Set-Content -LiteralPath $productPageA -Value $originalProductPageA -Encoding UTF8
}
$lintAfterRestore = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-lint", "--id", $productA.Id)

$wikiTextA = Read-AllWikiText -ProductBase $baseA
$wikiTextB = Read-AllWikiText -ProductBase $baseB
$contextJson = $contextImage | ConvertTo-Json -Depth 20

$typedUpdateChecks = @($proposalPayload.updates | ForEach-Object {
    [pscustomobject]@{
        path = $_.path
        has_type = [bool]$_.update_type
        has_target_page = [bool]$_.target_page
        has_target_section = [bool]$_.target_section
        has_risk = [bool]$_.risk_level
        source_count = @($_.source_ids).Count
    }
})

$state = $stateExport.state
$provenanceSourceIds = @($state._provenance."learning.confirmed_wiki_learning".source_ids)
$proposalSourceIds = @($proposalPayload.source_ids)
$sourceId = if ($proposalSourceIds.Count -gt 0) { [string]$proposalSourceIds[0] } else { "" }

$passed = [bool](
    $createA.success -and
    $ingestA.success -and
    $upgradeA.success -and
    $fingerprintA.success -and
    $createB.success -and
    $ingestB.success -and
    $upgradeB.success -and
    $fingerprintB.success -and
    $feedback.success -and
    $proposal.success -and
    $proposalPayload.schema_version -eq "product_creative.evolution_proposal.v1" -and
    $proposalPayload.requires_human_review -and
    @($proposalPayload.preview).Count -gt 0 -and
    @($proposalPayload.target_pages).Count -gt 1 -and
    @($typedUpdateChecks | Where-Object { -not $_.has_type -or -not $_.has_target_page -or -not $_.has_target_section -or -not $_.has_risk -or $_.source_count -lt 1 }).Count -eq 0 -and
    $sourceIndexText.Contains("raw_input") -and
    $sourceIndexText.Contains("feedback") -and
    $sourceId -and
    $wikiTextA.Contains($sourceId) -and
    $apply.success -and
    $lintAfterApply.success -and
    $stateExport.success -and
    $state._export.schema_version -eq "product_creative.product_state_export.v2" -and
    $provenanceSourceIds.Count -gt 0 -and
    $contextImage.success -and
    $contextImage.context_profile -eq "image-generation" -and
    (@($contextImage.page_list) -contains "content-patterns/failed-patterns.md") -and
    (-not $contextJson.Contains($productB.Id)) -and
    (-not $wikiTextB.Contains($productA.Id)) -and
    (-not $guardProbe.success) -and
    (@($guardProbe.errors | Where-Object { $_ -like "*$($productB.Id)*" }).Count -gt 0) -and
    $lintAfterRestore.success
)

[pscustomobject]@{
    success = $passed
    live_call_count = 0
    products = @($productA.Id, $productB.Id)
    proposal_id = $proposal.proposal_id
    proposal_path = $proposal.proposal_path
    proposal_source_ids = $proposalSourceIds
    typed_update_checks = $typedUpdateChecks
    source_index = $sourceIndexPath
    state_export = $stateExport.files.json
    context_profile = $contextImage.context_profile
    context_pages = @($contextImage.page_list)
    guard_probe_success_expected_false = $guardProbe.success
    guard_probe_errors = @($guardProbe.errors)
    lint_after_restore_success = $lintAfterRestore.success
} | ConvertTo-Json -Depth 8

if (-not $passed) {
    exit 1
}
