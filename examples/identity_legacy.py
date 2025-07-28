"""Python legacy generic function implementation."""

from typing import TypeVar

T = TypeVar("T")


def identity(value: T) -> T:
    """Return the input value unchanged (legacy syntax)."""
    return value
