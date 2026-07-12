from __future__ import annotations

from typing import Iterable

from .models import IntentRule


def contains_any(message: str, phrases: Iterable[str]) -> bool:
    lowered = message.lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def phrases(action: str, priority: int, *values: str) -> IntentRule:
    return IntentRule(action, priority, lambda message: contains_any(message, values))
