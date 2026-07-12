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

workflow_path = plugin / "workflow.py"
tools_path = plugin / "tools.py"
tool_handlers_path = plugin / "tool_handlers.py"
contracts_path = plugin / "contracts" / "actions.py"
runtime_init = plugin / "runtime" / "__init__.py"
runtime_action_surface = plugin / "runtime" / "action_surface.py"
runtime_agent = plugin / "runtime" / "agent.py"
runtime_conversation = plugin / "runtime" / "conversation.py"
runtime_conversation_arguments = plugin / "runtime" / "conversation_arguments.py"
runtime_decision = plugin / "runtime" / "decision.py"
runtime_evidence = plugin / "runtime" / "evidence.py"
runtime_execution = plugin / "runtime" / "execution.py"
runtime_execution_arguments = plugin / "runtime" / "execution_arguments.py"
runtime_guard = plugin / "runtime" / "guard.py"
runtime_planning = plugin / "runtime" / "planning.py"
runtime_state = plugin / "runtime" / "state.py"
runtime_tracing = plugin / "runtime" / "tracing.py"

workflow_tree = ast.parse(workflow_path.read_text(encoding="utf-8-sig"))
tools_tree = ast.parse(tools_path.read_text(encoding="utf-8-sig"))
tool_handlers_tree = ast.parse(tool_handlers_path.read_text(encoding="utf-8-sig"))
contracts_tree = ast.parse(contracts_path.read_text(encoding="utf-8-sig"))
action_surface_tree = ast.parse(runtime_action_surface.read_text(encoding="utf-8-sig")) if runtime_action_surface.exists() else ast.Module(body=[], type_ignores=[])
agent_tree = ast.parse(runtime_agent.read_text(encoding="utf-8-sig")) if runtime_agent.exists() else ast.Module(body=[], type_ignores=[])
conversation_tree = ast.parse(runtime_conversation.read_text(encoding="utf-8-sig")) if runtime_conversation.exists() else ast.Module(body=[], type_ignores=[])
conversation_arguments_tree = ast.parse(runtime_conversation_arguments.read_text(encoding="utf-8-sig")) if runtime_conversation_arguments.exists() else ast.Module(body=[], type_ignores=[])
decision_tree = ast.parse(runtime_decision.read_text(encoding="utf-8-sig")) if runtime_decision.exists() else ast.Module(body=[], type_ignores=[])
evidence_tree = ast.parse(runtime_evidence.read_text(encoding="utf-8-sig")) if runtime_evidence.exists() else ast.Module(body=[], type_ignores=[])
execution_tree = ast.parse(runtime_execution.read_text(encoding="utf-8-sig")) if runtime_execution.exists() else ast.Module(body=[], type_ignores=[])
execution_arguments_tree = ast.parse(runtime_execution_arguments.read_text(encoding="utf-8-sig")) if runtime_execution_arguments.exists() else ast.Module(body=[], type_ignores=[])
guard_tree = ast.parse(runtime_guard.read_text(encoding="utf-8-sig")) if runtime_guard.exists() else ast.Module(body=[], type_ignores=[])
planning_tree = ast.parse(runtime_planning.read_text(encoding="utf-8-sig")) if runtime_planning.exists() else ast.Module(body=[], type_ignores=[])
state_tree = ast.parse(runtime_state.read_text(encoding="utf-8-sig")) if runtime_state.exists() else ast.Module(body=[], type_ignores=[])

DECISION_FUNCTIONS = {
    "action_from_message",
    "duration_from_message",
    "exact_video_template_from_message",
    "external_mode_from_message",
    "external_provider_from_message",
    "fps_from_message",
    "message_allows_evolution",
    "message_indicates_confirmation",
    "message_indicates_rejected",
    "message_indicates_selected",
    "rating_from_message",
    "target_from_message",
    "url_from_message",
    "variant_from_message",
}

