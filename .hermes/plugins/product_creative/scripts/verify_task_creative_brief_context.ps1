[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$python = "C:\Users\1\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"

$test = @'
import json
import os
import sys
from pathlib import Path

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / ".hermes" / "plugins"))

from product_creative.common import read_json
from product_creative.capabilities.content.llm_service import configure_llm as configure_generator_llm
from product_creative.infrastructure.sqlite.repositories import SqliteWorkflowRepository
from product_creative.runtime.agent import product_agent_turn
from product_creative.runtime.guard import action_guard
from product_creative.runtime.decision_service import configure_llm as configure_decision_llm
from product_creative.capabilities.product.ingestion_service import ingest_product
from product_creative.capabilities.product.workspace_service import create_product


class Response:
    def __init__(self, parsed):
        self.parsed = parsed
        self.text = json.dumps(parsed, ensure_ascii=False)
        self.provider = "fixture"
        self.model = "fixture"
        self.agent_id = ""
        self.usage = None
        self.content_type = "application/json"


class FakeLlm:
    def __init__(self):
        self.generation_instructions = ""

    def complete_structured(self, **kwargs):
        if kwargs.get("purpose") == "product_creative.intent_decision":
            return Response({
                "action": "run_channel_review",
                "goal": "妇女节期间，每一种女性身份都值得被看见",
                "modality": "text",
                "target": "xiaohongshu-seeding-note",
                "constraints": ["包含成年孕妇", "不展示产品使用", "不作孕期或医疗承诺"],
                "requested_outputs": ["小红书文案"],
                "confidence": 0.98,
                "rationale": "channel content request",
                "source": "llm",
            })
        self.generation_instructions = kwargs.get("instructions") or ""
        return Response({
            "variants": [{
                "variant": 1,
                "style": "温柔群像",
                "title_options": ["每一种女性身份，都值得被看见", "妇女节，看见她的每一种角色"],
                "opening_hook": "她是准妈妈，也是她自己。",
                "body": "妇女节，看见每一种女性身份。成年孕妇只是群像中的一员；产品仅作为桌面礼物出现，不展示使用。",
                "selling_point_mapping": ["周十五蜂蜜露", "10mL×12"],
                "tone": "尊重、克制、温柔",
                "hashtags": ["妇女节", "看见她"],
                "avoid_claims": ["不作医疗承诺", "不作孕期适用或安全承诺"],
                "generation_notes": {
                    "basis": "Product State evidence and turn-scoped creative brief.",
                    "preference": "Keep product use off screen.",
                    "requires_human_review": True,
                },
            }]
        })


product_id = "task-brief-context-check"
brief = (
    "请为妇女节生成小红书文案，主题是每一种女性身份都值得被看见；"
    "包含成年孕妇，但不展示产品使用，不作孕期或医疗承诺。"
)
create_product(product_id, "Task Brief Context Check")
ingest_product(product_id, "产品名：Task Brief Context Check。规格：10mL×12。")

fake = FakeLlm()
configure_decision_llm(fake)
configure_generator_llm(fake)
old_enable = os.environ.get("PRODUCT_CREATIVE_ENABLE_LLM")
old_disable = os.environ.pop("PRODUCT_CREATIVE_DISABLE_LLM", None)
os.environ["PRODUCT_CREATIVE_ENABLE_LLM"] = "1"
try:
    result = product_agent_turn(
        product_id=product_id,
        message=brief,
        target="xiaohongshu-seeding-note",
        variants=1,
        max_steps=1,
    )
finally:
    if old_enable is None:
        os.environ.pop("PRODUCT_CREATIVE_ENABLE_LLM", None)
    else:
        os.environ["PRODUCT_CREATIVE_ENABLE_LLM"] = old_enable
    if old_disable is not None:
        os.environ["PRODUCT_CREATIVE_DISABLE_LLM"] = old_disable

artifact_rel = result["created_artifacts"]["channel_content"]["path"]
artifact = read_json(repo / ".hermes" / "product_creative" / "products" / product_id / artifact_rel, {})
workflow_id = result["workflow_instance"]["workflow_id"]
workflow = SqliteWorkflowRepository().get(workflow_id)
step_brief = workflow.steps[0].args.get("creative_brief") if workflow and workflow.steps else {}

checks = {
    "intent_is_llm": result["interpreted_intent"]["source"] == "llm",
    "executed": result["execution_contract"]["executed"] is True,
    "workflow_has_brief": step_brief.get("raw_message") == brief,
    "prompt_has_brief": brief in fake.generation_instructions,
    "artifact_has_brief": artifact.get("creative_brief", {}).get("raw_message") == brief,
    "artifact_uses_llm": artifact.get("generation_method") == "llm",
    "brain_not_mutated": result["execution_contract"]["mutates_product_brain"] is False,
    "post_generation_state_can_regenerate": action_guard(product_id, "run_channel_review")["allowed"] is True,
}
report = {"success": all(checks.values()), "checks": checks, "workflow_id": workflow_id, "artifact": str(artifact_rel)}
print(json.dumps(report, ensure_ascii=False, indent=2))
if not report["success"]:
    raise SystemExit(1)
'@

$test | & $python - $repoRoot
exit $LASTEXITCODE
