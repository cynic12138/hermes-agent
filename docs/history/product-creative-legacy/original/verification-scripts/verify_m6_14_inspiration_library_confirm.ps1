param(
    [string]$ProductId = "m6-inspiration-library-confirm-test",
    [string]$PackId = "",
    [string]$Target = "xiaohongshu-seeding-note",
    [string]$Note = "Confirmed for M6.14 verification only.",
    [switch]$CreateFixture,
    [switch]$Confirmed,
    [switch]$GenerateAfterConfirm
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot "..\..\..\..")).Path
$ProductCreative = Join-Path $ScriptRoot "product_creative.ps1"
$ProductRoot = Join-Path $RepoRoot ".hermes\product_creative\products\$ProductId"

function Invoke-ProductCreative {
    param([string[]]$CommandArgs)

    $raw = & $ProductCreative @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "product_creative.ps1 failed: $($CommandArgs -join ' ')"
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

function Get-LibraryCount {
    $dir = Join-Path $ProductRoot "artifacts\inspiration_library"
    if (-not (Test-Path -LiteralPath $dir)) {
        return 0
    }
    return @((Get-ChildItem -LiteralPath $dir -Filter "*.json" -File)).Count
}

Invoke-ProductCreative -CommandArgs @("create", "--id", $ProductId, "--name", "M6 Inspiration Library Confirm Test") | Out-Null
Invoke-ProductCreative -CommandArgs @(
    "ingest",
    "--id", $ProductId,
    "--text", "A honey dew beverage workspace for testing user-confirmed inspiration library writes."
) | Out-Null

if ($CreateFixture -and [string]::IsNullOrWhiteSpace($PackId)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $PackId = "llm-inspiration-pack-m6-14-fixture-$stamp"
    $packDir = Join-Path $ProductRoot "artifacts\llm_inspiration_packs"
    New-Item -ItemType Directory -Force -Path $packDir | Out-Null
    $fixture = [ordered]@{
        schema_version = "product_creative.llm_inspiration_pack.v6.11"
        pack_id = $PackId
        product_id = $ProductId
        created_at = (Get-Date).ToUniversalTime().ToString("o")
        status = "review_required"
        status_reason = "user_review_required_before_library_write"
        summary_type = "llm_deep_inspiration_summary"
        goal = "Fixture LLM inspiration pack for M6.14 confirmation guard."
        target = $Target
        channel = if ($Target -eq "douyin-short-video-script") { "douyin" } else { "xiaohongshu" }
        source_snapshot_ids = @("fixture-source-snapshot")
        source_item_count = 1
        llm_summary = [ordered]@{
            summary_title = "Fixture inspiration"
            executive_summary = "Use clean honey-colored visuals and a daily-drink moment as creative inspiration only."
            channel_insights = @("Use scenario-first language.")
            hooks = @([ordered]@{ text = "今天的清甜感"; why_it_works = "Short, scenario-led hook."; rewrite_rule = "Rewrite with product-specific facts only." })
            content_angles = @([ordered]@{ angle = "daily refresh"; consumer_moment = "afternoon drink"; product_bridge = "bridge only through confirmed Product Brain facts" })
            script_or_note_structures = @("hook -> scene -> product -> review")
            visual_or_scene_directions = @("honey color, chilled bottle, clean table")
            generation_guidance = [ordered]@{
                copy_prompt_addition = "Use this as style inspiration only."
                image_brief_prompt_addition = "Use honey-color freshness only if product facts allow it."
                video_brief_prompt_addition = "Use short scene-first structure."
            }
            product_connection = [ordered]@{ fit_level = "medium"; how_to_use = "creative structure only"; do_not_claim = @("medical efficacy", "unconfirmed ingredients") }
            risks = @("Do not copy external wording.")
            library_card = [ordered]@{ title = "Fixture card"; tags = @("honey", "daily-drink"); reusable_rules = @("start from scene"); examples_to_avoid = @("medical claims") }
        }
        brief_context = "copy_prompt_addition: Use this as style inspiration only.`nimage_brief_prompt_addition: Use honey-color freshness only if product facts allow it.`nvideo_brief_prompt_addition: Use short scene-first structure."
        llm = [ordered]@{ provider = "fixture"; model = "fixture"; agent_id = ""; usage = [ordered]@{}; content_type = "fixture"; call_mode = "fixture" }
        review_contract = [ordered]@{
            must_be_reviewed_by_user = $true
            may_be_written_to_inspiration_library_after_confirmation = $true
            external_sources_are_not_product_facts = $true
            does_not_update_product_brain = $true
        }
        requires_user_confirmation_for_library = $true
        confirmation_status = "pending"
        not_product_fact = $true
        mutates_product_brain = $false
    }
    $fixture | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $packDir "$PackId.json") -Encoding UTF8
}

