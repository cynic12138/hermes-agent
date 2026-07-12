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

providers_path = plugin / "providers.py"
adapters_path = plugin / "provider_adapters.py"
contracts_path = plugin / "provider_contracts.py"
payloads_path = plugin / "provider_payloads.py"
generation_path = plugin / "provider_generation.py"
paths_path = plugin / "provider_paths.py"
validation_path = plugin / "provider_validation.py"
config_path = plugin / "provider_config.py"
readiness_path = plugin / "provider_readiness.py"
response_path = plugin / "provider_response.py"
video_tasks_path = plugin / "provider_video_tasks.py"
registry_path = plugin / "provider_registry.py"
io_path = plugin / "provider_io.py"
http_path = plugin / "provider_http.py"

providers_tree = ast.parse(providers_path.read_text(encoding="utf-8-sig"))
adapters_tree = ast.parse(adapters_path.read_text(encoding="utf-8-sig")) if adapters_path.exists() else ast.Module(body=[], type_ignores=[])
contracts_tree = ast.parse(contracts_path.read_text(encoding="utf-8-sig")) if contracts_path.exists() else ast.Module(body=[], type_ignores=[])
payloads_tree = ast.parse(payloads_path.read_text(encoding="utf-8-sig")) if payloads_path.exists() else ast.Module(body=[], type_ignores=[])
generation_tree = ast.parse(generation_path.read_text(encoding="utf-8-sig")) if generation_path.exists() else ast.Module(body=[], type_ignores=[])
paths_tree = ast.parse(paths_path.read_text(encoding="utf-8-sig")) if paths_path.exists() else ast.Module(body=[], type_ignores=[])
validation_tree = ast.parse(validation_path.read_text(encoding="utf-8-sig")) if validation_path.exists() else ast.Module(body=[], type_ignores=[])
config_tree = ast.parse(config_path.read_text(encoding="utf-8-sig")) if config_path.exists() else ast.Module(body=[], type_ignores=[])
readiness_tree = ast.parse(readiness_path.read_text(encoding="utf-8-sig")) if readiness_path.exists() else ast.Module(body=[], type_ignores=[])
response_tree = ast.parse(response_path.read_text(encoding="utf-8-sig")) if response_path.exists() else ast.Module(body=[], type_ignores=[])
video_tasks_tree = ast.parse(video_tasks_path.read_text(encoding="utf-8-sig")) if video_tasks_path.exists() else ast.Module(body=[], type_ignores=[])
registry_tree = ast.parse(registry_path.read_text(encoding="utf-8-sig")) if registry_path.exists() else ast.Module(body=[], type_ignores=[])
io_tree = ast.parse(io_path.read_text(encoding="utf-8-sig")) if io_path.exists() else ast.Module(body=[], type_ignores=[])
http_tree = ast.parse(http_path.read_text(encoding="utf-8-sig")) if http_path.exists() else ast.Module(body=[], type_ignores=[])

CONTRACT_CONSTANTS = {
    "GENERATION_JOB_SCHEMA_VERSION",
    "GENERATION_RESULT_SCHEMA_VERSION",
    "LIVE_READINESS_SCHEMA_VERSION",
    "PROVIDER_PAYLOAD_SCHEMA_VERSION",
    "PROVIDER_VALIDATION_SCHEMA_VERSION",
    "VIDEO_EXECUTION_POLICY_SCHEMA_VERSION",
    "VIDEO_REFERENCE_READINESS_SCHEMA_VERSION",
    "VIDEO_TASK_SCHEMA_VERSION",
    "VIDEO_TASK_STATUS_SCHEMA_VERSION",
}

ADAPTER_FUNCTIONS = {
    "adapt_image_prompt",
    "adapt_video_prompt",
    "duration_seconds",
    "image_request",
    "is_data_url",
    "is_http_url",
    "video_request",
}

PROVIDERS_REQUIRED_ADAPTER_SYMBOLS = {
    "PROMPT_ADAPTER_SCHEMA_VERSION",
    "VIDEO_PROMPT_ADAPTER_SCHEMA_VERSION",
}

READINESS_REQUIRED_ADAPTER_SYMBOLS = {
    "is_data_url",
    "is_http_url",
}

PROVIDER_LOCAL_ADAPTER_FUNCTIONS = {
    "_adapt_image_prompt",
    "_adapt_video_prompt",
    "_ark_video_content",
    "_ark_video_request_draft",
    "_asset_local_reference",
    "_duration_seconds",
    "_image_request",
    "_is_data_url",
    "_is_http_url",
    "_video_reference_url",
    "_video_request",
}

