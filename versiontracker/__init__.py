"""VersionTracker - CLI versiontracker and update tool for macOS.

This package provides tools to track and manage application versions on macOS,
with a focus on applications installed outside of the App Store. It helps
identify which applications can be managed via Homebrew, checks for outdated
applications, and provides recommendations for better application management.

Key features:
- List applications in /Applications/ not updated by the App Store
- List all currently installed Homebrew casks
- Recommend which applications could be managed through Homebrew
- Check for outdated applications by comparing with latest Homebrew versions
- Export results in machine-readable formats (JSON and CSV)

This package is designed for macOS users who want to keep their applications
up to date and well-managed, especially those who use a mix of App Store and
non-App Store applications.

Main components:
- apps.py: Core functionality for application discovery and version checking
- cli.py: Command-line interface parsing and handling
- config.py: Configuration management and validation
- handlers/: Command handler implementations
- ui.py: User interface components including progress bars and colored output

For detailed usage instructions, see the README.md or run:
    versiontracker --help

Note: This module uses lazy loading via __getattr__ to avoid importing heavy
submodules until they are actually needed. All exports listed in __all__ are
available but loaded on-demand.
"""

from typing import Any

__version__ = "0.7.0"

# Explicitly define what should be imported with "from versiontracker import *"
# Note: Items marked with lazy loading are imported on-demand via __getattr__
# The following items are available through lazy loading but trigger false positive warnings
__all__ = [
    "__version__",
    "get_applications",  # type: ignore[attr-defined]  # Lazy loaded from .apps
    "get_homebrew_casks",  # type: ignore[attr-defined]  # Lazy loaded from .apps
    "Config",  # type: ignore[attr-defined]  # Lazy loaded from .config
    "get_config",  # type: ignore[attr-defined]  # Lazy loaded from .config
    "VersionTrackerError",  # type: ignore[attr-defined]  # Lazy loaded from .exceptions
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