WORKFLOW_DECISION_FUNCTIONS = {"_" + name for name in DECISION_FUNCTIONS}
WORKFLOW_REQUIRED_DECISION_FUNCTIONS = {
    "url_from_message",
}
CONVERSATION_FUNCTIONS = {
    "conversation_adapter",
}
WORKFLOW_REQUIRED_CONVERSATION_SYMBOLS = {
    "CONVERSATION_ADAPTER_SCHEMA_VERSION",
    "conversation_adapter",
}
WORKFLOW_CONVERSATION_FUNCTIONS = {
    "_agent_reply",
    "_apply_conversation_args",
    "_remove_missing_input",
    "conversation_adapter",
}
ACTION_SURFACE_FUNCTIONS = {
    "action_descriptor",
    "command_for_action",
    "user_next_message_for_action",
}
WORKFLOW_ACTION_SURFACE_FUNCTIONS = {
    "_action",
    "_command",
    "_user_next_message",
}
GUARD_FUNCTIONS = {
    "action_guard",
}
WORKFLOW_REQUIRED_GUARD_SYMBOLS = {
    "ACTION_GUARD_SCHEMA_VERSION",
    "action_guard",
}
WORKFLOW_GUARD_FUNCTIONS = {
    "_action_metadata",
    "_allow",
    "_block",
    "_guard_base",
    "action_guard",
}
PLANNING_FUNCTIONS = {
    "missing_inputs",
    "plan_status",
    "workflow_next",
    "workflow_plan",
    "workflow_summary",
}
WORKFLOW_REQUIRED_PLANNING_SYMBOLS = {
    "WORKFLOW_NEXT_SCHEMA_VERSION",
    "WORKFLOW_PLAN_SCHEMA_VERSION",
    "WORKFLOW_SUMMARY_SCHEMA_VERSION",
    "workflow_next",
    "workflow_plan",
    "workflow_summary",
}
WORKFLOW_PLANNING_FUNCTIONS = {
    "_args_template",
    "_latest_proposal_id",
    "_missing_inputs",
    "_plan_status",
    "workflow_next",
    "workflow_plan",
    "workflow_summary",
}
EXECUTION_FUNCTIONS = {
    "workflow_execute",
    "workflow_run",
}
WORKFLOW_REQUIRED_EXECUTION_SYMBOLS = {
    "WORKFLOW_EXECUTE_SCHEMA_VERSION",
    "WORKFLOW_RUN_SCHEMA_VERSION",
    "workflow_execute",
    "workflow_run",
}
WORKFLOW_EXECUTION_FUNCTIONS = {
    "_apply_execution_args",
    "_auto_step_allowed",
    "_execute_ready_step",
    "_execution_action",
    "_execution_summary",
    "_m6_auto_followup_allowed",
    "_refresh_plan_status",
    "_run_stop_reason",
    "workflow_execute",
    "workflow_run",
}
AGENT_FUNCTIONS = {
    "compact_workflow_run_result",
    "execution_contract",
    "interpreted_intent",
    "learning_writeback_state",
    "product_agent_turn",
}
EVIDENCE_FUNCTIONS = {
    "is_newer",
    "is_strictly_newer",
    "latest_json",
    "latest_json_matching",
    "proposal_pair",
    "source_count",
}
WORKFLOW_REQUIRED_EVIDENCE_FUNCTIONS = {
    "is_newer",
    "is_strictly_newer",
}
STATE_REQUIRED_EVIDENCE_FUNCTIONS = {
    "is_newer",
    "latest_json",
    "latest_json_matching",
    "proposal_pair",
    "source_count",
}
STATE_FUNCTIONS = {
    "safety_contract",
    "workflow_status",
}
WORKFLOW_EVIDENCE_FUNCTIONS = {
    "_is_newer",
    "_is_strictly_newer",
    "_latest_json",
    "_latest_json_matching",
    "_proposal_pair",
    "_read_jsonl",
    "_source_count",
}
WORKFLOW_STATE_FUNCTIONS = {
    "_batch_policy_extra",
    "_compact_item",
    "_derive_status",
    "_feedback_extra",
    "_image_analysis_extra",
    "_image_brief_extra",
    "_image_brief_review_extra",
    "_image_intent_extra",
    "_image_run_extra",
    "_live_readiness_extra",
    "_material_card_extra",
    "_material_extra",
    "_material_feedback_extra",
    "_material_usage_extra",
    "_proposal_extra",
    "_provider_payload_extra",
    "_review_package_extra",
    "_run_extra",
    "_safety_contract",
    "_task_material_pack_extra",
    "_video_execution_policy_extra",
    "_video_reference_readiness_extra",
    "_video_result_extra",
    "_video_task_extra",
    "_video_task_status_extra",
    "_visual_alignment_extra",
    "workflow_status",
}


