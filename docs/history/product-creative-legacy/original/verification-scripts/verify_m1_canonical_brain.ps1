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

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

$products = @(
    [pscustomobject]@{
        Id = "m1-canonical-a-$stamp"
        Name = "新疆吊干杏"
        Text = "新疆吊干杏，自然成熟，果香浓郁，适合作为办公室零食和礼盒搭配。"
        Keywords = @("新疆", "吊干杏", "办公室零食")
    },
    [pscustomobject]@{
        Id = "m1-canonical-b-$stamp"
        Name = "冷萃咖啡豆"
        Text = "冷萃咖啡豆，低酸顺滑，适合办公室冷泡和夏季饮品，视觉偏好干净、专业、不要太促销。"
        Keywords = @("冷萃", "咖啡豆", "低酸顺滑")
    },
    [pscustomobject]@{
        Id = "m1-canonical-c-$stamp"
        Name = "儿童护眼台灯"
        Text = "儿童护眼台灯，光线柔和，适合学习桌和睡前阅读，强调安全、稳定、家长可信。"
        Keywords = @("儿童护眼台灯", "光线柔和", "学习桌")
    }
)

$results = @()
foreach ($product in $products) {
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $product.Id, "--name", $product.Name)
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("ingest", "--id", $product.Id, "--text", $product.Text)
    $upgrade = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-upgrade", "--id", $product.Id)
    $lint = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-lint", "--id", $product.Id)
    $stateExport = Invoke-JsonScript -ScriptPath $runner -InputArgs @("state-export", "--id", $product.Id)
    $context = Invoke-JsonScript -ScriptPath $runner -InputArgs @("context", "--id", $product.Id)
    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $product.Id)
    $wikiText = Read-AllWikiText -ProductBase $base
    $results += [pscustomobject]@{
        product = $product
        create = $create
        ingest = $ingest
        upgrade = $upgrade
        lint = $lint
        state_export = $stateExport
        context = $context
        base = $base
        wiki_text = $wikiText
    }
}

$requiredPages = @($results[0].upgrade.required_pages)
$structureConsistent = $true
foreach ($result in $results) {
    $pages = @($result.upgrade.required_pages)
    if (($pages -join "|") -ne ($requiredPages -join "|")) {
        $structureConsistent = $false
    }
}

$isolationErrors = @()
foreach ($result in $results) {
    foreach ($other in $products) {
        if ($other.Id -eq $result.product.Id) {
            continue
        }
        if ($result.wiki_text.Contains($other.Id)) {
            $isolationErrors += "$($result.product.Id) wiki contains other product id $($other.Id)"
        }
    }
}

$aKeywords = @($products[0].Keywords)
foreach ($result in $results | Where-Object { $_.product.Id -ne $products[0].Id }) {
    foreach ($keyword in $aKeywords) {
        if ($result.wiki_text.Contains($keyword)) {
            $isolationErrors += "$($result.product.Id) wiki contains A keyword $keyword"
        }
    }
}

$stateChecks = @()
foreach ($result in $results) {
    $state = $result.state_export.state
    $ownKeywordFound = $false
    foreach ($keyword in $result.product.Keywords) {
        if (($state.basic.brief -like "*$keyword*") -or (($state.selling_points -join "`n") -like "*$keyword*")) {
            $ownKeywordFound = $true
        }
    }
    $stateChecks += [pscustomobject]@{
        product_id = $result.product.Id
        state_product_id_ok = $state.product_id -eq $result.product.Id
        own_keyword_found = $ownKeywordFound
        export_source = $state._export.source
    }
}

$contextChecks = @()
foreach ($result in $results) {
    $contextJson = $result.context | ConvertTo-Json -Depth 20
    $hasOtherProduct = $false
    foreach ($other in $products) {
        if ($other.Id -ne $result.product.Id -and $contextJson.Contains($other.Id)) {
            $hasOtherProduct = $true
        }
    }
    $contextChecks += [pscustomobject]@{
        product_id = $result.product.Id
        page_count = @($result.context.page_list).Count
        lint_errors = $result.context.lint_summary.error_count
        has_other_product = $hasOtherProduct
    }
}

$allSuccess = [bool](
    ($results | Where-Object { -not $_.create.success }).Count -eq 0 -and
    ($results | Where-Object { -not $_.ingest.success }).Count -eq 0 -and
    ($results | Where-Object { -not $_.upgrade.success }).Count -eq 0 -and
    ($results | Where-Object { -not $_.lint.success }).Count -eq 0 -and
    ($results | Where-Object { -not $_.state_export.success }).Count -eq 0 -and
    ($results | Where-Object { -not $_.context.success }).Count -eq 0 -and
    $structureConsistent -and
    $isolationErrors.Count -eq 0 -and
    ($stateChecks | Where-Object { -not $_.state_product_id_ok -or -not $_.own_keyword_found -or $_.export_source -ne "product_wiki" }).Count -eq 0 -and
    ($contextChecks | Where-Object { $_.has_other_product -or $_.lint_errors -ne 0 -or $_.page_count -lt 8 }).Count -eq 0
)

[pscustomobject]@{
    success = $allSuccess
    live_call_count = 0
    products = @($products | ForEach-Object { $_.Id })
    required_page_count = $requiredPages.Count
    structure_consistent = $structureConsistent
    isolation_errors = $isolationErrors
    state_checks = $stateChecks
    context_checks = $contextChecks
    lint_reports = @($results | ForEach-Object { $_.lint.files.json })
    state_exports = @($results | ForEach-Object { $_.state_export.files.json })
} | ConvertTo-Json -Depth 8

if (-not $allSuccess) {
    exit 1
}