if ([string]::IsNullOrWhiteSpace($PackId)) {
    $packDir = Join-Path $ProductRoot "artifacts\llm_inspiration_packs"
    $latest = if (Test-Path -LiteralPath $packDir) {
        Get-ChildItem -LiteralPath $packDir -Filter "*.json" -File | Sort-Object LastWriteTime | Select-Object -Last 1
    }
    else {
        $null
    }
    if (-not $latest) {
        throw "No LLM inspiration pack found. Pass -PackId or use -CreateFixture."
    }
    $PackId = [System.IO.Path]::GetFileNameWithoutExtension($latest.Name)
}

$beforeCount = Get-LibraryCount
$guard = Invoke-ProductCreative -CommandArgs @(
    "inspiration-library-confirm",
    "--id", $ProductId,
    "--pack", $PackId,
    "--note", $Note
)
Assert-True ($guard.status -eq "review_required") "Confirmation guard should require explicit user confirmation."
Assert-True ((Get-LibraryCount) -eq $beforeCount) "Library entry was written without explicit confirmation."

$entry = $null
$generated = $null
if ($Confirmed) {
    $entry = Invoke-ProductCreative -CommandArgs @(
        "inspiration-library-confirm",
        "--id", $ProductId,
        "--pack", $PackId,
        "--note", $Note,
        "--confirmed"
    )
    Assert-True ($entry.status -eq "active") "Confirmed inspiration library entry is not active."
    $afterFirstCount = Get-LibraryCount
    Assert-True (($entry.idempotent_replay -and $afterFirstCount -eq $beforeCount) -or $afterFirstCount -gt $beforeCount) "Confirmed library entry was not written or replayed."

    $replay = Invoke-ProductCreative -CommandArgs @(
        "inspiration-library-confirm",
        "--id", $ProductId,
        "--pack", $PackId,
        "--note", $Note,
        "--confirmed"
    )
    Assert-True ($replay.entry_id -eq $entry.entry_id) "Repeated confirmation created a different logical entry."
    Assert-True ((Get-LibraryCount) -eq $afterFirstCount) "Repeated confirmation created a duplicate library entry."

    if ($GenerateAfterConfirm) {
        $generated = Invoke-ProductCreative -CommandArgs @(
            "generate",
            "--id", $ProductId,
            "--target", $Target,
            "--variants", "1"
        )
        Assert-True ($generated.material_context.inspiration_context.source -eq "inspiration_library") "Generation did not use inspiration_library context."
        Assert-True ($generated.material_context.inspiration_context.entry_id -eq $entry.entry_id) "Generation did not use the confirmed library entry."
    }
}

[pscustomobject]@{
    success = $true
    product_id = $ProductId
    pack_id = $PackId
    guard_status = $guard.status
    confirmed = [bool]$Confirmed
    entry_id = if ($entry) { $entry.entry_id } else { "" }
    generated_artifact_id = if ($generated) { $generated.artifact_id } else { "" }
    generation_used_inspiration_library = if ($generated) { $generated.material_context.inspiration_context.source -eq "inspiration_library" } else { $false }
    external_call_performed = $false
    note = "M6.14 confirmation guard verified. Use -Confirmed -GenerateAfterConfirm only after review approval."
} | ConvertTo-Json -Depth 8
