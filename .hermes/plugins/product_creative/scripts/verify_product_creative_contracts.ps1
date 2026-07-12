[CmdletBinding()]
param(
    [switch]$ReportOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import argparse
import ast
import json
import re
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
plugin = repo_root / ".hermes" / "plugins" / "product_creative"


def parse_python(rel_path):
    return ast.parse((plugin / rel_path).read_text(encoding="utf-8-sig"))


def dict_from_assign(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return dict(ast.literal_eval(node.value))
                    except ValueError:
                        sys.path.insert(0, str(repo_root / ".hermes" / "plugins"))
                        from product_creative.contracts.actions import ACTION_CONTRACTS
                        return dict(ACTION_CONTRACTS) if name == "ACTION_CONTRACTS" else {}
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            try:
                return dict(ast.literal_eval(node.value))
            except ValueError:
                sys.path.insert(0, str(repo_root / ".hermes" / "plugins"))
                from product_creative.contracts.actions import ACTION_CONTRACTS
                return dict(ACTION_CONTRACTS) if name == "ACTION_CONTRACTS" else {}
    return {}


def action_contract_index(tree):
    contracts = dict_from_assign(tree, "ACTION_CONTRACTS")
    action_tools = {}
    metadata = {}
    for action, contract in contracts.items():
        action_tools[action] = contract.get("tool", "")
        metadata[action] = {
            "requires_user_input": bool(contract.get("requires_user_input")),
            "requires_explicit_confirmation": bool(contract.get("requires_explicit_confirmation")),
            "writes_product_workspace": bool(contract.get("writes_product_workspace")),
            "mutates_confirmed_product_brain": bool(contract.get("mutates_confirmed_product_brain")),
        }
    return set(contracts), action_tools, metadata


def auto_step_actions(tree):
    candidates = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "_auto_step_allowed":
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Set):
                values = []
                for elt in sub.elts:
                    if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
                        values = []
                        break
                    values.append(elt.value)
                if values:
                    candidates.append(values)
    return set(max(candidates, key=len)) if candidates else set()


def registered_runtime_actions():
    sys.path.insert(0, str(repo_root / ".hermes" / "plugins"))
    from product_creative.capabilities.registry import action_descriptors
    descriptors = action_descriptors()
    actions = set(descriptors)
    auto_actions = {name for name, descriptor in descriptors.items() if descriptor.runtime.auto_advance}
    return actions, auto_actions


def registered_tools(tree):
    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "register_tools":
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "tools" for target in stmt.targets):
                continue
            for item in stmt.value.elts:
                if not isinstance(item, ast.Tuple) or len(item.elts) < 3:
                    continue
                tool = item.elts[0].value if isinstance(item.elts[0], ast.Constant) else ""
                schema = item.elts[1].id if isinstance(item.elts[1], ast.Name) else ""
                handler = item.elts[2].id if isinstance(item.elts[2], ast.Name) else ""
                tools.append({"tool": tool, "schema": schema, "handler": handler})
    return tools


def catalog_tools(tree):
    tools = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if not any(isinstance(target, ast.Name) and target.id == "PRODUCT_TOOL_SPECS" for target in targets):
            continue
        if not isinstance(value, ast.List):
            continue
        for item in value.elts:
            if not isinstance(item, ast.Call) or len(item.args) < 3:
                continue
            tool = item.args[0].value if isinstance(item.args[0], ast.Constant) else ""
            schema = ""
            if isinstance(item.args[1], ast.Attribute):
                schema = item.args[1].attr
            elif isinstance(item.args[1], ast.Name):
                schema = item.args[1].id
            handler = item.args[2].value if isinstance(item.args[2], ast.Constant) else ""
            tools.append({"tool": tool, "schema": schema, "handler": handler})
    return tools


def schema_constants(*trees):
    schemas = set()
    for tree in trees:
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_SCHEMA"):
                    schemas.add(target.id)
    return schemas


def cli_contracts(tree):
    sys.path.insert(0, str(repo_root / ".hermes" / "plugins"))
    from product_creative.cli import register_cli

    runtime_parser = argparse.ArgumentParser()
    register_cli(runtime_parser)
    subparsers_action = next(
        action for action in runtime_parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    parsers = set(subparsers_action.choices)
    dispatch = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            parsers.add(node.args[0].value)
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "command":
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                    dispatch.add(comparator.value)
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "CLI_COMMAND_HANDLERS" for target in node.targets):
                value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "CLI_COMMAND_HANDLERS":
            value = node.value
        if isinstance(value, ast.Dict):
            for key in value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    dispatch.add(key.value)
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "CLI_COMMAND_NAMES" for target in node.targets
        ) and isinstance(node.value, (ast.Tuple, ast.List)):
            for item in node.value.elts:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    dispatch.add(item.value)
    return parsers, dispatch


def plugin_tools():
    tools = []
    in_block = False
    for line in (plugin / "plugin.yaml").read_text(encoding="utf-8").splitlines():
        if line.strip() == "provides_tools:":
            in_block = True
            continue
        if not in_block:
            continue
        match = re.match(r"\s*-\s*(\S+)", line)
        if match:
            tools.append(match.group(1))
        elif line and not line.startswith(" "):
            break
    return set(tools)


def action_enum_derived_from_contracts(tree):
    imports_action_names = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "contracts.actions"
        and any(alias.name == "ACTION_NAMES" for alias in node.names)
        for node in tree.body
    )
    assigns_sorted_action_names = False
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "WORKFLOW_ACTION_ENUM" for target in node.targets):
            continue
        value = node.value
        assigns_sorted_action_names = (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "sorted"
            and len(value.args) == 1
            and isinstance(value.args[0], ast.Name)
            and value.args[0].id == "ACTION_NAMES"
        )
    return imports_action_names and assigns_sorted_action_names


