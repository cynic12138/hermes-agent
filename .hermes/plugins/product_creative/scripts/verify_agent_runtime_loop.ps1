param(
    [string]$ProductId = ""
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot "..\..\..\..")).Path
$ProductCreative = Join-Path $ScriptRoot "product_creative.ps1"

if (-not $ProductId) {
    $ProductId = "agent-runtime-loop-$((Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss'))"
}

$ProductRoot = Join-Path $RepoRoot ".hermes\product_creative\products\$ProductId"

function Invoke-ProductCreativeJson {
    param([string[]]$CommandArgs)

    $raw = & $ProductCreative @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "product_creative.ps1 failed: $($CommandArgs -join ' ')`n$raw"
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

function Count-Items {
    param($Value)

    return (($Value | Measure-Object).Count)
}

$created = Invoke-ProductCreativeJson -CommandArgs @("create", "--id", $ProductId, "--name", "Agent Runtime Loop Test")
Assert-True $created.success "Product creation failed."

$sourceText = @"
产品名：Agent Runtime Loop Test
主打：清爽自然、低糖、冷藏即饮，适合下午茶和轻负担场景。
包装：浅色瓶身，视觉要干净、有高级质感。
表达偏好：不要太促销，强调真实场景和轻决策。
"@

$ingested = Invoke-ProductCreativeJson -CommandArgs @("ingest", "--id", $ProductId, "--text", $sourceText)
Assert-True $ingested.success "Product ingest failed."

$fixtureDir = Join-Path $ProductRoot "raw\fixtures"
New-Item -ItemType Directory -Force -Path $fixtureDir | Out-Null
$imagePath = Join-Path $fixtureDir "main.png"
[byte[]]$png = [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
[System.IO.File]::WriteAllBytes($imagePath, $png)

$materialTurn = Invoke-ProductCreativeJson -CommandArgs @(
    "workflow-run",
    "--id", $ProductId,
    "--message", "登记这张主图素材，作为当前主图",
    "--path", $imagePath,
    "--role", "current_main_image",
    "--description", "Agent runtime loop test main image",
    "--usage", "provider_payload",
    "--max-steps", "1"
)
Assert-True ($materialTurn.interpreted_intent.action -eq "register_material_asset") "Agent turn did not understand material registration."
Assert-True ($materialTurn.execution_contract.executed -eq $true) "Agent turn did not register material."

$external = Invoke-ProductCreativeJson -CommandArgs @(
    "external-source",
    "--id", $ProductId,
    "--provider", "manual",
    "--query", "小红书下午茶灵感",
    "--channel", "xiaohongshu",
    "--mode", "import",
    "--text", "爆款灵感：先用下午茶场景开头，再突出低糖清爽，结尾用轻决策引导。"
)
Assert-True $external.success "External inspiration source import failed."

$candidates = Invoke-ProductCreativeJson -CommandArgs @(
    "inspiration-candidates",
    "--id", $ProductId,
    "--snapshot", $external.snapshot_id,
    "--goal", "提炼小红书种草结构",
    "--max-candidates", "3"
)
Assert-True ($candidates.success -and (Count-Items $candidates.candidates) -ge 1) "Inspiration candidate extraction failed."

$firstCandidate = $candidates.candidates[0].candidate_id
$pack = Invoke-ProductCreativeJson -CommandArgs @(
    "inspiration-pack",
    "--id", $ProductId,
    "--candidate", $firstCandidate,
    "--goal", "用于下一轮小红书种草",
    "--target", "xiaohongshu-seeding-note",
    "--limit", "3"
)
Assert-True $pack.success "Inspiration pack creation failed."

$generationTurn = Invoke-ProductCreativeJson -CommandArgs @(
    "workflow-run",
    "--id", $ProductId,
    "--message", "请生成一轮小红书种草文案，出1版",
    "--target", "xiaohongshu-seeding-note",
    "--variants", "1",
    "--max-steps", "1"
)
Assert-True ($generationTurn.interpreted_intent.action -eq "run_channel_review") "Agent turn did not route content generation."
Assert-True ($generationTurn.execution_contract.executed -eq $true) "Agent turn did not execute content generation."
$artifactId = $generationTurn.created_artifacts.channel_content.id
Assert-True ([bool]$artifactId) "Agent turn did not return generated channel content artifact id."

$feedback = Invoke-ProductCreativeJson -CommandArgs @(
    "channel-feedback",
    "--id", $ProductId,
    "--artifact", $artifactId,
    "--note", "这版高级质感和低促销表达适合，后续保持下午茶真实场景开头。",
    "--selected",
    "--variant", "1",
    "--rating", "5",
    "--allow-evolve",
    "--like-reason", "高级质感",
    "--like-reason", "下午茶真实场景"
)
Assert-True ($feedback.success -and $feedback.eligible_for_evolution_proposal) "Channel feedback should be eligible for evolution."

$proposalTurn = Invoke-ProductCreativeJson -CommandArgs @(
    "workflow-run",
    "--id", $ProductId,
    "--message", "生成学习提案",
    "--max-steps", "1"
)
Assert-True ($proposalTurn.interpreted_intent.action -eq "create_evolution_proposal") "Agent turn did not route learning proposal creation."
Assert-True ($proposalTurn.execution_contract.executed -eq $true) "Agent turn did not create learning proposal."
Assert-True ($proposalTurn.learning_writeback.status -eq "proposal_created") "Agent turn did not expose proposal_created learning state."
$proposalId = $proposalTurn.learning_writeback.proposal_id
Assert-True ([bool]$proposalId) "Agent turn did not return proposal id."
Assert-True ($proposalTurn.recommended_next_action.action -eq "apply_evolution_proposal") "Next action should ask for proposal apply."
Assert-True ($proposalTurn.recommended_next_action.requires_explicit_confirmation -eq $true) "Proposal apply should require explicit confirmation."

$applyTurn = Invoke-ProductCreativeJson -CommandArgs @(
    "workflow-run",
    "--id", $ProductId,
    "--message", "确认应用这个学习提案 $proposalId",
    "--confirmed",
    "--max-steps", "1"
)
Assert-True ($applyTurn.interpreted_intent.action -eq "apply_evolution_proposal") "Agent turn did not route proposal apply."
Assert-True ($applyTurn.execution_contract.executed -eq $true) "Agent turn did not apply proposal."
Assert-True ($applyTurn.execution_contract.confirmed -eq $true) "Agent turn did not preserve confirmation."
Assert-True ($applyTurn.execution_contract.requires_explicit_confirmation -eq $false) "Confirmed apply should not remain pending confirmation."
Assert-True ($applyTurn.learning_writeback.status -eq "applied") "Agent turn did not expose applied learning state."
Assert-True ([int]$applyTurn.learning_writeback.applied_update_count -ge 1) "No learning updates were applied."

$context = Invoke-ProductCreativeJson -CommandArgs @("context", "--id", $ProductId, "--target", "xiaohongshu-seeding-note")
$learningText = ($context.state.learning | ConvertTo-Json -Depth 12)
Assert-True ($learningText.Contains("高级质感") -or $learningText.Contains("下午茶真实场景")) "Context pack does not expose applied learning."

$next = Invoke-ProductCreativeJson -CommandArgs @("generate", "--id", $ProductId, "--target", "xiaohongshu-seeding-note", "--variants", "1")
Assert-True ($next.success -and (Test-Path -LiteralPath $next.artifact_json)) "Next generation failed after learning writeback."

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    material_intent = $materialTurn.interpreted_intent.action
    inspiration_snapshot_id = $external.snapshot_id
    inspiration_pack_id = $pack.pack_id
    generated_artifact_id = $artifactId
    proposal_id = $proposalId
    applied_update_count = $applyTurn.learning_writeback.applied_update_count
    context_learning_verified = $true
    next_generation = $next.artifact_json
} | ConvertTo-Json -Depth 8
