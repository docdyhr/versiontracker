"""Python 3.12+ generic function implementation.

NOTE: This file contains Python 3.12+ syntax and should only be imported
when running on Python 3.12 or later to avoid syntax errors.
"""

from typing import TypeVar

T = TypeVar("T")


def identity(value: T) -> T:
    """Return the input value unchanged (traditional syntax)."""
    return value
