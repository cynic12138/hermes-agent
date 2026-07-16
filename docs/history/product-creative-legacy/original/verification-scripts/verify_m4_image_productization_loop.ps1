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

function Has-ArtifactType {
    param(
        [object]$Manifest,
        [string]$Type
    )
    return @($Manifest.manifest.artifacts | Where-Object { $_.artifact_type -eq $Type }).Count -gt 0
}

function Get-ImagePreferenceCount {
    param([object]$State)
    if ($null -eq $State.learning -or $null -eq $State.learning.image_generation_preferences) {
        return 0
    }
    return @($State.learning.image_generation_preferences).Count
}

$runner = Join-Path $PSScriptRoot "product_creative.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$previousDisableLlm = $env:PRODUCT_CREATIVE_DISABLE_LLM
$env:PRODUCT_CREATIVE_DISABLE_LLM = "1"
$tempImage = Join-Path ([System.IO.Path]::GetTempPath()) "m4-main-image-$stamp.png"

try {
    $png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    [System.IO.File]::WriteAllBytes($tempImage, $png)

    $productId = "m4-image-$stamp"
    $create = Invoke-JsonScript -ScriptPath $runner -InputArgs @("create", "--id", $productId, "--name", "周十五蜂蜜露")
    $ingest = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "ingest",
        "--id",
        $productId,
        "--text",
        "周十五蜂蜜露是一款清甜饮品，核心卖点是清爽口感、日常分享、产品主体清晰。内容生成需避免夸大功效。"
    )
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
        "product_reference",
        "--usage",
        "image_reference"
    )
    $analysis = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-analyze",
        "--id",
        $productId,
        "--asset",
        $asset.material_id,
        "--provider",
        "mock-vision"
    )
    $cards = Invoke-JsonScript -ScriptPath $runner -InputArgs @("material-card-rebuild", "--id", $productId)

    $base = Join-Path $repoRoot (".hermes\product_creative\products\" + $productId)
    $statePath = Join-Path $base "structured\product_state.json"
    $stateBeforeM4 = Read-JsonFile -Path $statePath
    $imagePreferenceCountBefore = Get-ImagePreferenceCount -State $stateBeforeM4

    $workflowRun = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "workflow-run",
        "--id",
        $productId,
        "--message",
        "帮我生成3张电商主图，高级感",
        "--max-steps",
        "5"
    )
    $statusAfterWorkflow = Invoke-JsonScript -ScriptPath $runner -InputArgs @("workflow-status", "--id", $productId)
    $intentId = $statusAfterWorkflow.evidence.latest_image_intent.id
    $briefId = $statusAfterWorkflow.evidence.latest_image_brief.id
    $reviewId = $statusAfterWorkflow.evidence.latest_image_brief_review.id

    $policy = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "batch-policy",
        "--id",
        $productId,
        "--intent",
        $intentId,
        "--brief",
        $briefId,
        "--provider",
        "volcengine-ark-image",
        "--mode",
        "mock",
        "--count",
        "3",
        "--confirmed",
        "--note",
        "确认本批电商主图生成策略"
    )
    $payload = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-provider-payload",
        "--id",
        $productId,
        "--brief",
        $briefId,
        "--provider",
        "volcengine-ark-image",
        "--batch-policy",
        $policy.policy_id
    )
    $imageRun = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "image-run",
        "--id",
        $productId,
        "--payload",
        $payload.payload_id,
        "--provider",
        "generic",
        "--mode",
        "mock",
        "--count",
        "2"
    )
    $resultId = $imageRun.image_generation_run.jobs[0].result_id
    $feedback = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "result-feedback",
        "--id",
        $productId,
        "--result",
        $resultId,
        "--selected",
        "--rating",
        "5",
        "--allow-evolve",
        "--subject-clarity",
        "5",
        "--product-recognizability",
        "5",
        "--composition",
        "5",
        "--style-fit",
        "5",
        "--copy-fit",
        "5",
        "--note",
        "这张图适合作为后续高级感电商主图方向"
    )
    $proposal = Invoke-JsonScript -ScriptPath $runner -InputArgs @("evolve", "--id", $productId)
    $selectedAsset = Invoke-JsonScript -ScriptPath $runner -InputArgs @(
        "selected-image-asset",
        "--id",
        $productId,
        "--result",
        $resultId,
        "--role",
        "generated_candidate",
        "--description",
        "M4验证选中的生成候选图"
    )
    $manifest = Invoke-JsonScript -ScriptPath $runner -InputArgs @("artifact-manifest", "--id", $productId)
    $stateAfterM4 = Read-JsonFile -Path $statePath
    $imagePreferenceCountAfter = Get-ImagePreferenceCount -State $stateAfterM4

    $runActions = @($workflowRun.executions | ForEach-Object { $_.action })
    $proposalTargetsImageLearning = @($proposal.proposal.target_state_paths | Where-Object { $_ -eq "learning.image_generation_preferences" }).Count -gt 0
    $selectedAssetPayload = Read-JsonFile -Path $selectedAsset.files.json

    $passed = [bool](
        $create.success -and
        $ingest.success -and
        $asset.success -and
        $analysis.success -and
        $cards.success -and
        ($workflowRun.stop_reason -eq "requires_explicit_confirmation") -and
        ($runActions -contains "resolve_image_intent") -and
        ($runActions -contains "create_image_brief") -and
        ($runActions -contains "review_image_brief") -and
        $intentId -and
        $briefId -and
        $reviewId -and
        ($policy.status -eq "active") -and
        $payload.success -and
        ($payload.validation.status -eq "valid") -and
        $imageRun.success -and
        ($imageRun.external_call_count -eq 0) -and
        ($imageRun.image_generation_run.count -eq 2) -and
        $feedback.success -and
        $feedback.eligible_for_evolution_proposal -and
        $proposal.success -and
        $proposalTargetsImageLearning -and
        $selectedAsset.success -and
        ($selectedAsset.role -eq "generated_candidate") -and
        ($selectedAssetPayload.generation_source.source_result_id -eq $resultId) -and
        (Has-ArtifactType -Manifest $manifest -Type "image_intent") -and
        (Has-ArtifactType -Manifest $manifest -Type "image_brief_review") -and
        (Has-ArtifactType -Manifest $manifest -Type "batch_generation_policy") -and
        (Has-ArtifactType -Manifest $manifest -Type "image_generation_run") -and
        ($imagePreferenceCountAfter -eq $imagePreferenceCountBefore)
    )

    [pscustomobject]@{
        success = $passed
        product_id = $productId
        live_call_count = 0
        workflow_run = $workflowRun.files.json
        workflow_stop_reason = $workflowRun.stop_reason
        workflow_actions = $runActions
        image_intent = $intentId
        image_brief = $briefId
        image_brief_review = $reviewId
        batch_policy = $policy.policy_id
        provider_payload = $payload.payload_id
        image_generation_run = $imageRun.image_run_id
        result_feedback = $feedback.feedback_id
        evolution_proposal = $proposal.proposal_id
        selected_material = $selectedAsset.material_id
        selected_material_role = $selectedAsset.role
        image_learning_written_without_apply = ($imagePreferenceCountAfter -ne $imagePreferenceCountBefore)
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
    Remove-Item -LiteralPath $tempImage -Force -ErrorAction SilentlyContinue
}

