[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..\..\..\..")).Path

$python = @'
import ast
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
plugin = repo_root / ".hermes" / "plugins" / "product_creative"

tools_path = plugin / "tools.py"
handlers_path = plugin / "tool_handlers.py"
catalog_path = plugin / "tool_catalog.py"

tools_tree = ast.parse(tools_path.read_text(encoding="utf-8-sig"))
handlers_tree = ast.parse(handlers_path.read_text(encoding="utf-8-sig")) if handlers_path.exists() else ast.Module(body=[], type_ignores=[])
catalog_tree = ast.parse(catalog_path.read_text(encoding="utf-8-sig")) if catalog_path.exists() else ast.Module(body=[], type_ignores=[])


def product_tool_specs(tree):
    specs = []
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
            schema = item.args[1].attr if isinstance(item.args[1], ast.Attribute) else ""
            handler = item.args[2].value if isinstance(item.args[2], ast.Constant) else ""
            specs.append({"tool": tool, "schema": schema, "handler": handler})
    return specs


def function_names(tree):
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def imports_tool_catalog(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "tool_catalog":
            continue
        names = {alias.name for alias in node.names}
        return "PRODUCT_TOOL_SPECS" in names
    return False


def imports_schemas_directly(tree):
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "schemas":
            return True
        if isinstance(node, ast.ImportFrom) and node.module == ".schemas":
            return True
    return False


def register_uses_catalog(tree):
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "register_tools":
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id == "PRODUCT_TOOL_SPECS":
                return True
    return False


specs = product_tool_specs(catalog_tree)
handler_names = function_names(handlers_tree)
if not specs:
    sys.path.insert(0, str(repo_root / ".hermes" / "plugins"))
    from product_creative import schemas as runtime_schemas
    from product_creative.capabilities.registry import command_descriptors
    schema_names = {id(value): name for name, value in vars(runtime_schemas).items() if name.endswith("_SCHEMA")}
    descriptors = command_descriptors()
    specs = [
        {"tool": item.name, "schema": schema_names.get(id(item.schema), ""), "handler": item.compatibility_handler_name}
        for item in descriptors.values()
    ]
    handler_names = {item.compatibility_handler_name for item in descriptors.values()}
duplicate_tools = sorted({item["tool"] for item in specs if [s["tool"] for s in specs].count(item["tool"]) > 1})
missing_handlers = sorted(item["handler"] for item in specs if item["handler"] not in handler_names)
missing_schema_refs = sorted(item["tool"] for item in specs if not item["schema"])

failures = {
    "missing_tool_catalog": [] if catalog_path.exists() else [str(catalog_path)],
    "missing_tool_handlers": [] if handlers_path.exists() else [str(handlers_path)],
    "empty_tool_catalog": [] if specs else ["tool_catalog.PRODUCT_TOOL_SPECS"],
    "duplicate_tool_specs": duplicate_tools,
    "tool_specs_missing_handlers": missing_handlers,
    "tool_specs_missing_schema_refs": missing_schema_refs,
    "tools_missing_command_registry_import": [] if any(isinstance(node, ast.ImportFrom) and node.module == "capabilities.registry" for node in handlers_tree.body) else ["tool_handlers.py"],
    "tools_register_not_using_registry": [] if any(isinstance(node, ast.Name) and node.id == "command_descriptors" for node in ast.walk(handlers_tree)) else ["tool_handlers.register_tools"],
    "tools_imports_schemas_directly": ["tool_handlers.py"] if imports_schemas_directly(handlers_tree) else [],
}

report = {
    "success": not any(failures.values()),
    "schema_version": "product_creative.tool_boundary_check.v1",
    "counts": {
        "tool_specs": len(specs),
        "tool_handlers": len([name for name in handler_names if name.startswith("_handle_product_")]),
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
