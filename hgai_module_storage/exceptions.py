"""Storage abstraction exceptions."""


class StorageError(Exception):
    """Base class for all storage errors."""


class NotFoundError(StorageError):
    """Raised when a requested document does not exist."""


class ConflictError(StorageError):
    """Raised on duplicate-key or other constraint violations."""


class BackendNotRegisteredError(StorageError):
    """Raised when the requested backend name has not been registered."""
