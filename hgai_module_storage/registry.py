"""Backend registry for pluggable storage implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Type

if TYPE_CHECKING:
    from .backend import StorageBackend

from .exceptions import BackendNotRegisteredError

_backends: Dict[str, Type["StorageBackend"]] = {}


def register_backend(name: str, cls: Type["StorageBackend"]) -> None:
    """Register a storage backend class under the given name."""
    _backends[name] = cls


def get_backend_class(name: str) -> Type["StorageBackend"]:
    """Return the registered backend class for the given name.

    Raises BackendNotRegisteredError if the name is not registered.
    """
    if name not in _backends:
        raise BackendNotRegisteredError(
            f"Storage backend {name!r} not registered. Available: {list(_backends)}"
        )
    return _backends[name]


def list_backends() -> List[str]:
    """Return the names of all registered backends."""
    return list(_backends.keys())
