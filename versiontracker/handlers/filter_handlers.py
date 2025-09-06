"""Filter handlers for VersionTracker.

This module contains handler functions for filter management commands
in VersionTracker, allowing users to save, load, list, and delete
query filters.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

import logging
from typing import Any

from versiontracker.config import get_config
from versiontracker.ui import QueryFilterManager, create_progress_bar


def _handle_list_filters(filter_manager: QueryFilterManager) -> int:
    """Handle listing available filters.

    Args:
        filter_manager: The filter manager instance

    Returns:
        Exit code (0 for success)
    """
    filters = filter_manager.list_filters()
    if filters:
        print(create_progress_bar().color("green")("Available filters:"))
        for i, filter_name in enumerate(filters, 1):
            print(f"{i}. {filter_name}")
    else:
        print(create_progress_bar().color("yellow")("No saved filters found."))
    return 0


def _handle_delete_filter(filter_name: str, filter_manager: QueryFilterManager) -> int:
    """Handle deleting a filter.

    Args:
        filter_name: Name of filter to delete
        filter_manager: The filter manager instance

    Returns:
        Exit code (0 for success)
    """
    if filter_manager.delete_filter(filter_name):
        print(create_progress_bar().color("green")(f"Filter '{filter_name}' deleted successfully."))
    else:
        print(create_progress_bar().color("red")(f"Filter '{filter_name}' not found."))
    return 0


def _apply_filter_to_options(filter_data: dict[str, Any], options: Any) -> None:
    """Apply filter settings to options object.

    Args:
        filter_data: Filter data dictionary
        options: Command line options object
    """
    for key, value in filter_data.items():
        if hasattr(options, key):
            setattr(options, key, value)


def _apply_filter_to_config(filter_data: dict[str, Any]) -> None:
    """Apply filter settings to configuration.

    Args:
        filter_data: Filter data dictionary
    """
    if "config" in filter_data:
        config = get_config()
        for key, value in filter_data["config"].items():
            if key in config._config:
                config._config[key] = value


def _handle_load_filter(filter_name: str, filter_manager: QueryFilterManager, options: Any) -> int | None:
    """Handle loading a filter.

    Args:
        filter_name: Name of filter to load
        filter_manager: The filter manager instance
        options: Command line options object

    Returns:
        None for success (to continue execution), 1 for failure
    """
    filter_data = filter_manager.load_filter(filter_name)
    if filter_data:
        print(create_progress_bar().color("green")(f"Loaded filter: {filter_name}"))
        _apply_filter_to_options(filter_data, options)
        _apply_filter_to_config(filter_data)
        return None  # Continue execution - don't exit early
    else:
        print(create_progress_bar().color("red")(f"Filter '{filter_name}' not found."))
        return 1


def handle_filter_management(options: Any, filter_manager: QueryFilterManager) -> int | None:
    """Handle filter management operations.

    Args:
        options: Command line options
        filter_manager: The filter manager instance

    Returns:
        int: Exit code if a filter operation was handled, None otherwise
    """
    # List filters
    if hasattr(options, "list_filters") and options.list_filters:
        return _handle_list_filters(filter_manager)

    # Delete filter
    if hasattr(options, "delete_filter") and options.delete_filter:
        return _handle_delete_filter(options.delete_filter, filter_manager)

    # Load filter
    if hasattr(options, "load_filter") and options.load_filter:
        return _handle_load_filter(options.load_filter, filter_manager, options)

    return None


def handle_save_filter(options: Any, filter_manager: QueryFilterManager) -> int:
    """Save the current settings as a filter.

    Args:
        options: Command line options
        filter_manager: The filter manager instance

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        if hasattr(options, "save_filter") and options.save_filter:
            filter_name = options.save_filter

            # Collect filter settings
            filter_data = {}
            # Add relevant options to filter data (exclude command-specific ones)
            for opt in dir(options):
                if opt.startswith("_") or opt in (
                    "command",
                    "save_filter",
                    "load_filter",
                    "list_filters",
                    "delete_filter",
                ):
                    continue
                filter_data[opt] = getattr(options, opt)

            # Add relevant config settings
            filter_data["config"] = {
                "ui": get_config()._config.get("ui", {}),
                "rate_limit": get_config()._config.get("rate_limit", 3),
                "max_workers": get_config()._config.get("max_workers", 10),
            }

            # Save the filter
            if filter_manager.save_filter(filter_name, filter_data):
                print(create_progress_bar().color("green")(f"Filter '{filter_name}' saved successfully."))
                return 0
            else:
                print(create_progress_bar().color("red")(f"Failed to save filter '{filter_name}'."))
                return 1
        return 0
    except Exception as e:
        logging.error(f"Error saving filter: {str(e)}")
        print(create_progress_bar().color("red")(f"Error saving filter: {str(e)}"))
        return 1
