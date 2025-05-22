"""Handlers for various VersionTracker commands.

This package contains modules that handle different CLI commands and operations
for VersionTracker. Each handler module is designed to encapsulate the logic
for a specific command or set of related commands, implementing the command pattern
design principle for better separation of concerns.

Args:
    None: This is a package, not a function.

Returns:
    None: This package doesn't return anything directly.
"""

from versiontracker.handlers.app_handlers import handle_list_apps
from versiontracker.handlers.brew_handlers import (
    handle_brew_recommendations,
    handle_list_brews,
)
from versiontracker.handlers.config_handlers import handle_config_generation
from versiontracker.handlers.export_handlers import handle_export
from versiontracker.handlers.filter_handlers import (
    handle_filter_management,
    handle_save_filter,
)
from versiontracker.handlers.outdated_handlers import handle_outdated_check
from versiontracker.handlers.setup_handlers import (
    handle_configure_from_options,
    handle_initialize_config,
    handle_setup_logging,
)
from versiontracker.handlers.ui_handlers import get_status_color, get_status_icon

__all__ = [
    "handle_list_apps",
    "handle_list_brews",
    "handle_brew_recommendations",
    "handle_config_generation",
    "handle_export",
    "handle_filter_management",
    "handle_save_filter",
    "handle_outdated_check",
    "handle_initialize_config",
    "handle_configure_from_options",
    "handle_setup_logging",
    "get_status_icon",
    "get_status_color",
]
