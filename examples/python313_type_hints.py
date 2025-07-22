"""Example of Python 3.13 compatible type hints."""

from __future__ import annotations  # Enable modern type hint syntax

import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Optional, Protocol, Union


class VersionTrackerProtocol(Protocol):
    """Protocol for version tracker objects."""

    def get_version(self) -> str:
        """Get version string."""
        ...


# Modern type hints (Python 3.9+)
def process_apps(
    apps: list[str],  # Instead of List[str]
    config: dict[str, Any],  # Instead of Dict[str, Any]
    options: tuple[str, ...] = (),  # Instead of Tuple[str, ...]
    exclude: set[str] | None = None,  # Union syntax with |
) -> dict[str, list[str]]:  # Instead of Dict[str, List[str]]
    """Process applications with modern type hints.

    Args:
        apps: List of application names
        config: Configuration dictionary
        options: Optional configuration tuple
        exclude: Set of apps to exclude

    Returns:
        Dictionary mapping categories to app lists
    """
    if exclude is None:
        exclude = set()

    result: dict[str, list[str]] = {}

    for app in apps:
        if app not in exclude:
            category = config.get("category", "default")
            if category not in result:
                result[category] = []
            result[category].append(app)

    return result


# Still use Union/Optional for complex types
ComplexType = Union[str, int, list[str], dict[str, Any]]
MaybeString = Optional[str]


# Use collections.abc for abstract types
def handle_mapping(data: Mapping[str, Any]) -> Sequence[str]:
    """Handle mapping data."""
    return list(data.keys())


# Generic functions with type variables (if needed)
if sys.version_info >= (3, 12):
    # Python 3.12+ generic syntax
    def identity[T](value: T) -> T:
        """Return the input value unchanged."""
        return value
else:
    # Backward compatible syntax
    from typing import TypeVar

    T = TypeVar("T")

    def identity(value: T) -> T:
        """Return the input value unchanged."""
        return value


# Class with generic type parameters
class Cache[K, V]:  # Python 3.12+ syntax
    """Generic cache class."""

    def __init__(self) -> None:
        """Initialize empty cache."""
        self._data: dict[K, V] = {}

    def get(self, key: K) -> V | None:
        """Get value by key."""
        return self._data.get(key)

    def set(self, key: K, value: V) -> None:
        """Set value by key."""
        self._data[key] = value


# For older Python versions, use traditional syntax
if sys.version_info < (3, 12):
    from typing import Generic, TypeVar

    K = TypeVar("K")
    V = TypeVar("V")

    class Cache(Generic[K, V]):
        """Generic cache class (backward compatible)."""

        def __init__(self) -> None:
            """Initialize empty cache."""
            self._data: dict[K, V] = {}

        def get(self, key: K) -> V | None:
            """Get value by key."""
            return self._data.get(key)

        def set(self, key: K, value: V) -> None:
            """Set value by key."""
            self._data[key] = value
