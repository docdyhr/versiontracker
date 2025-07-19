"""Handlers for various VersionTracker commands.

This package contains modules that handle different CLI commands and operations
for VersionTracker. Each handler module is designed to encapsulate the logic
for a specific command or set of related commands, implementing the command pattern
design principle for better separation of concerns.
"""

# Import handlers from submodules for easier access
from versiontracker.handlers.app_handlers import handle_list_apps
from versiontracker.handlers.auto_update_handlers import (
    handle_blacklist_auto_updates,
    handle_list_auto_updates,
    handle_uninstall_auto_updates,
)
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

# Import macOS handlers only if available
try:
    from versiontracker.handlers.macos_handlers import (
        handle_install_service,
        handle_menubar_app,
        handle_service_status,
        handle_test_notification,
        handle_uninstall_service,
    )

    _MACOS_HANDLERS_AVAILABLE = True
except ImportError:
    _MACOS_HANDLERS_AVAILABLE = False

__all__ = [
    "handle_list_apps",
    "handle_list_brews",
    "handle_brew_recommendations",
    "handle_blacklist_auto_updates",
    "handle_uninstall_auto_updates",
    "handle_list_auto_updates",
    "handle_config_generation",
    "handle_export",
    "handle_filter_management",
    "handle_save_filter",
    "handle_outdated_check",
    "handle_initialize_config",
    "handle_configure_from_options",
    "handle_setup_logging",
]

# Add macOS handlers to __all__ if available
if _MACOS_HANDLERS_AVAILABLE:
    __all__.extend(
        [
            "handle_install_service",
            "handle_uninstall_service",
            "handle_service_status",
            "handle_test_notification",
            "handle_menubar_app",
        ]
    )
