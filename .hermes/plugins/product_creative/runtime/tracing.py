"""Runtime trace writers for Product Creative workflow runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..common import append_jsonl, update_index_and_log, write_json


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _rel(base: Path, path: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))


def workflow_run_markdown(run: Dict[str, Any]) -> str:
    lines = [
        f"# {run['workflow_run_id']}",
        "",
        f"Product: {run['product_id']}",
        f"Stop reason: {run['stop_reason']}",
        f"Executed steps: {run['executed_count']} / {run['attempted_count']}",
        f"Initial message: {run.get('initial_message') or ''}",
        "",
        "## Steps",
        "",
    ]
    for item in run.get("executions") or []:
        lines.append(
            f"- {item.get('action')}: {item.get('execution_status')} | "
            f"result={item.get('result_id') or ''}"
        )
    next_action = run.get("recommended_next_action") or {}
    lines.extend(
        [
            "",
            "## Next",
            "",
            f"- Action: {next_action.get('action') or ''}",
            f"- User next message: {next_action.get('user_next_message') or ''}",
            f"- Requires user input: {next_action.get('requires_user_input')}",
            f"- Requires confirmation: {next_action.get('requires_explicit_confirmation')}",
            f"- Mutates Product Brain: {next_action.get('mutates_product_brain')}",
            "",
        ]
    )
    return "\n".join(lines)


def write_workflow_run_record(base: Path, run: Dict[str, Any]) -> Dict[str, str]:
    out_dir = base / "artifacts" / "workflow_runs"
    run_id = _text(run.get("workflow_run_id"))
    json_path = out_dir / f"{run_id}.json"
    md_path = out_dir / f"{run_id}.md"
    write_json(json_path, run)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(workflow_run_markdown(run), encoding="utf-8")
    append_jsonl(
        base / "structured" / "workflow_run_index.jsonl",
        {
            "workflow_run_id": run_id,
            "created_at": run.get("created_at", ""),
            "stop_reason": run.get("stop_reason", ""),
            "executed_count": run.get("executed_count", 0),
            "attempted_count": run.get("attempted_count", 0),
            "recommended_next_action": (run.get("recommended_next_action") or {}).get("action", ""),
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(
        base,
        "workflow-run",
        run_id,
        [
            f"Executed: {run.get('executed_count', 0)} / {run.get('attempted_count', 0)}",
            f"Stop reason: {run.get('stop_reason', '')}",
            f"Next: {(run.get('recommended_next_action') or {}).get('action', '')}",
        ],
    )
    return {"json": str(json_path), "markdown": str(md_path)}
