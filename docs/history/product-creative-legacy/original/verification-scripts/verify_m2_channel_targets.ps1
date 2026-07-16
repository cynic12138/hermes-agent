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
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$previousDisableLlm = $env:PRODUCT_CREATIVE_DISABLE_LLM
$env:PRODUCT_CREATIVE_DISABLE_LLM = "1"

try {
    $productA = "m2-channel-a-$stamp"
    $productB = "m2-channel-b-$stamp"

    $createA = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productA, "--name", "山野冻干蓝莓")
    $ingestA = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productA,
        "--text",
        "山野冻干蓝莓，真实果粒，酸甜清爽，适合办公室轻零食和早餐酸奶搭配。主图希望高级质感，突出真实果粒，不要太促销。"
    )
    $upgradeA = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-upgrade", "--id", $productA)

    $createB = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productB, "--name", "暖光护眼阅读灯")
    $ingestB = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productB,
        "--text",
        "暖光护眼阅读灯，光线柔和，适合睡前阅读和学习桌使用，强调稳定底座、低频闪和家长可信。"
    )
    $upgradeB = Invoke-JsonScript -ScriptPath $runner -InputArgs @("wiki-upgrade", "--id", $productB)

    $targetList = Invoke-JsonScript -ScriptPath $runner -InputArgs @("target-list")
    $targetNames = @($targetList.targets | ForEach-Object { $_.target })
    $expectedTargets = @(
        "product-copy-pack",
        "ecommerce-main-image-copy",
        "xiaohongshu-seeding-note",
        "douyin-short-video-script"
    )

    $contexts = @{}
    foreach ($target in $expectedTargets) {
        $contexts[$target] = Invoke-JsonScript -ScriptPath $runner -InputArgs @("context", "--id", $productA, "--target", $target)
    }

    $generated = @{}
    foreach ($target in @("product-copy-pack", "ecommerce-main-image-copy", "xiaohongshu-seeding-note", "douyin-short-video-script")) {
        $result = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
            "generate",
            "--id",
            $productA,
            "--target",
            $target,
            "--variants",
            "2"
        )
        $payload = Read-JsonFile -Path $result.artifact_json
        $generated[$target] = [pscustomobject]@{
            result = $result
            payload = $payload
            markdown_exists = Test-Path -LiteralPath $result.artifact_markdown
        }
    }

    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productA)
    $manifestTargets = @($manifest.manifest.artifacts | ForEach-Object {
        if ($_.artifact_type -eq "channel_content") {
            $doc = Read-JsonFile -Path (Join-Path (Split-Path -Parent $manifest.files.json) ("..\\" + $_.path))
            $doc.target
        }
    })

    $contextChecks = @()
    foreach ($target in $expectedTargets) {
        $context = $contexts[$target]
        $contextJson = $context | ConvertTo-Json -Depth 20
        $contextChecks += [pscustomobject]@{
            target = $target
            success = $context.success
            context_profile = $context.context_profile
            page_count = @($context.page_list).Count
            has_other_product = $contextJson.Contains($productB)
            lint_errors = $context.lint_summary.error_count
        }
    }

    $generationChecks = @(
        [pscustomobject]@{
            target = "product-copy-pack"
            ok = $generated["product-copy-pack"].result.success -and
                @($generated["product-copy-pack"].payload.variants).Count -eq 2 -and
                $generated["product-copy-pack"].payload.generation_method -eq "rule-fallback" -and
                $generated["product-copy-pack"].markdown_exists
        },
        [pscustomobject]@{
            target = "ecommerce-main-image-copy"
            ok = $generated["ecommerce-main-image-copy"].result.success -and
                $generated["ecommerce-main-image-copy"].payload.schema_version -eq "product_creative.channel_content.v2.2" -and
                @($generated["ecommerce-main-image-copy"].payload.variants).Count -eq 2 -and
                [bool]$generated["ecommerce-main-image-copy"].payload.variants[0].main_title -and
                [bool]$generated["ecommerce-main-image-copy"].payload.variants[0].visual_prompt_seed -and
                $generated["ecommerce-main-image-copy"].markdown_exists
        },
        [pscustomobject]@{
            target = "xiaohongshu-seeding-note"
            ok = $generated["xiaohongshu-seeding-note"].result.success -and
                $generated["xiaohongshu-seeding-note"].payload.schema_version -eq "product_creative.channel_content.v2.2" -and
                @($generated["xiaohongshu-seeding-note"].payload.variants[0].title_options).Count -gt 0 -and
                [bool]$generated["xiaohongshu-seeding-note"].payload.variants[0].body -and
                @($generated["xiaohongshu-seeding-note"].payload.variants[0].hashtags).Count -gt 0 -and
                $generated["xiaohongshu-seeding-note"].markdown_exists
        },
        [pscustomobject]@{
            target = "douyin-short-video-script"
            ok = $generated["douyin-short-video-script"].result.success -and
                $generated["douyin-short-video-script"].payload.schema_version -eq "product_creative.channel_content.v2.2" -and
                [bool]$generated["douyin-short-video-script"].payload.variants[0].hook_0_3s -and
                @($generated["douyin-short-video-script"].payload.variants[0].shots).Count -gt 0 -and
                [bool]$generated["douyin-short-video-script"].payload.variants[0].video_brief_seed -and
                $generated["douyin-short-video-script"].markdown_exists
        }
    )

    $passed = [bool](
        $createA.success -and
        $ingestA.success -and
        $upgradeA.success -and
        $createB.success -and
        $ingestB.success -and
        $upgradeB.success -and
        $targetList.success -and
        (@($expectedTargets | Where-Object { $targetNames -notcontains $_ }).Count -eq 0) -and
        (@($contextChecks | Where-Object {
            -not $_.success -or
            $_.context_profile -ne $_.target -or
            $_.page_count -lt 7 -or
            $_.has_other_product -or
            $_.lint_errors -ne 0
        }).Count -eq 0) -and
        (@($generationChecks | Where-Object { -not $_.ok }).Count -eq 0) -and
        (@($manifestTargets | Where-Object {
            $_ -in @("ecommerce-main-image-copy", "xiaohongshu-seeding-note", "douyin-short-video-script")
        }).Count -eq 3)
    )

    [pscustomobject]@{
        success = $passed
        live_call_count = 0
        products = @($productA, $productB)
        expected_targets = $expectedTargets
        target_list = $targetNames
        context_checks = $contextChecks
        generation_checks = $generationChecks
        artifacts = @($generated.Keys | ForEach-Object {
            [pscustomobject]@{
                target = $_
                json = $generated[$_].result.artifact_json
                markdown = $generated[$_].result.artifact_markdown
            }
        })
        manifest = $manifest.files.json
    } | ConvertTo-Json -Depth 8

    if (-not $passed) {
        exit 1
    }
}
finally {
    if ($null -eq $previousDisableLlm) {
        Remove-Item Env:\PRODUCT_CREATIVE_DISABLE_LLM -ErrorAction SilentlyContinue
    }
    else {
        $env:PRODUCT_CREATIVE_DISABLE_LLM = $previousDisableLlm
    }
}
