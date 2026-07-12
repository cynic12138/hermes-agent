param(
    [Parameter(Position = 0)]
    [string]$Command = "",
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$RestArgs = @()
)

$ErrorActionPreference = "Stop"
$CommandArgs = @()
if ($Command) {
    $CommandArgs += $Command
}
if ($RestArgs) {
    $CommandArgs += $RestArgs
}

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

    $candidates = @()
    $candidates += (Join-Path $HermesHome "hermes-agent\venv\Scripts\python.exe")
    $candidates += (Join-Path $HermesHome "hermes-agent\venv\bin\python")

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
    $deadline = (Get-Date).AddSeconds(300)
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

    $tempScript = New-TemporaryFile
    try {
        Set-Content -LiteralPath $tempScript.FullName -Value $script -Encoding UTF8
        & $Python $tempScript.FullName | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to temporarily enable product_creative plugin."
        }
    }
    finally {
        Remove-Item -LiteralPath $tempScript.FullName -Force -ErrorAction SilentlyContinue
    }
}

function Get-HermesArgs {
    param([string[]]$InputArgs)

    if (-not $InputArgs -or $InputArgs.Count -eq 0) {
        Write-Host "usage: product_creative.ps1 [product] {create,ingest,workspace-resolve,target-list,generate,evaluate,channel-evaluate,channel-review-package,channel-review-run,brief,image-generate,image-intent,image-brief,image-brief-review,image-brief-revise,batch-policy,image-provider-payload,image-run,selected-image-asset,video-generate,provider-list,provider-validate,generation-job,artifact-manifest,review-package,result-feedback,result-review-package,result-evaluate,task-overview-package,exact-main-video,channel-feedback,video-brief-feedback,live-readiness,video-reference-readiness,video-execution-policy,video-task-status,video-result-import,wiki-upgrade,wiki-lint,state-export,fingerprint,creative-run,image-qa,comparison-package,feedback,evolve,context,workflow-status,workflow-next,workflow-summary,action-guard,workflow-plan,conversation-adapter,workflow-execute,workflow-run,asset-register,asset-bind-url,asset-list,material-manifest,material-compat,material-card-rebuild,material-library-map,task-material-pack,material-usage,material-feedback,external-source,inspiration-candidates,inspiration-pack,llm-inspiration-pack,inspiration-library-confirm,image-analyze,visual-align,video-intent,video-brief,video-brief-review,video-brief-revise} ..."
        exit 2
    }
    if ($InputArgs[0] -eq "product") {
        return $InputArgs
    }
    return @("product") + $InputArgs
}

$repoRoot = Get-RepoRoot
$hermesHome = Get-DefaultHermesHome
$configPath = Join-Path $hermesHome "config.yaml"
$python = Get-HermesPython -HermesHome $hermesHome
$hermesArgs = Get-HermesArgs -InputArgs $CommandArgs

$hadConfig = Test-Path -LiteralPath $configPath
$backup = New-TemporaryFile
$configLock = $null
$previousProjectPlugins = $env:HERMES_ENABLE_PROJECT_PLUGINS
$pushed = $false
$exitCode = 0

try {
    $configLock = Enter-ConfigLock -HermesHome $hermesHome
    if ($hadConfig) {
        Copy-Item -LiteralPath $configPath -Destination $backup.FullName -Force
    }

    $env:HERMES_ENABLE_PROJECT_PLUGINS = "1"
    Push-Location $repoRoot
    $pushed = $true

    Enable-ProductCreativePlugin -Python $python

    & $python -m hermes_cli.main @hermesArgs
    $exitCode = $LASTEXITCODE
}
finally {
    if ($pushed) {
        Pop-Location
    }

    if ($hadConfig) {
        Copy-Item -LiteralPath $backup.FullName -Destination $configPath -Force
    }
    elseif (Test-Path -LiteralPath $configPath) {
        Remove-Item -LiteralPath $configPath -Force
    }

    Remove-Item -LiteralPath $backup.FullName -Force -ErrorAction SilentlyContinue
    if ($configLock) {
        $configLock.Dispose()
        $configLock = $null
    }

    if ($null -eq $previousProjectPlugins) {
        Remove-Item Env:\HERMES_ENABLE_PROJECT_PLUGINS -ErrorAction SilentlyContinue
    }
    else {
        $env:HERMES_ENABLE_PROJECT_PLUGINS = $previousProjectPlugins
    }
}

exit $exitCode
