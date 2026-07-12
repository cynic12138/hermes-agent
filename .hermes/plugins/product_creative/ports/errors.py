"""Storage boundary exceptions exposed to core services."""


class StoreError(RuntimeError):
    pass


class StoreCorruptionError(StoreError):
    pass
