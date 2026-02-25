"""VersionTracker - Application version management for macOS.

A command-line tool for tracking and managing applications installed
outside of the Mac App Store, with Homebrew cask integration.
"""

from typing import Any

__version__ = "0.8.2"

from versiontracker.config import Config, get_config
from versiontracker.exceptions import (
    ApplicationError,
    CacheError,
    ConfigError,
    HandlerError,
    HomebrewError,
    NetworkError,
    TimeoutError,
    VersionError,
    VersionTrackerError,
)
from versiontracker.version import (
    compare_versions,
    is_version_newer,
    parse_version,
)

__all__ = [
    "__version__",
    "Config",
    "get_config",
    "VersionTrackerError",
    "ConfigError",
    "VersionError",
    "NetworkError",
    "TimeoutError",
    "HomebrewError",
    "ApplicationError",
    "CacheError",
    "HandlerError",
    "parse_version",
    "compare_versions",
    "is_version_newer",
]


def __getattr__(name: str) -> Any:
    """Lazily import heavy submodules on demand.

    This function is called when an attribute is not found in the module's
    namespace. It allows us to defer imports of heavy modules (like apps.py)
    until they are actually needed, improving startup time.

    Args:
        name: The name of the attribute being accessed

    Returns:
        The requested attribute/function/class

    Raises:
        AttributeError: If the requested attribute is not available
    """
    if name in {"get_applications", "get_homebrew_casks"}:
        from .apps import get_applications, get_homebrew_casks

        globals().update(
            {
                "get_applications": get_applications,
                "get_homebrew_casks": get_homebrew_casks,
            }
        )
        return globals()[name]

    if name in {"Config", "get_config"}:
        from .config import Config, get_config

        globals().update({"Config": Config, "get_config": get_config})
        return globals()[name]

    if name == "VersionTrackerError":
        from .exceptions import VersionTrackerError

        globals()["VersionTrackerError"] = VersionTrackerError
        return VersionTrackerError

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
