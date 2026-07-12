$ErrorActionPreference = "Stop"

$plugin = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = "$((Get-Item $plugin).Parent.FullName);$env:PYTHONPATH"

@'
import ast
import json
from pathlib import Path

from product_creative.capabilities.registry import (
    action_descriptors,
    conversation_binders,
    execution_binders,
    intent_rules,
    recommendation_policies,
)

plugin = Path.cwd() / ".hermes" / "plugins" / "product_creative"
central = [
    plugin / "application" / "command_bus.py",
    plugin / "application" / "policy.py",
    plugin / "durable_workflow" / "engine.py",
    plugin / "runtime" / "action_surface.py",
    plugin / "runtime" / "conversation_arguments.py",
    plugin / "runtime" / "decision.py",
    plugin / "runtime" / "execution_arguments.py",
    plugin / "runtime" / "planning.py",
]
known = set(action_descriptors())
violations = []
legacy_modules = {
    "image_generation", "video_intent", "video_briefing", "m8_experience",
    "materials", "material_cards", "material_packs", "material_resolver",
    "inspiration", "generator", "briefs", "runs", "evaluator",
    "artifacts", "artifact_manifest", "artifact_feedback", "self_iteration",
    "store_workspace", "store_ingestion", "store_feedback", "store_evolution",
}

for module in sorted(legacy_modules):
    if (plugin / f"{module}.py").exists():
        violations.append(f"legacy root business module remains:{module}.py")
for path in (plugin / "capabilities").rglob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported = node.module.rsplit(".", 1)[-1]
            if imported in legacy_modules:
                violations.append(f"{path.relative_to(plugin)}:{node.lineno}:imports legacy {imported}")
            if {"infrastructure", "stores"} & set(node.module.split(".")):
                violations.append(f"{path.relative_to(plugin)}:{node.lineno}:capability imports storage adapter")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sqlite3" or ".infrastructure" in alias.name or ".stores" in alias.name:
                    violations.append(f"{path.relative_to(plugin)}:{node.lineno}:capability imports storage adapter")
    if path.name != "manifest_service.py":
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"glob", "rglob"}:
                if any(isinstance(arg, ast.Constant) and arg.value == "*.json" for arg in node.args):
                    violations.append(f"{path.relative_to(plugin)}:{node.lineno}:runtime artifact filesystem scan")

for path in central:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        values = [node.left, *node.comparators]
        literals = {item.value for item in values if isinstance(item, ast.Constant) and isinstance(item.value, str)}
        if literals & known:
            violations.append(f"{path.relative_to(plugin)}:{node.lineno}:central action comparison")

for folder in ("application", "brain", "domain", "runtime", "workflow", "durable_workflow"):
    for path in (plugin / folder).rglob("*.py"):
        text = path.read_text(encoding="utf-8-sig")
        if any(".jsonl" in line and ("read_text" in line or "open(" in line) for line in text.splitlines()):
            violations.append(f"{path.relative_to(plugin)}:JSONL runtime read")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if {"infrastructure", "stores"} & set(node.module.split(".")):
                    violations.append(f"{path.relative_to(plugin)}:{node.lineno}:core layer imports storage adapter")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "sqlite3" or ".infrastructure" in alias.name or ".stores" in alias.name:
                        violations.append(f"{path.relative_to(plugin)}:{node.lineno}:core layer imports storage adapter")

for rule in intent_rules():
    if rule.action not in known:
        violations.append(f"intent:{rule.action}:unknown action")
for name in set(execution_binders()) | set(conversation_binders()):
    if name not in known:
        violations.append(f"binder:{name}:unknown action")
if not recommendation_policies():
    violations.append("recommendation:no policies discovered")

result = {
    "success": not violations,
    "counts": {
        "actions": len(known),
        "intent_rules": len(intent_rules()),
        "execution_binders": len(execution_binders()),
        "conversation_binders": len(conversation_binders()),
        "recommendation_policies": len(recommendation_policies()),
    },
    "violations": violations,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["success"] else 1)
'@ | python -
$pythonExitCode = $LASTEXITCODE
if ($pythonExitCode -ne 0) {
    exit $pythonExitCode
}