PATH_FUNCTIONS = {
    "resolve_brief_path",
    "resolve_payload_path",
    "resolve_video_policy_path",
    "resolve_video_task_path",
}

PROVIDERS_REQUIRED_PATH_SYMBOLS = set()

PROVIDER_LOCAL_PATH_FUNCTIONS = {
    "_resolve_brief_path",
    "_resolve_payload_path",
    "_resolve_video_policy_path",
    "_resolve_video_task_path",
}

VALIDATION_FUNCTIONS = {
    "validate_payload_doc",
    "validate_provider_payload",
}

PROVIDERS_REQUIRED_VALIDATION_SYMBOLS = {
    "validate_provider_payload",
}

PROVIDER_LOCAL_VALIDATION_FUNCTIONS = {
    "_validate_payload_doc",
    "_validation_markdown",
    "validate_provider_payload",
}

CONFIG_FUNCTIONS = {
    "provider_api_key",
    "provider_endpoint",
    "provider_model",
}

PROVIDERS_REQUIRED_CONFIG_SYMBOLS = set()

PROVIDER_LOCAL_CONFIG_FUNCTIONS = {
    "_provider_api_key",
    "_provider_endpoint",
    "_provider_model",
}

READINESS_FUNCTIONS = {
    "check_live_readiness",
    "check_video_reference_readiness",
    "create_video_execution_policy",
}

PROVIDER_LOCAL_READINESS_FUNCTIONS = {
    "_readiness_markdown",
    "_video_execution_policy_markdown",
    "_video_reference_readiness_markdown",
    "check_live_readiness",
    "check_video_reference_readiness",
    "create_video_execution_policy",
}

RESPONSE_FUNCTIONS = {
    "find_first_key",
    "find_urls",
}

PROVIDERS_REQUIRED_RESPONSE_SYMBOLS = set()

PROVIDER_LOCAL_RESPONSE_FUNCTIONS = {
    "_find_first_key",
    "_find_urls",
}

VIDEO_TASK_FUNCTIONS = {
    "check_video_task_status",
    "import_video_result",
    "write_live_video_task",
}

PROVIDERS_REQUIRED_VIDEO_TASK_SYMBOLS = {
    "check_video_task_status",
    "import_video_result",
}

PROVIDER_LOCAL_VIDEO_TASK_FUNCTIONS = {
    "_generated_video_markdown",
    "_normalize_video_task_status",
    "_provider_task_status",
    "_status_endpoint",
    "_video_task_markdown",
    "_video_task_status_markdown",
    "_write_generated_video_result",
    "_write_live_video_task",
    "_write_video_task_files",
    "check_video_task_status",
    "import_video_result",
}

PAYLOAD_FUNCTIONS = {
    "prepare_provider_payload",
}

PROVIDER_LOCAL_PAYLOAD_FUNCTIONS = {
    "_payload_markdown",
    "prepare_provider_payload",
}

GENERATION_FUNCTIONS = {
    "create_generation_job",
}

PROVIDER_LOCAL_GENERATION_FUNCTIONS = {
    "_build_provider_request",
    "_job_markdown",
    "_live_image_body",
    "_result_markdown",
    "_write_live_image_result",
    "_write_mock_result",
    "create_generation_job",
}

REGISTRY_FUNCTIONS = {
    "registry_path",
    "load_registry",
    "provider_entry",
    "env_value",
    "list_providers",
}

PROVIDER_LOCAL_REGISTRY_FUNCTIONS = {
    "_registry_path",
    "_load_registry",
    "_provider_entry",
    "_env_value",
    "list_providers",
}

IO_FUNCTIONS = {
    "download_image_asset",
    "download_video_asset",
}

PROVIDERS_REQUIRED_IO_SYMBOLS = set()

HTTP_FUNCTIONS = {
    "get_json",
    "post_json",
}

PROVIDERS_REQUIRED_HTTP_SYMBOLS = set()

PROVIDER_LOCAL_IO_FUNCTIONS = {
    "_download_image",
    "_download_video",
    "_download_video_with_curl",
    "_image_extension",
    "_video_extension",
}

PROVIDER_LOCAL_HTTP_FUNCTIONS = {
    "_get_json",
    "_post_json",
}