def dict_from_assign(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return ast.literal_eval(node.value)
                    except ValueError:
                        sys.path.insert(0, str(repo_root / ".hermes" / "plugins"))
                        from product_creative.contracts.actions import ACTION_CONTRACTS
                        return ACTION_CONTRACTS if name == "ACTION_CONTRACTS" else {}
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                sys.path.insert(0, str(repo_root / ".hermes" / "plugins"))
                from product_creative.contracts.actions import ACTION_CONTRACTS
                return ACTION_CONTRACTS if name == "ACTION_CONTRACTS" else {}
    return {}


def has_import_from_contracts(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module == ".contracts.actions" or node.module == "contracts.actions":
            return True
        if node.module == "product_creative.contracts.actions":
            return True
        if node.module == "contracts.actions":
            return True
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == ".contracts.actions"
        for node in tree.body
    )


def imports_action_tool_contract_symbols(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != ".contracts.actions" and node.module != "contracts.actions":
            continue
        names = {alias.name for alias in node.names}
        return {"ACTION_TOOL_NAMES"}.issubset(names)
    return False


def imports_guard_contract_symbols(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != ".contracts.actions" and node.module != "contracts.actions":
            continue
        names = {alias.name for alias in node.names}
        return {"ACTION_NAMES", "action_metadata"}.issubset(names)
    return False


def workflow_imports_contracts_directly(tree):
    return has_import_from_contracts(tree)


def imports_module(tree, module_name):
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            return True
        if isinstance(node, ast.Import):
            if any(alias.name == module_name for alias in node.names):
                return True
    return False


def workflow_redefines_contracts(tree):
    names = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return sorted(names & {"ACTION_NAMES", "ACTION_TOOL_NAMES", "ACTION_CONTRACTS"})


def workflow_defines_trace_writers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(names & {"_workflow_run_markdown", "_write_workflow_run_record", "write_workflow_run_record"})


def imports_tracing_writer(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.tracing":
            continue
        names = {alias.name for alias in node.names}
        return "write_workflow_run_record" in names
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


def agent_imports_execution_run(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "execution":
            continue
        names = {alias.name for alias in node.names}
        return "workflow_run" in names
    return False


def agent_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(AGENT_FUNCTIONS - names)


def conversation_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(CONVERSATION_FUNCTIONS - names)


def tools_redefines_agent_turn_helpers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(names & {"_compact_workflow_run_result", "product_agent_turn", "compact_workflow_run_result"})


def tools_imports_workflow_run_directly(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "workflow":
            continue
        names = {alias.name for alias in node.names}
        if "workflow_run" in names:
            return True
    return False


def imports_decision_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.decision":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted(WORKFLOW_REQUIRED_DECISION_FUNCTIONS - imported)


def imports_execution_symbols(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.execution":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted(WORKFLOW_REQUIRED_EXECUTION_SYMBOLS - imported)


def imports_execution_decision_functions(*trees):
    imported = set()
    for tree in trees:
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "decision":
                imported.update(alias.name for alias in node.names)
    return sorted({"url_from_message"} - imported)


def imports_conversation_decision_functions(*trees):
    imported = set()
    for tree in trees:
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "decision":
                imported.update(alias.name for alias in node.names)
    return sorted((DECISION_FUNCTIONS - {"action_from_message"}) - imported)


def imports_conversation_symbols(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.conversation":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted(WORKFLOW_REQUIRED_CONVERSATION_SYMBOLS - imported)


def imports_execution_conversation_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "conversation":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"conversation_adapter"} - imported)


def imports_conversation_planning_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "planning":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"workflow_next", "workflow_plan"} - imported)


def imports_conversation_state_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "state":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"safety_contract", "workflow_status"} - imported)


def imports_action_surface_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.action_surface":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted(ACTION_SURFACE_FUNCTIONS - imported)


def imports_planning_action_surface_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "action_surface":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"action_descriptor", "user_next_message_for_action"} - imported)


