[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import json
import os
import sys
import tempfile
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / ".hermes" / "plugins"))

from product_creative.brain.rules import persist_rule_candidates, rule_candidates_from_updates
from product_creative.cli import CLI_COMMAND_HANDLERS
from product_creative.contracts.actions import ACTION_NAMES
from product_creative.provider_gateway import configure_generation_provider_gateway, generation_provider_gateway
from product_creative.runtime.action_registry import action_runtime_registry
from product_creative.runtime.decision_service import configure_llm, decide_intent
from product_creative.runtime.workflow_catalog import workflow_definitions
from product_creative.capabilities.product.schemas import WORKFLOW_ACTION_ENUM
from product_creative.stores import (
    FileSystemArtifactRepository,
    FileSystemMaterialRepository,
    FileSystemProductBrainRepository,
    FileSystemStructuredRepository,
)
from product_creative.tools import product_tool_handlers
from product_creative.infrastructure.sqlite.domain_repositories import SqliteRuleRepository


class Response:
    parsed = {
        "action": "resolve_image_intent",
        "goal": "create product image",
        "modality": "image",
        "confidence": 0.92,
        "rationale": "user requested image generation",
        "source": "llm",
    }


class FakeLlm:
    def complete_structured(self, **_kwargs):
        return Response()


class FakeGateway:
    def check_live_readiness(self, product_id, provider, kind, payload_id):
        return {"success": True, "product_id": product_id, "provider": provider, "kind": kind, "payload_id": payload_id, "fake": True}


failures = []
with tempfile.TemporaryDirectory(prefix="product-creative-runtime-") as temp:
    base = Path(temp) / f"runtime-test-{Path(temp).name}"
    (base / "structured").mkdir(parents=True)
    brain = FileSystemProductBrainRepository(base)
    brain.save_state({"schema_version": "test", "product_id": base.name, "learning": {}})
    if brain.load_state().get("product_id") != base.name:
        failures.append("product_brain_repository_roundtrip")

    structured = FileSystemStructuredRepository(base)
    artifacts = FileSystemArtifactRepository(base)
    materials = FileSystemMaterialRepository(base)
    structured.save("tests", "one", {"kind": "structured"})
    artifacts.save("tests", "one", {"kind": "artifact"})
    materials.save_asset("material-one", {"material_id": "material-one"})
    materials.save_library({"assets": ["material-one"]})
    if structured.get("tests", "one") != {"kind": "structured"}:
        failures.append("structured_repository_roundtrip")
    if artifacts.get("tests", "one") != {"kind": "artifact"}:
        failures.append("artifact_repository_roundtrip")
    if not materials.get_asset("material-one") or not materials.load_library().get("assets"):
        failures.append("material_repository_roundtrip")
    try:
        structured.save("../escape", "one", {})
        failures.append("repository_path_escape_not_blocked")
    except ValueError:
        pass

    first = rule_candidates_from_updates(
        base.name,
        "evaluation-one",
        [{"path": "learning.successful_patterns", "value": "keep clear product framing", "risk_level": "low"}],
        {"evaluation_id": "evaluation-one"},
        "2026-07-11T00:00:00+00:00",
    )
    second = rule_candidates_from_updates(
        base.name,
        "evaluation-two",
        [{"path": "learning.successful_patterns", "value": "keep clear product framing", "risk_level": "low"}],
        {"evaluation_id": "evaluation-two"},
        "2026-07-11T00:01:00+00:00",
    )
    first_id = persist_rule_candidates(base, first, "evaluation-one")[0]
    second_id = persist_rule_candidates(base, second, "evaluation-two")[0]
    aggregated = SqliteRuleRepository().get(first_id)
    if first_id != second_id or aggregated.get("sample_size") != 2:
        failures.append("rule_evidence_not_aggregated")

old_disable = os.environ.pop("PRODUCT_CREATIVE_DISABLE_LLM", None)
old_enable = os.environ.get("PRODUCT_CREATIVE_ENABLE_LLM")
os.environ["PRODUCT_CREATIVE_ENABLE_LLM"] = "1"
configure_llm(FakeLlm())
decision = decide_intent("runtime-test-product", "请为产品生成一组图片", {"status": "ready_for_channel_run"}, "run_channel_review")
if decision.action != "resolve_image_intent" or decision.source != "llm":
    failures.append("structured_llm_decision")
if old_disable is not None:
    os.environ["PRODUCT_CREATIVE_DISABLE_LLM"] = old_disable
if old_enable is None:
    os.environ.pop("PRODUCT_CREATIVE_ENABLE_LLM", None)
else:
    os.environ["PRODUCT_CREATIVE_ENABLE_LLM"] = old_enable

configure_generation_provider_gateway(FakeGateway())
gateway_result = generation_provider_gateway().check_live_readiness("p", "fake", "image", "payload")
if not gateway_result.get("fake"):
    failures.append("provider_gateway_injection")

actions = action_runtime_registry()
definitions = workflow_definitions()
workflow_actions = {action for definition in definitions for action in definition.actions}
if set(actions) != set(ACTION_NAMES):
    failures.append("action_runtime_contract_drift")
if not workflow_actions.issubset(ACTION_NAMES):
    failures.append("workflow_action_contract_drift")
if sorted(WORKFLOW_ACTION_ENUM) != sorted(ACTION_NAMES):
    failures.append("schema_action_enum_drift")
apply_runtime = actions["apply_evolution_proposal"]
if not all((apply_runtime.plan_policy, apply_runtime.guard_policy, apply_runtime.missing_input_policy)):
    failures.append("action_extension_policies_missing")
if len(product_tool_handlers()) != 78 or len(CLI_COMMAND_HANDLERS) != 78:
    failures.append("unified_tool_cli_surface_drift")

report = {
    "success": not failures,
    "schema_version": "product_creative.ai_runtime_architecture_check.v1",
    "counts": {
        "actions": len(actions),
        "workflows": len(definitions),
        "tools": len(product_tool_handlers()),
        "cli_commands": len(CLI_COMMAND_HANDLERS),
        "aggregated_rule_sample_size": aggregated.get("sample_size"),
    },
    "decision": decision.model_dump(mode="json"),
    "failures": failures,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["success"] else 1)
'@

$python | python - $repoRoot
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