workflow_tree = parse_python("workflow.py")
execution_tree = parse_python("runtime/execution.py")
contracts_tree = parse_python("contracts/actions.py")
tools_tree = parse_python("tools.py")
tool_catalog_tree = parse_python("tool_catalog.py")
schemas_tree = parse_python("schemas.py")
capability_schema_trees = [parse_python(f"capabilities/{name}/schemas.py") for name in (
    "content", "image", "inspiration", "learning", "material", "product", "recovery", "review", "video"
)]
schema_runtime_tree = parse_python("capabilities/product/schemas.py")
cli_tree = parse_python("cli.py")

workflow_actions, action_tools, metadata = action_contract_index(contracts_tree)
runtime_actions, auto_actions = registered_runtime_actions()
tools = registered_tools(tools_tree) or catalog_tools(tool_catalog_tree)
if not tools:
    sys.path.insert(0, str(repo_root / ".hermes" / "plugins"))
    from product_creative import schemas as runtime_schemas
    from product_creative.capabilities.registry import command_descriptors
    schema_names = {
        id(value): name
        for name, value in vars(runtime_schemas).items()
        if name.endswith("_SCHEMA")
    }
    tools = [
        {
            "tool": descriptor.name,
            "schema": schema_names.get(id(descriptor.schema), ""),
            "handler": descriptor.compatibility_handler_name,
        }
        for descriptor in command_descriptors().values()
    ]
tool_names = {item["tool"] for item in tools}
tool_schemas = {item["schema"] for item in tools}
schemas = schema_constants(schemas_tree, *capability_schema_trees)
cli_parsers, cli_dispatch = cli_contracts(cli_tree)
provided_tools = plugin_tools()

failures = {
    "missing_action_contracts": [] if workflow_actions else ["contracts/actions.py: ACTION_CONTRACTS"],
    "workflow_actions_without_tool_mapping": sorted(workflow_actions - set(action_tools)),
    "tool_mappings_without_workflow_action": sorted(set(action_tools) - workflow_actions),
    "workflow_actions_without_metadata": sorted(workflow_actions - set(metadata)),
    "metadata_without_workflow_action": sorted(set(metadata) - workflow_actions),
    "mapped_tools_not_registered": sorted(set(action_tools.values()) - tool_names),
    "registered_tools_missing_from_plugin_yaml": sorted(tool_names - provided_tools),
    "plugin_yaml_tools_not_registered": sorted(provided_tools - tool_names),
    "registered_schema_consts_missing_definition": sorted(tool_schemas - schemas),
    "schema_consts_not_registered": sorted(schemas - tool_schemas),
    "cli_parsers_without_dispatch": sorted(cli_parsers - cli_dispatch),
    "cli_dispatch_without_parser": sorted(cli_dispatch - cli_parsers),
    "workflow_action_enum_not_derived_from_contracts": (
        [] if action_enum_derived_from_contracts(schema_runtime_tree)
        else ["schema_runtime.py: WORKFLOW_ACTION_ENUM"]
    ),
    "workflow_actions_without_runtime_handler": sorted(workflow_actions - runtime_actions),
    "runtime_handlers_without_workflow_action": sorted(runtime_actions - workflow_actions),
}

warnings = {
    "auto_actions_with_metadata_requires_user_input": sorted(
        action for action in auto_actions if metadata.get(action, {}).get("requires_user_input")
    ),
    "auto_actions_with_metadata_requires_explicit_confirmation": sorted(
        action for action in auto_actions if metadata.get(action, {}).get("requires_explicit_confirmation")
    ),
    "auto_actions_mutating_confirmed_product_brain": sorted(
        action for action in auto_actions if metadata.get(action, {}).get("mutates_confirmed_product_brain")
    ),
}

action_rows = []
tool_index = {item["tool"]: item for item in tools}
for action in sorted(workflow_actions):
    tool = action_tools.get(action, "")
    action_rows.append(
        {
            "action": action,
            "tool": tool,
            "schema": tool_index.get(tool, {}).get("schema", ""),
            "handler": tool_index.get(tool, {}).get("handler", ""),
            "requires_user_input": metadata.get(action, {}).get("requires_user_input"),
            "requires_explicit_confirmation": metadata.get(action, {}).get("requires_explicit_confirmation"),
            "writes_product_workspace": metadata.get(action, {}).get("writes_product_workspace"),
            "mutates_confirmed_product_brain": metadata.get(action, {}).get("mutates_confirmed_product_brain"),
            "auto_step_candidate": action in auto_actions,
        }
    )

success = not any(failures.values())
report = {
    "success": success,
    "schema_version": "product_creative.contract_invariants.v1",
    "counts": {
        "workflow_actions": len(workflow_actions),
        "workflow_action_tool_mappings": len(action_tools),
        "action_metadata_entries": len(metadata),
        "auto_step_candidates": len(auto_actions),
        "runtime_action_handlers": len(runtime_actions),
        "registered_tools": len(tools),
        "schema_constants": len(schemas),
        "cli_parsers": len(cli_parsers),
        "cli_dispatch_branches": len(cli_dispatch),
        "plugin_provides_tools": len(provided_tools),
    },
    "failures": failures,
    "warnings": warnings,
    "actions": action_rows,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
'@

$raw = $python | python - $repoRoot
$rawText = ($raw | Out-String).Trim()
Write-Output $rawText

$report = $rawText | ConvertFrom-Json
if (-not $ReportOnly -and -not $report.success) {
    exit 1
}
