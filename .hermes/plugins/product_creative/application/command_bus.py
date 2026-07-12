"""Typed command dispatch shared by Hermes tools and CLI."""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict

from ..capabilities.registry import action_descriptors, command_descriptors
from ..contracts.durable import CommandEnvelope, CommandResult
from ..contracts.models import ActionCommand
from .action_executor import capability_executor
from .policy import PolicyEngine
from ..ports.runtime_repositories import recovery


CommandHandler = Callable[[CommandEnvelope], CommandResult]


class CommandBus:
    def __init__(self):
        self._handlers: Dict[str, CommandHandler] = {}
        self._policy = PolicyEngine()

    def register(self, command: str, handler: CommandHandler) -> None:
        if command in self._handlers:
            raise RuntimeError(f"duplicate command handler '{command}'")
        self._handlers[command] = handler

    def registered_commands(self) -> tuple[str, ...]:
        return tuple(sorted(set(self._handlers) | set(command_descriptors()) | set(action_descriptors())))

    def dispatch(self, envelope: CommandEnvelope) -> CommandResult:
        handler = self._handlers.get(envelope.command)
        if handler is not None:
            return handler(envelope)
        descriptor = action_descriptors().get(envelope.command)
        if descriptor is not None:
            policy = self._policy.authorize(descriptor, envelope)
            if not policy.allowed:
                confirmation_id = ""
                if policy.status == "confirmation_required":
                    subject_id = next(
                        (str(envelope.payload.get(key) or "") for key in (
                            "proposal_id", "rule_id", "workflow_id", "provider_task_id", "target_version"
                        ) if envelope.payload.get(key) not in (None, "")),
                        "",
                    )
                    confirmation_id = recovery().request_confirmation(
                        envelope.product_id, envelope.command, subject_id, policy.risk_level, envelope.trace_id
                    )
                return CommandResult(
                    command=envelope.command,
                    product_id=envelope.product_id,
                    status="paused" if policy.status == "confirmation_required" else "failed",
                    success=False,
                    output={"success": False, "policy": policy.model_dump(mode="json"), "confirmation_id": confirmation_id},
                    error_code="CONFIRMATION_REQUIRED" if policy.status == "confirmation_required" else "POLICY_BLOCKED",
                    error_message=policy.reason,
                )
            action_result = capability_executor().execute(
                ActionCommand(
                    action=envelope.command,
                    product_id=envelope.product_id,
                    workflow_id=envelope.workflow_id,
                    step_id=envelope.step_id,
                    trace_id=envelope.trace_id,
                    idempotency_key=envelope.idempotency_key,
                    confirmed=envelope.confirmed,
                    args=dict(envelope.payload),
                )
            )
            return CommandResult(
                command=envelope.command,
                product_id=envelope.product_id,
                status="succeeded" if action_result.success else "failed",
                success=action_result.success,
                output=action_result.output,
                artifact_ids=action_result.artifact_ids,
                evidence=action_result.evidence,
                retryable=action_result.retryable,
                error_code=action_result.error_code,
                error_message=action_result.error_message,
            )
        command = command_descriptors().get(envelope.command)
        if command is None:
            return CommandResult(
                command=envelope.command,
                product_id=envelope.product_id,
                status="failed",
                success=False,
                error_code="UNKNOWN_COMMAND",
                error_message=f"unknown Product Creative command '{envelope.command}'",
            )
        raw = command.handler(dict(envelope.payload))
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError(f"command '{envelope.command}' returned a non-object payload")
        success = bool(payload.get("success"))
        error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        return CommandResult(
            command=envelope.command,
            product_id=envelope.product_id or str(payload.get("product_id") or ""),
            status="succeeded" if success else "failed",
            success=success,
            output=payload,
            retryable=bool(error.get("retryable")),
            error_code=str(error.get("error_code") or payload.get("error_code") or ""),
            error_message=str(error.get("error_message") or payload.get("error_message") or ""),
        )

    def invoke(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        product_id = str(payload.get("product_id") or payload.get("id") or "")
        result = self.dispatch(
            CommandEnvelope(
                command=command,
                product_id=product_id,
                trace_id=str(payload.get("trace_id") or f"trace-{uuid.uuid4().hex}"),
                confirmed=bool(payload.get("confirmed")),
                payload=dict(payload),
            )
        )
        return result.output if result.output else result.model_dump(mode="json")


_COMMAND_BUS = CommandBus()


def command_bus() -> CommandBus:
    return _COMMAND_BUS
