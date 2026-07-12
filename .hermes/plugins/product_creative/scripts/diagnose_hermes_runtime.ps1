param(
    [switch]$CheckPluginLoad,
    [switch]$UseTemporaryEnable,
    [switch]$AsJson
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

    return $null
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
                throw "Timed out waiting for runtime diagnostic config lock: $lockPath"
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
        throw "Failed to temporarily enable product_creative in config.yaml."
    }
}

function Invoke-HermesProbe {
    param(
        [string]$Python,
        [string]$RepoRoot,
        [bool]$LoadPlugin
    )

    $probe = @'
import json
import os
import sys
from pathlib import Path

out = {
    "python_executable": sys.executable,
    "python_cwd": str(Path.cwd()),
    "hermes_cli_import": None,
    "hermes_home_runtime": None,
    "config": {},
    "product_plugin": None,
    "error": None,
}

try:
    import hermes_cli
    out["hermes_cli_import"] = str(Path(hermes_cli.__file__).resolve())

    try:
        from hermes_constants import get_hermes_home
        out["hermes_home_runtime"] = str(get_hermes_home())
    except Exception as exc:
        out["hermes_home_runtime_error"] = repr(exc)

    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        model = cfg.get("model", {}) if isinstance(cfg.get("model", {}), dict) else {}
        plugins = cfg.get("plugins", {}) if isinstance(cfg.get("plugins", {}), dict) else {}
        out["config"] = {
            "model_provider": model.get("provider"),
            "model_default": model.get("default"),
            "model_base_url": model.get("base_url"),
            "plugins_enabled": plugins.get("enabled"),
            "product_creative_enabled": "product_creative" in (plugins.get("enabled") or []),
        }
    except Exception as exc:
        out["config_error"] = repr(exc)

    if os.environ.get("PRODUCT_CREATIVE_CHECK_PLUGIN_LOAD") == "1":
        from hermes_cli.plugins import get_plugin_manager
        manager = get_plugin_manager()
        manager.discover_and_load(force=True)
        plugins = manager.list_plugins()
        product = None
        for item in plugins:
            if item.get("key") == "product_creative" or item.get("name") == "product_creative":
                product = item
                break
        out["product_plugin"] = product
        out["registered_product_skills"] = manager.list_plugin_skills("product_creative")
except Exception as exc:
    out["error"] = repr(exc)

print(json.dumps(out, ensure_ascii=False, indent=2))
'@

    $oldCheck = $env:PRODUCT_CREATIVE_CHECK_PLUGIN_LOAD
    $oldEncoding = $env:PYTHONIOENCODING
    try {
        if ($LoadPlugin) {
            $env:PRODUCT_CREATIVE_CHECK_PLUGIN_LOAD = "1"
        }
        else {
            Remove-Item Env:\PRODUCT_CREATIVE_CHECK_PLUGIN_LOAD -ErrorAction SilentlyContinue
        }
        $env:PYTHONIOENCODING = "utf-8"

        Push-Location $RepoRoot
        try {
            $raw = $probe | & $Python -
            if ($LASTEXITCODE -ne 0) {
                return [ordered]@{
                    ok = $false
                    error = "Hermes probe exited with code $LASTEXITCODE"
                    raw = $raw
                }
            }
            return $raw | ConvertFrom-Json
        }
        finally {
            Pop-Location
        }
    }
    finally {
        if ($null -eq $oldCheck) {
            Remove-Item Env:\PRODUCT_CREATIVE_CHECK_PLUGIN_LOAD -ErrorAction SilentlyContinue
        }
        else {
            $env:PRODUCT_CREATIVE_CHECK_PLUGIN_LOAD = $oldCheck
        }

        if ($null -eq $oldEncoding) {
            Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue
        }
        else {
            $env:PYTHONIOENCODING = $oldEncoding
        }
    }
}

