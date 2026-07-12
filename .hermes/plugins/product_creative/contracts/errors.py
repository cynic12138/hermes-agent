"""Stable errors shared across application ports and infrastructure adapters."""


class OptimisticVersionConflict(RuntimeError):
    """The persisted aggregate version no longer matches the caller's observation."""
