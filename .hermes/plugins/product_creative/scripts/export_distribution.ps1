[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [string]$ExpectedVersion = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path
$pluginRoot = Join-Path $repoRoot ".hermes\plugins\product_creative"
$output = [IO.Path]::GetFullPath($OutputDirectory)

function Test-SameOrChild([string]$Candidate, [string]$Parent) {
    $candidatePath = [IO.Path]::GetFullPath($Candidate).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $parentPath = [IO.Path]::GetFullPath($Parent).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    return $candidatePath.Equals($parentPath, [StringComparison]::OrdinalIgnoreCase) -or
        $candidatePath.StartsWith($parentPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
}

$outputTrimmed = $output.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
$volumeRoot = [IO.Path]::GetPathRoot($output).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
if ($outputTrimmed.Equals($volumeRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to export to a volume root"
}
if ((Test-SameOrChild $output $repoRoot) -or (Test-SameOrChild $repoRoot $output)) {
    throw "OutputDirectory must be outside the source repository and must not be its ancestor"
}

python (Join-Path $pluginRoot "scripts\build_desktop_bundle.py") | Out-Null
$pluginManifestText = Get-Content -LiteralPath (Join-Path $pluginRoot "plugin.yaml") -Raw
$dashboardManifest = Get-Content -LiteralPath (Join-Path $pluginRoot "dashboard\manifest.json") -Raw | ConvertFrom-Json
$versionMatch = [regex]::Match($pluginManifestText, '(?m)^version:\s*([^\s]+)\s*$')
if (-not $versionMatch.Success) { throw "plugin.yaml has no version" }
$version = $versionMatch.Groups[1].Value
if ($dashboardManifest.version -ne $version) { throw "Plugin and dashboard versions differ" }
if ($ExpectedVersion -and $ExpectedVersion -ne $version) { throw "Release version $ExpectedVersion does not match plugin version $version" }

if (Test-Path -LiteralPath $output) { Remove-Item -LiteralPath $output -Recurse -Force }
New-Item -ItemType Directory -Path $output | Out-Null

# A release candidate must reflect the reviewed worktree, including newly added
# first-party source files that have not been committed yet. Ignored runtime
# data and generated files remain excluded by Git and the filters below.
$sourceFiles = @(
    git -C $repoRoot ls-files --cached --others --exclude-standard -- ".hermes/plugins/product_creative"
) | Sort-Object -Unique
foreach ($entry in $sourceFiles) {
    $relative = $entry.Substring(".hermes/plugins/product_creative/".Length)
    if (
        $relative -match '(^|/)(__pycache__|\.pytest_cache|runtime_data)(/|$)' -or
        $relative -match '\.(pyc|sqlite|sqlite3|db|wal|shm)$' -or
        $relative -match '^docs/' -or
        $relative -match '^dashboard/dist/' -or
        $relative -match '^scripts/verify_.*\.ps1$' -or
        $relative -in @(
            'scripts/build_desktop_bundle.py',
            'scripts/export_distribution.ps1',
            'scripts/validate_distribution.py',
            'scripts/verify_distribution_install.py'
        )
    ) { continue }
    $source = Join-Path $repoRoot ($entry -replace '/', '\')
    $target = Join-Path $output ($relative -replace '/', '\')
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $target
}

$desktopDist = Join-Path $output "dashboard\dist"
New-Item -ItemType Directory -Path $desktopDist -Force | Out-Null
$desktopBundle = Join-Path $pluginRoot "dashboard\dist\desktop.js"
$backendBundle = Join-Path $pluginRoot "dashboard\dist\backend-only.js"
Copy-Item -LiteralPath $desktopBundle -Destination (Join-Path $desktopDist "desktop.js")
Copy-Item -LiteralPath $backendBundle -Destination (Join-Path $desktopDist "backend-only.js")
$desktopTarget = Join-Path $desktopDist "desktop.js"

Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination (Join-Path $output "LICENSE")
$sourceCommit = (git -C $repoRoot rev-parse HEAD).Trim()
$bundleHash = (Get-FileHash -LiteralPath $desktopTarget -Algorithm SHA256).Hash.ToLower()
$relativePaths = [string[]]@(Get-ChildItem -LiteralPath $output -Recurse -File | ForEach-Object {
    $_.FullName.Substring($output.Length).TrimStart('\', '/') -replace '\\', '/'
})
[Array]::Sort($relativePaths, [StringComparer]::Ordinal)
$payloadRows = @($relativePaths | ForEach-Object {
    $fullPath = Join-Path $output ($_ -replace '/', '\')
    "{0} {1}" -f ((Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLower()), $_
})
$buildInput = $payloadRows -join "`n"
$sha256 = [Security.Cryptography.SHA256]::Create()
try {
    $payloadHash = ([BitConverter]::ToString($sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($buildInput))) -replace '-', '').ToLower()
} finally {
    $sha256.Dispose()
}
$sourceMetadata = @{
    source_repository = "cynic12138/hermes-agent"
    source_commit = $sourceCommit
    plugin_version = $version
    desktop_sdk_version = 1
    desktop_bundle_sha256 = $bundleHash
    payload_sha256 = $payloadHash
    generated_at = [DateTime]::UtcNow.ToString("o")
} | ConvertTo-Json
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $output "SOURCE.json"), $sourceMetadata + "`n", $utf8)

python (Join-Path $pluginRoot "scripts\validate_distribution.py") $output --expected-version $version --expected-commit $sourceCommit
if ($LASTEXITCODE -ne 0) { throw "Distribution validation failed" }

Write-Output $output