$repoRoot = Get-RepoRoot
$hermesHome = Get-DefaultHermesHome
$configPath = Join-Path $hermesHome "config.yaml"
$installedRoot = Join-Path $hermesHome "hermes-agent"
$desktopExe = Join-Path $installedRoot "apps\desktop\release\win-unpacked\Hermes.exe"
$devVenvPython = Join-Path $repoRoot "venv\Scripts\python.exe"
$python = Get-HermesPython -HermesHome $hermesHome
$hermesCommand = Get-Command hermes -ErrorAction SilentlyContinue
$pluginManifest = Join-Path $repoRoot ".hermes\plugins\product_creative\plugin.yaml"

if (-not $python) {
    throw "Could not find a Python runtime. Expected Hermes venv under '$installedRoot\venv'."
}

$previousProjectPlugins = $env:HERMES_ENABLE_PROJECT_PLUGINS
$hadConfig = Test-Path -LiteralPath $configPath
$backup = $null
$configLock = $null

try {
    if ($UseTemporaryEnable) {
        $CheckPluginLoad = $true
        $configLock = Enter-ConfigLock -HermesHome $hermesHome
        $env:HERMES_ENABLE_PROJECT_PLUGINS = "1"
        $backup = New-TemporaryFile
        if ($hadConfig) {
            Copy-Item -LiteralPath $configPath -Destination $backup.FullName -Force
        }
        Enable-ProductCreativePlugin -Python $python
    }

    if ($CheckPluginLoad -and -not $env:HERMES_ENABLE_PROJECT_PLUGINS) {
        $env:HERMES_ENABLE_PROJECT_PLUGINS = "1"
    }

    $probe = Invoke-HermesProbe -Python $python -RepoRoot $repoRoot -LoadPlugin ([bool]$CheckPluginLoad)
}
finally {
    if ($UseTemporaryEnable) {
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
            $configLock = $null
        }
    }

    if ($null -eq $previousProjectPlugins) {
        Remove-Item Env:\HERMES_ENABLE_PROJECT_PLUGINS -ErrorAction SilentlyContinue
    }
    else {
        $env:HERMES_ENABLE_PROJECT_PLUGINS = $previousProjectPlugins
    }
}

$importsDevSource = $false
if ($probe -and $probe.hermes_cli_import) {
    $importsDevSource = $probe.hermes_cli_import.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)
}

$verdict = @()
if (-not (Test-Path -LiteralPath $pluginManifest)) {
    $verdict += "Missing project product_creative plugin manifest."
}
if (-not $importsDevSource) {
    $verdict += "Hermes probe is not importing hermes_cli from the development repo."
}
if (-not $UseTemporaryEnable -and $probe.config -and -not $probe.config.product_creative_enabled) {
    $verdict += "product_creative is not enabled in config; use -UseTemporaryEnable for temporary validation or enable the plugin before Hermes chat."
}
if ($CheckPluginLoad) {
    if (-not $probe.product_plugin) {
        $verdict += "product_creative plugin was not discovered."
    }
    elseif (-not $probe.product_plugin.enabled) {
        $verdict += "product_creative plugin was discovered but not loaded. Check plugins.enabled."
    }
}
if (-not $verdict) {
    $verdict += "Runtime wiring looks ready for project-level Hermes chat validation."
}

$report = [ordered]@{
    repo_root = $repoRoot
    hermes_home_env = $env:HERMES_HOME
    hermes_home_effective = $hermesHome
    config_path = $configPath
    config_exists = (Test-Path -LiteralPath $configPath)
    installed_root = $installedRoot
    desktop_exe = $desktopExe
    desktop_exe_exists = (Test-Path -LiteralPath $desktopExe)
    installed_venv_python = $python
    dev_venv_python_exists = (Test-Path -LiteralPath $devVenvPython)
    hermes_command = if ($hermesCommand) { $hermesCommand.Source } else { $null }
    project_plugins_env_for_probe = if ($CheckPluginLoad -or $UseTemporaryEnable) { "1" } else { $previousProjectPlugins }
    used_temporary_config_enable = [bool]$UseTemporaryEnable
    product_plugin_manifest_exists = (Test-Path -LiteralPath $pluginManifest)
    probe = $probe
    imports_dev_source = $importsDevSource
    verdict = $verdict
}

if ($AsJson -or $true) {
    $report | ConvertTo-Json -Depth 12
}
