[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import argparse
import ast
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
plugin = repo_root / ".hermes" / "plugins" / "product_creative"
sys.path.insert(0, str(plugin.parent))

cli_path = plugin / "cli.py"
dispatch_path = plugin / "cli_dispatch.py"

cli_tree = ast.parse(cli_path.read_text(encoding="utf-8-sig"))
dispatch_tree = ast.parse(dispatch_path.read_text(encoding="utf-8-sig")) if dispatch_path.exists() else ast.Module(body=[], type_ignores=[])


def function_names(tree):
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def parser_names(tree):
    names = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.append(node.args[0].value)
    return names


def handler_keys(tree):
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "CLI_COMMAND_HANDLERS" for target in node.targets):
                value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "CLI_COMMAND_HANDLERS":
            value = node.value
        if not isinstance(value, ast.Dict):
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "CLI_COMMAND_NAMES" for target in node.targets
            ) and isinstance(node.value, (ast.Tuple, ast.List)):
                return [item.value for item in node.value.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
            continue
        keys = []
        for key in value.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.append(key.value)
        return keys
    return []


def product_command_uses_dispatch(tree):
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "product_command":
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "dispatch_product_command":
                return True
    return False


def command_compare_lines(tree):
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "command":
            lines.append(node.lineno)
    return lines


def imports_dispatch_adapter(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "cli_dispatch":
            continue
        names = {alias.name for alias in node.names}
        return "dispatch_product_command" in names
    return False


def imports_agent_turn(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.agent":
            continue
        names = {alias.name for alias in node.names}
        return "product_agent_turn" in names
    return False


def imports_tool_invoker(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module != "tools":
            continue
        return any(alias.name == "invoke_product_tool" for alias in node.names)
    return False


def imports_workflow_run_directly(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "workflow":
            continue
        names = {alias.name for alias in node.names}
        if "workflow_run" in names:
            return True
    return False


def workflow_run_handler_uses_agent(tree):
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "CLI_COMMAND_HANDLERS" for target in node.targets):
                value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "CLI_COMMAND_HANDLERS":
            value = node.value
        if not isinstance(value, ast.Dict):
            continue
        for key, handler in zip(value.keys, value.values):
            if not (isinstance(key, ast.Constant) and key.value == "workflow-run"):
                continue
            return any(
                isinstance(sub, ast.Name) and sub.id == "product_agent_turn"
                for sub in ast.walk(handler)
            )
    return False


from product_creative.cli import register_cli

runtime_parser = argparse.ArgumentParser()
register_cli(runtime_parser)
subparsers_action = next(
    action for action in runtime_parser._actions
    if isinstance(action, argparse._SubParsersAction)
)
parsers = list(subparsers_action.choices)
handlers = handler_keys(cli_tree)
duplicate_parsers = sorted({item for item in parsers if parsers.count(item) > 1})
duplicate_handlers = sorted({item for item in handlers if handlers.count(item) > 1})

failures = {
    "missing_cli_dispatch_module": [] if dispatch_path.exists() else [str(dispatch_path)],
    "cli_dispatch_missing_functions": sorted({"dispatch_product_command", "usage_text"} - function_names(dispatch_tree)),
    "cli_missing_dispatch_import": [] if imports_dispatch_adapter(cli_tree) else ["cli.py"],
    "cli_missing_tool_invoker_import": [] if imports_tool_invoker(cli_tree) else ["cli.py"],
    "cli_product_command_not_delegated": [] if product_command_uses_dispatch(cli_tree) else ["cli.product_command"],
    "cli_reintroduces_command_if_chain": command_compare_lines(cli_tree),
    "cli_imports_workflow_run_directly": ["cli.py"] if imports_workflow_run_directly(cli_tree) else [],
    "cli_workflow_run_not_using_unified_tool_adapter": [] if "workflow-run" in handlers and imports_tool_invoker(cli_tree) else ["cli.workflow-run"],
    "cli_missing_command_handlers": [] if handlers else ["cli.CLI_COMMAND_HANDLERS"],
    "cli_parsers_without_handlers": sorted(set(parsers) - set(handlers)),
    "cli_handlers_without_parsers": sorted(set(handlers) - set(parsers)),
    "duplicate_cli_parsers": duplicate_parsers,
    "duplicate_cli_handlers": duplicate_handlers,
}

report = {
    "success": not any(failures.values()),
    "schema_version": "product_creative.cli_boundary_check.v1",
    "counts": {
        "cli_parsers": len(parsers),
        "cli_command_handlers": len(handlers),
    },
    "failures": failures,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
'@

$raw = $python | python - $repoRoot
$rawText = ($raw | Out-String).Trim()
Write-Output $rawText

$report = $rawText | ConvertFrom-Json
if (-not $report.success) {
    exit 1
}
