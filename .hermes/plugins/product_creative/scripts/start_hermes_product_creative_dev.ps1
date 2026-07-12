param(
    [string]$Query = "",
    [int]$MaxTurns = 8,
    [switch]$Quiet,
    [switch]$Yolo,
    [switch]$NoTemporaryEnable,
    [switch]$PrintCommand
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
}

function Get-DefaultHermesHome {
    if ($env:HERMES_HOME) {
        return $env:HERMES_HOME
    }
    if ($env:LOCALAPPDATA) {
        return (Join-Path $env:LOCALAPPDATA "hermes")
    }
    return (Join-Path $HOME ".hermes")
}

function Get-HermesPython {
    param([string]$HermesHome)

    $candidates = @(
        (Join-Path $HermesHome "hermes-agent\venv\Scripts\python.exe"),
        (Join-Path $HermesHome "hermes-agent\venv\bin\python")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    throw "Could not find Python. Expected Hermes venv under '$HermesHome\hermes-agent\venv'."
}

function Enter-ConfigLock {
    param([string]$HermesHome)

    $lockPath = Join-Path $HermesHome ".product_creative_runtime_probe.lock"
    $deadline = (Get-Date).AddSeconds(30)
    while ($true) {
        try {
            return [System.IO.File]::Open(
                $lockPath,
                [System.IO.FileMode]::OpenOrCreate,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
        }
        catch {
            if ((Get-Date) -gt $deadline) {
                throw "Timed out waiting for Hermes config lock: $lockPath"
            }
            Start-Sleep -Milliseconds 200
        }
    }
}

function Enable-ProductCreativePlugin {
    param([string]$Python)

    $script = @'
from hermes_cli.config import load_config, save_config

cfg = load_config() or {}
plugins = cfg.setdefault("plugins", {})
if not isinstance(plugins, dict):
    plugins = {}
    cfg["plugins"] = plugins

enabled = plugins.setdefault("enabled", [])
if not isinstance(enabled, list):
    enabled = []
    plugins["enabled"] = enabled
if "product_creative" not in enabled:
    enabled.append("product_creative")

entries = plugins.setdefault("entries", {})
if not isinstance(entries, dict):
    entries = {}
    plugins["entries"] = entries
entry = entries.setdefault("product_creative", {})
if not isinstance(entry, dict):
    entry = {}
    entries["product_creative"] = entry
entry["allow_tool_override"] = False

save_config(cfg)
'@

    $script | & $Python -
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to enable product_creative for this dev chat session."
    }
}

function Format-CommandPreview {
    param(
        [string]$Python,
        [string[]]$CommandArgs
    )

    $parts = @("& `"$Python`"")
    foreach ($item in $CommandArgs) {
        if ($item -match "\s") {
            $parts += "`"$item`""
        }
        else {
            $parts += $item
        }
    }
    return ($parts -join " ")
}

$repoRoot = Get-RepoRoot
$hermesHome = Get-DefaultHermesHome
$configPath = Join-Path $hermesHome "config.yaml"
$python = Get-HermesPython -HermesHome $hermesHome

$chatArgs = @(
    "-m", "hermes_cli.main",
    "chat",
    "--cli",
    "--toolsets", "product_creative,skills",
    "--skills", "product_creative:product-creative-operator",
    "--max-turns", ([string]$MaxTurns),
    "--accept-hooks"
)
if ($Quiet -or $Query) {
    $chatArgs += "--quiet"
}
if ($Yolo) {
    $chatArgs += "--yolo"
}
if ($Query) {
    $chatArgs += @("--query", $Query)
}

if ($PrintCommand) {
    [ordered]@{
        repo_root = $repoRoot
        hermes_home = $hermesHome
        config_path = $configPath
        temporary_enable = -not [bool]$NoTemporaryEnable
        command = (Format-CommandPreview -Python $python -CommandArgs $chatArgs)
    } | ConvertTo-Json -Depth 4
    exit 0
}

$previousProjectPlugins = $env:HERMES_ENABLE_PROJECT_PLUGINS
$previousEncoding = $env:PYTHONIOENCODING
$hadConfig = Test-Path -LiteralPath $configPath
$backup = $null
$configLock = $null
$pushed = $false
$exitCode = 0

try {
    $env:HERMES_ENABLE_PROJECT_PLUGINS = "1"
    $env:PYTHONIOENCODING = "utf-8"

    if (-not $NoTemporaryEnable) {
        $configLock = Enter-ConfigLock -HermesHome $hermesHome
        $backup = New-TemporaryFile
        if ($hadConfig) {
            Copy-Item -LiteralPath $configPath -Destination $backup.FullName -Force
        }
        Enable-ProductCreativePlugin -Python $python
    }

    Push-Location $repoRoot
    $pushed = $true
    & $python @chatArgs
    $exitCode = $LASTEXITCODE
}
finally {
    if ($pushed) {
        Pop-Location
    }

    if (-not $NoTemporaryEnable) {
        if ($hadConfig -and $backup -and (Test-Path -LiteralPath $backup.FullName)) {
            Copy-Item -LiteralPath $backup.FullName -Destination $configPath -Force
        }
        elseif (-not $hadConfig -and (Test-Path -LiteralPath $configPath)) {
            Remove-Item -LiteralPath $configPath -Force
        }
        if ($backup) {
            Remove-Item -LiteralPath $backup.FullName -Force -ErrorAction SilentlyContinue
        }
        if ($configLock) {
            $configLock.Dispose()
        }
    }

    if ($null -eq $previousProjectPlugins) {
        Remove-Item Env:\HERMES_ENABLE_PROJECT_PLUGINS -ErrorAction SilentlyContinue
    }
    else {
        $env:HERMES_ENABLE_PROJECT_PLUGINS = $previousProjectPlugins
    }

    if ($null -eq $previousEncoding) {
        Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONIOENCODING = $previousEncoding
    }
}

exit $exitCode
