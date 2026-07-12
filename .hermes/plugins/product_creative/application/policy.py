"""Policy boundary for confirmation, provider, and Product Brain safety."""

from __future__ import annotations

import os

from ..capabilities.models import ActionDescriptor
from ..contracts.durable import CommandEnvelope, PolicyDecision


class PolicyEngine:
    def authorize(self, descriptor: ActionDescriptor, envelope: CommandEnvelope) -> PolicyDecision:
        provider_is_mock = (
            str(envelope.payload.get("provider") or "mock").lower().startswith("mock")
            or str(envelope.payload.get("mode") or "").lower() == "mock"
        )
        external_effect = descriptor.side_effect in {"publish", "channel"}
        canonical_effect = descriptor.side_effect in {"canonical_material", "product_brain"}
        confirmation_required = (
            descriptor.requires_explicit_confirmation
            or descriptor.mutates_confirmed_product_brain
            or external_effect
            or canonical_effect
            or (descriptor.side_effect == "provider" and not provider_is_mock)
        )
        risk = "high" if canonical_effect or external_effect else "medium" if confirmation_required else "low"
        if descriptor.side_effect == "provider" and not provider_is_mock:
            if os.environ.get("PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER") != "1":
                return PolicyDecision(
                    allowed=False,
                    status="blocked",
                    reason="Real provider execution is disabled; PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER=1 is required.",
                    risk_level="high",
                    confirmation_subject=descriptor.name,
                )
            if not envelope.confirmed:
                return PolicyDecision(
                    allowed=False,
                    status="confirmation_required",
                    reason=f"{descriptor.name} requires explicit confirmation before a billable provider call.",
                    risk_level="high",
                    confirmation_subject=descriptor.name,
                )
        if confirmation_required and not envelope.confirmed:
            return PolicyDecision(
                allowed=False,
                status="confirmation_required",
                reason=f"{descriptor.name} requires explicit user confirmation.",
                risk_level=risk,
                confirmation_subject=descriptor.name,
            )
        return PolicyDecision(allowed=True, status="allowed", risk_level=risk)
