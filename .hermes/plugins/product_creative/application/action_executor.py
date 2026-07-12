"""Capability execution service with durable idempotency receipts."""

from __future__ import annotations

import os
from typing import Any, Dict

from ..capabilities.registry import action_descriptors
from ..common import now_iso
from ..contracts.models import ActionCommand, ActionResult
from ..ports.runtime_repositories import provider_dispatcher, receipts
from ..provider_registry import env_value, provider_entry


class CapabilityExecutor:
    def execute(self, command: ActionCommand) -> ActionResult:
        descriptor = action_descriptors().get(command.action)
        if descriptor is None:
            return ActionResult(
                success=False,
                action=command.action,
                product_id=command.product_id,
                workflow_id=command.workflow_id,
                step_id=command.step_id,
                trace_id=command.trace_id,
                error_code="UNKNOWN_ACTION",
                error_message=f"unknown Product Creative action '{command.action}'",
            )
        definition = descriptor.runtime
        if descriptor.side_effect == "provider":
            provider = str(command.args.get("provider") or "mock").lower()
            mode = str(command.args.get("mode") or "").lower()
            if not provider.startswith("mock") and mode != "mock":
                provider_error = self._real_provider_error(provider, command.confirmed)
                if provider_error:
                    return ActionResult(
                        success=False,
                        action=command.action,
                        product_id=command.product_id,
                        workflow_id=command.workflow_id,
                        step_id=command.step_id,
                        trace_id=command.trace_id,
                        error_code=provider_error[0],
                        error_message=provider_error[1],
                    )
        repository = receipts(command.product_id)
        receipt_key = ""
        values: Dict[str, Any] = {}
        if definition.idempotency_fields and command.product_id:
            values = {field: command.args.get(field) for field in definition.idempotency_fields}
            receipt_key = command.idempotency_key or repository.key(command.action, values)
            claim = repository.claim(command.action, receipt_key, values)
            if not claim["claimed"]:
                if claim["status"] == "completed":
                    replay = dict(claim.get("result") or {})
                    replay.update({"idempotent_replay": True, "action_receipt": claim["receipt_path"]})
                    return self._result(command, replay)
                if descriptor.side_effect != "provider":
                    return ActionResult(
                        success=False,
                        action=command.action,
                        product_id=command.product_id,
                        workflow_id=command.workflow_id,
                        step_id=command.step_id,
                        trace_id=command.trace_id,
                        error_code="ACTION_IN_PROGRESS",
                        error_message="an equivalent action is already in progress",
                        retryable=True,
                    )
        try:
            if descriptor.side_effect == "provider":
                output = self._execute_provider(descriptor, definition, command, receipt_key)
            else:
                output = definition.execute(dict(command.args))
        except Exception as exc:
            if receipt_key:
                repository.fail(
                    command.action,
                    receipt_key,
                    {"type": type(exc).__name__, "message": str(exc), "retryable": False},
                )
            raise
        if receipt_key:
            if output.get("success"):
                receipt_path = repository.save(
                    command.action,
                    receipt_key,
                    {
                        "idempotency_values": values,
                        "created_at": now_iso(),
                        "result": output,
                    },
                )
                output = {**output, "action_receipt": receipt_path}
            else:
                repository.fail(
                    command.action,
                    receipt_key,
                    output.get("error") if isinstance(output.get("error"), dict) else {"result": output},
                )
        return self._result(command, output)

    @staticmethod
    def _real_provider_error(provider: str, confirmed: bool) -> tuple[str, str] | None:
        if os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER") != "1":
            return (
                "REAL_PROVIDER_DISABLED",
                "Real provider execution requires PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1.",
            )
        if not confirmed:
            return (
                "CONFIRMATION_REQUIRED",
                "Explicit confirmation is required before a real provider call.",
            )
        try:
            entry = provider_entry(provider)
        except ValueError as exc:
            return ("PROVIDER_NOT_REGISTERED", str(exc))
        if not entry.get("execute_supported"):
            return ("PROVIDER_EXECUTION_UNSUPPORTED", f"Provider '{provider}' does not support execution.")
        missing = [name for name in entry.get("requires_config", []) if not env_value(str(name))]
        if missing:
            return ("PROVIDER_CONFIG_MISSING", "Missing provider configuration: " + ", ".join(missing))
        return None

    @staticmethod
    def _execute_provider(descriptor, definition, command: ActionCommand, receipt_key: str) -> Dict[str, Any]:
        return provider_dispatcher().dispatch(
            command=command,
            descriptor=descriptor,
            definition=definition,
            receipt_key=receipt_key,
        )

    @staticmethod
    def _result(command: ActionCommand, output: Dict[str, Any]) -> ActionResult:
        error = output.get("error") if isinstance(output.get("error"), dict) else {}
        return ActionResult(
            success=bool(output.get("success")),
            action=command.action,
            product_id=command.product_id,
            workflow_id=command.workflow_id,
            step_id=command.step_id,
            trace_id=command.trace_id,
            output=output,
            error_code=str(error.get("error_code") or output.get("error_code") or ""),
            error_message=str(error.get("error_message") or output.get("error_message") or ""),
            retryable=bool(error.get("retryable") or output.get("retryable")),
        )


_EXECUTOR = CapabilityExecutor()


def capability_executor() -> CapabilityExecutor:
    return _EXECUTOR