def imports_guard_symbols(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.guard":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted(WORKFLOW_REQUIRED_GUARD_SYMBOLS - imported)


def imports_planning_guard_symbols(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "guard":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"action_guard"} - imported)


def imports_planning_symbols(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.planning":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted(WORKFLOW_REQUIRED_PLANNING_SYMBOLS - imported)


def imports_execution_planning_functions(*trees):
    imported = set()
    for tree in trees:
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "planning":
                imported.update(alias.name for alias in node.names)
    return sorted({"missing_inputs", "plan_status", "workflow_next", "workflow_plan"} - imported)


def imports_evidence_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.evidence":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted(WORKFLOW_REQUIRED_EVIDENCE_FUNCTIONS - imported)


def imports_planning_evidence_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "evidence":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"is_newer", "is_strictly_newer"} - imported)


def imports_state_evidence_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "evidence":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted(STATE_REQUIRED_EVIDENCE_FUNCTIONS - imported)


def imports_state_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "runtime.state":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"WORKFLOW_STATUS_SCHEMA_VERSION", "workflow_status"} - imported)


def imports_execution_state_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "state":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"safety_contract", "workflow_status"} - imported)


def imports_execution_tracing_writer(tree):
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "tracing":
            continue
        names = {alias.name for alias in node.names}
        return "write_workflow_run_record" in names
    return False


def imports_planning_state_functions(tree):
    imported = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "state":
            continue
        imported.update(alias.name for alias in node.names)
    return sorted({"safety_contract", "workflow_status"} - imported)


def decision_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(DECISION_FUNCTIONS - names)


def action_surface_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(ACTION_SURFACE_FUNCTIONS - names)


def guard_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(GUARD_FUNCTIONS - names)


def planning_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(PLANNING_FUNCTIONS - names)


def execution_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(EXECUTION_FUNCTIONS - names)


def evidence_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(EVIDENCE_FUNCTIONS - names)