def function_names(tree):
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def assigned_names(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def import_names_from(tree, module_name):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != module_name:
            continue
        imported.update(alias.name for alias in node.names)
    return imported


def imported_modules(tree):
    modules = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


registry_names = function_names(registry_tree)
adapter_names = function_names(adapters_tree)
contracts_names = assigned_names(contracts_tree)
payload_names = function_names(payloads_tree)
generation_names = function_names(generation_tree)
paths_names = function_names(paths_tree)
validation_names = function_names(validation_tree)
config_names = function_names(config_tree)
readiness_names = function_names(readiness_tree)
response_names = function_names(response_tree)
video_task_names = function_names(video_tasks_tree)
io_names = function_names(io_tree)
http_names = function_names(http_tree)
providers_names = function_names(providers_tree)
providers_assigns = assigned_names(providers_tree)
provider_adapter_imports = import_names_from(providers_tree, "provider_adapters")
provider_contract_imports = import_names_from(providers_tree, "provider_contracts")
provider_payload_imports = import_names_from(providers_tree, "provider_payloads")
provider_generation_imports = import_names_from(providers_tree, "provider_generation")
provider_path_imports = import_names_from(providers_tree, "provider_paths")
provider_validation_imports = import_names_from(providers_tree, "provider_validation")
provider_config_imports = import_names_from(providers_tree, "provider_config")
provider_readiness_imports = import_names_from(providers_tree, "provider_readiness")
provider_response_imports = import_names_from(providers_tree, "provider_response")
provider_video_task_imports = import_names_from(providers_tree, "provider_video_tasks")
provider_registry_imports = import_names_from(providers_tree, "provider_registry")
provider_io_imports = import_names_from(providers_tree, "provider_io")
provider_http_imports = import_names_from(providers_tree, "provider_http")
providers_imported_modules = imported_modules(providers_tree)

failures = {
    "missing_provider_adapters": [] if adapters_path.exists() else [str(adapters_path)],
    "missing_provider_contracts": [] if contracts_path.exists() else [str(contracts_path)],
    "missing_provider_payloads": [] if payloads_path.exists() else [str(payloads_path)],
    "missing_provider_generation": [] if generation_path.exists() else [str(generation_path)],
    "missing_provider_paths": [] if paths_path.exists() else [str(paths_path)],
    "missing_provider_validation": [] if validation_path.exists() else [str(validation_path)],
    "missing_provider_config": [] if config_path.exists() else [str(config_path)],
    "missing_provider_readiness": [] if readiness_path.exists() else [str(readiness_path)],
    "missing_provider_response": [] if response_path.exists() else [str(response_path)],
    "missing_provider_video_tasks": [] if video_tasks_path.exists() else [str(video_tasks_path)],
    "missing_provider_registry": [] if registry_path.exists() else [str(registry_path)],
    "missing_provider_io": [] if io_path.exists() else [str(io_path)],
    "missing_provider_http": [] if http_path.exists() else [str(http_path)],
    "provider_adapters_missing_functions": sorted(ADAPTER_FUNCTIONS - adapter_names),
    "provider_contracts_missing_constants": sorted(CONTRACT_CONSTANTS - contracts_names),
    "provider_payloads_missing_functions": sorted(PAYLOAD_FUNCTIONS - payload_names),
    "provider_payloads_missing_contract_imports": sorted({"PROVIDER_PAYLOAD_SCHEMA_VERSION"} - import_names_from(payloads_tree, "provider_contracts")),
    "provider_payloads_missing_adapter_imports": sorted({"image_request", "video_request"} - import_names_from(payloads_tree, "provider_adapters")),
    "provider_payloads_missing_path_imports": sorted({"resolve_brief_path"} - import_names_from(payloads_tree, "provider_paths")),
    "provider_payloads_missing_registry_imports": sorted({"provider_entry"} - import_names_from(payloads_tree, "provider_registry")),
    "provider_generation_missing_functions": sorted(GENERATION_FUNCTIONS - generation_names),
    "provider_generation_missing_contract_imports": sorted({"GENERATION_JOB_SCHEMA_VERSION", "GENERATION_RESULT_SCHEMA_VERSION"} - import_names_from(generation_tree, "provider_contracts")),
    "provider_generation_missing_config_imports": sorted({"provider_api_key", "provider_endpoint", "provider_model"} - import_names_from(generation_tree, "provider_config")),
    "provider_generation_missing_http_imports": sorted({"post_json"} - import_names_from(generation_tree, "provider_http")),
    "provider_generation_missing_io_imports": sorted({"download_image_asset"} - import_names_from(generation_tree, "provider_io")),
    "provider_generation_missing_path_imports": sorted({"resolve_payload_path", "resolve_video_policy_path"} - import_names_from(generation_tree, "provider_paths")),
    "provider_generation_missing_readiness_imports": sorted({"check_live_readiness"} - import_names_from(generation_tree, "provider_readiness")),
    "provider_generation_missing_registry_imports": sorted({"provider_entry"} - import_names_from(generation_tree, "provider_registry")),
    "provider_generation_missing_response_imports": sorted({"find_urls"} - import_names_from(generation_tree, "provider_response")),
    "provider_generation_missing_validation_imports": sorted({"validate_payload_doc"} - import_names_from(generation_tree, "provider_validation")),
    "provider_generation_missing_video_task_imports": sorted({"write_live_video_task"} - import_names_from(generation_tree, "provider_video_tasks")),
    "provider_paths_missing_functions": sorted(PATH_FUNCTIONS - paths_names),
    "provider_validation_missing_functions": sorted(VALIDATION_FUNCTIONS - validation_names),
    "provider_validation_missing_contract_imports": sorted({"PROVIDER_PAYLOAD_SCHEMA_VERSION", "PROVIDER_VALIDATION_SCHEMA_VERSION"} - import_names_from(validation_tree, "provider_contracts")),
    "provider_validation_missing_path_import": sorted({"resolve_payload_path"} - import_names_from(validation_tree, "provider_paths")),
    "provider_config_missing_functions": sorted(CONFIG_FUNCTIONS - config_names),
    "provider_readiness_missing_functions": sorted(READINESS_FUNCTIONS - readiness_names),
    "provider_readiness_missing_contract_imports": sorted({"LIVE_READINESS_SCHEMA_VERSION", "VIDEO_EXECUTION_POLICY_SCHEMA_VERSION", "VIDEO_REFERENCE_READINESS_SCHEMA_VERSION"} - import_names_from(readiness_tree, "provider_contracts")),
    "provider_readiness_missing_path_import": sorted({"resolve_payload_path"} - import_names_from(readiness_tree, "provider_paths")),
    "provider_readiness_missing_validation_import": sorted({"validate_payload_doc"} - import_names_from(readiness_tree, "provider_validation")),
    "provider_readiness_missing_config_imports": sorted({"provider_endpoint", "provider_model"} - import_names_from(readiness_tree, "provider_config")),
    "provider_readiness_missing_registry_imports": sorted({"env_value", "provider_entry"} - import_names_from(readiness_tree, "provider_registry")),
    "provider_readiness_missing_adapter_imports": sorted(READINESS_REQUIRED_ADAPTER_SYMBOLS - import_names_from(readiness_tree, "provider_adapters")),
    "provider_response_missing_functions": sorted(RESPONSE_FUNCTIONS - response_names),
    "provider_video_tasks_missing_functions": sorted(VIDEO_TASK_FUNCTIONS - video_task_names),
    "provider_video_tasks_missing_contract_imports": sorted({"GENERATION_RESULT_SCHEMA_VERSION", "VIDEO_TASK_SCHEMA_VERSION", "VIDEO_TASK_STATUS_SCHEMA_VERSION"} - import_names_from(video_tasks_tree, "provider_contracts")),
    "provider_video_tasks_missing_response_imports": sorted(RESPONSE_FUNCTIONS - import_names_from(video_tasks_tree, "provider_response")),
    "provider_video_tasks_missing_config_imports": sorted({"provider_api_key", "provider_endpoint"} - import_names_from(video_tasks_tree, "provider_config")),
    "provider_video_tasks_missing_http_imports": sorted({"get_json", "post_json"} - import_names_from(video_tasks_tree, "provider_http")),
    "provider_video_tasks_missing_io_imports": sorted({"download_video_asset"} - import_names_from(video_tasks_tree, "provider_io")),
    "provider_video_tasks_missing_path_imports": sorted({"resolve_video_task_path"} - import_names_from(video_tasks_tree, "provider_paths")),
    "provider_video_tasks_missing_registry_imports": sorted({"provider_entry"} - import_names_from(video_tasks_tree, "provider_registry")),
    "provider_video_tasks_missing_adapter_imports": sorted({"is_http_url"} - import_names_from(video_tasks_tree, "provider_adapters")),
    "provider_registry_missing_functions": sorted(REGISTRY_FUNCTIONS - registry_names),
    "provider_io_missing_functions": sorted(IO_FUNCTIONS - io_names),
    "provider_http_missing_functions": sorted(HTTP_FUNCTIONS - http_names),
    "providers_missing_adapter_imports": sorted(PROVIDERS_REQUIRED_ADAPTER_SYMBOLS - provider_adapter_imports),
    "providers_missing_contract_imports": sorted(CONTRACT_CONSTANTS - provider_contract_imports),
    "providers_missing_payload_imports": sorted(PAYLOAD_FUNCTIONS - provider_payload_imports),
    "providers_missing_generation_imports": sorted(GENERATION_FUNCTIONS - provider_generation_imports),
    "providers_missing_path_imports": sorted(PROVIDERS_REQUIRED_PATH_SYMBOLS - provider_path_imports),
    "providers_missing_validation_imports": sorted(PROVIDERS_REQUIRED_VALIDATION_SYMBOLS - provider_validation_imports),
    "providers_missing_config_imports": sorted(PROVIDERS_REQUIRED_CONFIG_SYMBOLS - provider_config_imports),
    "providers_missing_readiness_imports": sorted(READINESS_FUNCTIONS - provider_readiness_imports),
    "providers_missing_response_imports": sorted(PROVIDERS_REQUIRED_RESPONSE_SYMBOLS - provider_response_imports),
    "providers_missing_video_task_imports": sorted(PROVIDERS_REQUIRED_VIDEO_TASK_SYMBOLS - provider_video_task_imports),
    "providers_redefines_contract_constants": sorted(CONTRACT_CONSTANTS & providers_assigns),
    "providers_missing_registry_imports": sorted({"list_providers"} - provider_registry_imports),
    "providers_missing_io_imports": sorted(PROVIDERS_REQUIRED_IO_SYMBOLS - provider_io_imports),
    "providers_missing_http_imports": sorted(PROVIDERS_REQUIRED_HTTP_SYMBOLS - provider_http_imports),
    "providers_redefines_adapter_functions": sorted(PROVIDER_LOCAL_ADAPTER_FUNCTIONS & providers_names),
    "providers_redefines_payload_functions": sorted(PROVIDER_LOCAL_PAYLOAD_FUNCTIONS & providers_names),
    "providers_redefines_generation_functions": sorted(PROVIDER_LOCAL_GENERATION_FUNCTIONS & providers_names),
    "providers_redefines_path_functions": sorted(PROVIDER_LOCAL_PATH_FUNCTIONS & providers_names),
    "providers_redefines_validation_functions": sorted(PROVIDER_LOCAL_VALIDATION_FUNCTIONS & providers_names),
    "providers_redefines_config_functions": sorted(PROVIDER_LOCAL_CONFIG_FUNCTIONS & providers_names),
    "providers_redefines_readiness_functions": sorted(PROVIDER_LOCAL_READINESS_FUNCTIONS & providers_names),
    "providers_redefines_response_functions": sorted(PROVIDER_LOCAL_RESPONSE_FUNCTIONS & providers_names),
    "providers_redefines_video_task_functions": sorted(PROVIDER_LOCAL_VIDEO_TASK_FUNCTIONS & providers_names),
    "providers_redefines_registry_functions": sorted(PROVIDER_LOCAL_REGISTRY_FUNCTIONS & providers_names),
    "providers_redefines_io_functions": sorted(PROVIDER_LOCAL_IO_FUNCTIONS & providers_names),
    "providers_redefines_http_functions": sorted(PROVIDER_LOCAL_HTTP_FUNCTIONS & providers_names),
    "providers_keeps_video_task_http_imports": sorted({"get_json"} & provider_http_imports),
    "providers_keeps_video_task_io_imports": sorted({"download_video_asset"} & provider_io_imports),
    "providers_keeps_video_task_path_imports": sorted({"resolve_video_task_path"} & provider_path_imports),
    "providers_keeps_low_level_io_imports": sorted({"os", "shutil", "subprocess"} & providers_imported_modules),
    "providers_keeps_low_level_http_imports": sorted({"json", "urllib.error", "urllib.request"} & providers_imported_modules),
    "providers_imports_material_resolver_directly": sorted({"material_resolver"} & providers_imported_modules),
}

report = {
    "success": not any(failures.values()),
    "schema_version": "product_creative.provider_boundary_check.v1",
    "counts": {
        "contract_constants": len(CONTRACT_CONSTANTS),
        "registry_functions": len(REGISTRY_FUNCTIONS),
        "adapter_functions": len(ADAPTER_FUNCTIONS),
        "payload_functions": len(PAYLOAD_FUNCTIONS),
        "generation_functions": len(GENERATION_FUNCTIONS),
        "path_functions": len(PATH_FUNCTIONS),
        "validation_functions": len(VALIDATION_FUNCTIONS),
        "config_functions": len(CONFIG_FUNCTIONS),
        "readiness_functions": len(READINESS_FUNCTIONS),
        "response_functions": len(RESPONSE_FUNCTIONS),
        "video_task_functions": len(VIDEO_TASK_FUNCTIONS),
        "io_functions": len(IO_FUNCTIONS),
        "http_functions": len(HTTP_FUNCTIONS),
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
