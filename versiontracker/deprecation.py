"""Deprecation utilities for VersionTracker.

This module centralizes emission of deprecation warnings (e.g., legacy CLI
flags like ``--blacklist``) so that:

1. Each deprecation is only emitted *once* per process execution
2. Warnings can be suppressed (e.g., in automated test runs)
3. Messages follow a consistent format with optional removal/version metadata
4. Future programmatic inspection (e.g., exporting a JSON summary) is enabled

Usage Example:
    from versiontracker.deprecation import warn_deprecated_flag

    # When parsing CLI arguments:
    if args.blacklist and not args.blocklist:
        warn_deprecated_flag(
            flag="--blacklist",
            replacement="--blocklist",
            removal_version="0.8.0",
        )

Testing:
    - In tests, call ``reset_deprecation_registry()`` in test setup to ensure
      isolation.
    - To assert warning emission, capture stderr or patch ``logging.warning``.
    - To suppress warnings globally (e.g., performance benchmark), set env:
      ``export VERSIONTRACKER_NO_DEPRECATION_WARNINGS=1``.

Environment Variables:
    VERSIONTRACKER_NO_DEPRECATION_WARNINGS:
        If set to any truthy value (1, true, yes, on), no deprecation
        warnings will be emitted.

Design Notes:
    - We avoid using the standard ``warnings`` module for finer control over
      formatting and to permit future structured export (JSON).
    - Logging is used (WARNING level) to fit existing project logging
      patterns. Console user hint is (optionally) printed with minimal
      formatting for visibility if color support is available.

Future Ideas:
    - Add JSON export of collected deprecations for telemetry.
    - Add severity levels (e.g., pending removal vs newly deprecated).
    - Integrate with a global "doctor" or "diagnostics" command.

"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass

# Module-level logger
LOGGER = logging.getLogger("versiontracker.deprecation")

# Thread-safe registry to ensure single emission per key
_registry_lock = threading.Lock()
_emitted: set[str] = set()

# Cache of formatted messages for potential future retrieval (e.g., diagnostics)
_message_cache: dict[str, str] = {}

# Truthy values for environment flag
_TRUTHY = {"1", "true", "yes", "on"}


@dataclass
class DeprecationRecord:
    """Structured representation of a deprecation event.

    Attributes:
        key: A unique internal key for this deprecation (e.g., flag name)
        message: The formatted user-facing message
        replacement: Suggested replacement (if any)
        removal_version: Target version for removal (if known)
    """

    key: str
    message: str
    replacement: str | None
    removal_version: str | None


def _is_suppressed(env: dict | None = None) -> bool:
    """Determine if deprecation warnings are globally suppressed.

    Args:
        env: Optional environment mapping (for testing)

    Returns:
        bool: True if suppression is active
    """
    mapping = env if env is not None else os.environ
    raw = mapping.get("VERSIONTRACKER_NO_DEPRECATION_WARNINGS", "").strip().lower()
    return raw in _TRUTHY


def _format_flag_message(
    flag: str,
    replacement: str | None,
    removal_version: str | None,
) -> str:
    """Format a standardized deprecation message.

    Args:
        flag: The deprecated flag or identifier
        replacement: Replacement suggestion
        removal_version: Planned removal version (semantic version string)

    Returns:
        str: Formatted message
    """
    parts = [f"The flag '{flag}' is deprecated"]
    if replacement:
        parts.append(f"use '{replacement}' instead")
    if removal_version:
        parts.append(f"(planned removal in {removal_version})")
    return " - ".join(parts)


def warn_deprecated_flag(
    flag: str,
    replacement: str | None = None,
    removal_version: str | None = None,
    emit_console_hint: bool = True,
) -> None:
    """Emit a deprecation warning for a CLI flag (only once per process).

    Args:
        flag: The deprecated flag (e.g., ``--blacklist``)
        replacement: Optional suggested replacement flag
        removal_version: Optional future removal version (semantic)
        emit_console_hint: Whether to also print a user-facing hint (stdout)

    Returns:
        None
    """
    if _is_suppressed():
        return

    key = f"flag:{flag}"

    with _registry_lock:
        if key in _emitted:
            return
        _emitted.add(key)

    message = _format_flag_message(flag, replacement, removal_version)
    _message_cache[key] = message

    # Log with WARNING level (no f-strings inside logging call per project style)
    LOGGER.warning("Deprecation: %s", message)

    if emit_console_hint:
        _print_console_hint(message)


def _print_console_hint(message: str) -> None:
    """Print a console hint using color if available.

    Args:
        message: The message to display

    Returns:
        None
    """
    try:
        from .ui import create_progress_bar  # Local import to avoid circular load

        pb = create_progress_bar()
        colored = pb.color("yellow")(f"[DEPRECATION] {message}")
        print(colored)
    except Exception:
        # Fallback plain output
        print(f"[DEPRECATION] {message}")


def reset_deprecation_registry() -> None:
    """Reset the internal deprecation emission registry (testing utility).

    This function is intended for use in unit/integration tests to ensure
    each test can assert emission behavior deterministically.

    Returns:
        None
    """
    with _registry_lock:
        _emitted.clear()
        _message_cache.clear()


def get_emitted_deprecations() -> dict[str, str]:
    """Retrieve a mapping of emitted deprecation keys to messages.

    Returns:
        Dict[str, str]: Copy of internal message cache
    """
    with _registry_lock:
        return dict(_message_cache)


__all__ = [
    "DeprecationRecord",
    "warn_deprecated_flag",
    "reset_deprecation_registry",
    "get_emitted_deprecations",
]