def state_defines_required_functions(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(STATE_FUNCTIONS - names)


def workflow_defines_decision_parsers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(WORKFLOW_DECISION_FUNCTIONS & names)


def workflow_defines_conversation_helpers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(WORKFLOW_CONVERSATION_FUNCTIONS & names)


def workflow_defines_action_surface_helpers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(WORKFLOW_ACTION_SURFACE_FUNCTIONS & names)


def workflow_defines_guard_helpers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(WORKFLOW_GUARD_FUNCTIONS & names)


def workflow_defines_planning_helpers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(WORKFLOW_PLANNING_FUNCTIONS & names)


def workflow_defines_execution_helpers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(WORKFLOW_EXECUTION_FUNCTIONS & names)


def workflow_defines_evidence_readers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(WORKFLOW_EVIDENCE_FUNCTIONS & names)


def workflow_defines_state_snapshot_helpers(tree):
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    return sorted(WORKFLOW_STATE_FUNCTIONS & names)


def action_metadata_delegates(tree):
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "_action_metadata":
            continue
        returns = [sub.value for sub in ast.walk(node) if isinstance(sub, ast.Return)]
        if len(returns) != 1:
            return False
        value = returns[0]
        return (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "contract_action_metadata"
        )
    return False


contracts = dict_from_assign(contracts_tree, "ACTION_CONTRACTS")
contract_errors = []
for action, contract in contracts.items():
    if not contract.get("tool"):
        contract_errors.append(f"{action}: missing tool")
    if not contract.get("domain"):
        contract_errors.append(f"{action}: missing domain")
    for key in [
        "requires_user_input",
        "requires_explicit_confirmation",
        "writes_product_workspace",
        "mutates_confirmed_product_brain",
    ]:
        if key not in contract:
            contract_errors.append(f"{action}: missing {key}")

failures = {
    "missing_contract_registry": [] if contracts_path.exists() else [str(contracts_path)],
    "missing_action_contracts": [] if contracts else ["contracts/actions.py: ACTION_CONTRACTS"],
    "missing_runtime_package": [] if runtime_init.exists() else [str(runtime_init)],
    "missing_runtime_action_surface": [] if runtime_action_surface.exists() else [str(runtime_action_surface)],
    "missing_runtime_agent": [] if runtime_agent.exists() else [str(runtime_agent)],
    "missing_runtime_conversation": [] if runtime_conversation.exists() else [str(runtime_conversation)],
    "missing_runtime_decision": [] if runtime_decision.exists() else [str(runtime_decision)],
    "missing_runtime_evidence": [] if runtime_evidence.exists() else [str(runtime_evidence)],
    "missing_runtime_execution": [] if runtime_execution.exists() else [str(runtime_execution)],
    "missing_runtime_guard": [] if runtime_guard.exists() else [str(runtime_guard)],
    "missing_runtime_planning": [] if runtime_planning.exists() else [str(runtime_planning)],
    "missing_runtime_state": [] if runtime_state.exists() else [str(runtime_state)],
    "missing_runtime_tracing": [] if runtime_tracing.exists() else [str(runtime_tracing)],
    "runtime_action_surface_missing_functions": action_surface_defines_required_functions(action_surface_tree),
    "runtime_agent_missing_functions": agent_defines_required_functions(agent_tree),
    "runtime_agent_missing_execution_import": [] if agent_imports_execution_run(agent_tree) else ["runtime/agent.py"],
    "runtime_conversation_missing_functions": conversation_defines_required_functions(conversation_tree),
    "runtime_conversation_missing_decision_imports": imports_conversation_decision_functions(conversation_tree, conversation_arguments_tree),
    "runtime_conversation_missing_planning_imports": imports_conversation_planning_functions(conversation_tree),
    "runtime_conversation_missing_state_imports": imports_conversation_state_functions(conversation_tree),
    "runtime_decision_missing_functions": decision_defines_required_functions(decision_tree),
    "runtime_evidence_missing_functions": evidence_defines_required_functions(evidence_tree),
    "runtime_execution_missing_functions": execution_defines_required_functions(execution_tree),
    "runtime_execution_missing_conversation_imports": imports_execution_conversation_functions(execution_tree),
    "runtime_execution_missing_decision_imports": imports_execution_decision_functions(execution_tree, execution_arguments_tree),
    "runtime_execution_missing_planning_imports": imports_execution_planning_functions(execution_tree, execution_arguments_tree),
    "runtime_execution_missing_state_imports": imports_execution_state_functions(execution_tree),
    "runtime_execution_missing_tracing_import": [] if imports_execution_tracing_writer(execution_tree) else ["runtime/execution.py"],
    "runtime_guard_missing_functions": guard_defines_required_functions(guard_tree),
    "runtime_guard_missing_capability_registry": [] if imports_module(guard_tree, "capabilities.registry") else ["runtime/guard.py"],
    "runtime_guard_missing_policy_helpers": [] if imports_module(guard_tree, "capabilities.policy_helpers") else ["runtime/guard.py"],
    "runtime_planning_missing_functions": planning_defines_required_functions(planning_tree),
    "runtime_planning_missing_contract_imports": [] if imports_module(planning_tree, "capabilities.registry") else ["runtime/planning.py"],
    "runtime_planning_missing_action_surface_imports": imports_planning_action_surface_functions(planning_tree),
    "runtime_planning_missing_guard_imports": imports_planning_guard_symbols(planning_tree),
    "runtime_planning_missing_evidence_imports": imports_planning_evidence_functions(planning_tree),
    "runtime_planning_missing_state_imports": imports_planning_state_functions(planning_tree),
    "runtime_state_missing_functions": state_defines_required_functions(state_tree),
    "runtime_state_missing_evidence_imports": imports_state_evidence_functions(state_tree),
    "workflow_imports_contracts_directly": ["workflow.py"] if workflow_imports_contracts_directly(workflow_tree) else [],
    "workflow_redefines_contract_registry": workflow_redefines_contracts(workflow_tree),
    "workflow_missing_execution_imports": imports_execution_symbols(workflow_tree),
    "workflow_redefines_execution_helpers": workflow_defines_execution_helpers(workflow_tree),
    "workflow_missing_conversation_imports": imports_conversation_symbols(workflow_tree),
    "workflow_redefines_conversation_helpers": workflow_defines_conversation_helpers(workflow_tree),
    "workflow_imports_action_surface_directly": ["workflow.py"] if imports_module(workflow_tree, "runtime.action_surface") else [],
    "workflow_redefines_action_surface_helpers": workflow_defines_action_surface_helpers(workflow_tree),
    "workflow_missing_guard_imports": imports_guard_symbols(workflow_tree),
    "workflow_redefines_guard_helpers": workflow_defines_guard_helpers(workflow_tree),
    "workflow_missing_planning_imports": imports_planning_symbols(workflow_tree),
    "workflow_redefines_planning_helpers": workflow_defines_planning_helpers(workflow_tree),
    "workflow_redefines_decision_parsers": workflow_defines_decision_parsers(workflow_tree),
    "workflow_imports_evidence_directly": ["workflow.py"] if imports_module(workflow_tree, "runtime.evidence") else [],
    "workflow_redefines_evidence_readers": workflow_defines_evidence_readers(workflow_tree),
    "workflow_missing_state_imports": imports_state_functions(workflow_tree),
    "workflow_redefines_state_snapshot_helpers": workflow_defines_state_snapshot_helpers(workflow_tree),
    "workflow_redefines_trace_writers": workflow_defines_trace_writers(workflow_tree),
    "tools_missing_capability_command_registry": [] if imports_module(tool_handlers_tree, "capabilities.registry") else ["tool_handlers.py"],
    "tools_redefines_agent_turn_helpers": tools_redefines_agent_turn_helpers(tool_handlers_tree),
    "tools_imports_workflow_run_directly": ["tool_handlers.py"] if tools_imports_workflow_run_directly(tool_handlers_tree) else [],
    "invalid_action_contracts": contract_errors,
}

report = {
    "success": not any(failures.values()),
    "schema_version": "product_creative.runtime_boundary_check.v1",
    "counts": {
        "action_contracts": len(contracts),
        "action_surface_functions": len(ACTION_SURFACE_FUNCTIONS),
        "agent_functions": len(AGENT_FUNCTIONS),
        "conversation_functions": len(CONVERSATION_FUNCTIONS),
        "decision_functions": len(DECISION_FUNCTIONS),
        "evidence_functions": len(EVIDENCE_FUNCTIONS),
        "execution_functions": len(EXECUTION_FUNCTIONS),
        "guard_functions": len(GUARD_FUNCTIONS),
        "planning_functions": len(PLANNING_FUNCTIONS),
        "state_functions": len(STATE_FUNCTIONS),
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
