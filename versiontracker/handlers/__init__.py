"""Handlers for various VersionTracker commands.

This package contains modules that handle different CLI commands and operations
for VersionTracker. Each handler module is designed to encapsulate the logic
for a specific command or set of related commands.
"""

from versiontracker.handlers.app_handlers import handle_list_apps
from versiontracker.handlers.brew_handlers import (
    handle_list_brews,
    handle_brew_recommendations,
)
from versiontracker.handlers.config_handlers import handle_config_generation
from versiontracker.handlers.export_handlers import handle_export
from versiontracker.handlers.outdated_handlers import handle_outdated_check
from versiontracker.handlers.ui_handlers import get_status_icon, get_status_color

__all__ = [
    "handle_list_apps",
    "handle_list_brews",
    "handle_brew_recommendations",
    "handle_config_generation",
    "handle_export",
    "handle_outdated_check",
    "get_status_icon",
    "get_status_color",
]