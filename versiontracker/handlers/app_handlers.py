"""Application handlers for VersionTracker.

This module contains handler functions for the application listing
commands of VersionTracker.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

import logging
import traceback
from typing import Any

from tabulate import tabulate

from versiontracker.apps import (
    filter_out_brews,
    get_applications,
    get_homebrew_casks,
)
from versiontracker.config import Config, get_config
from versiontracker.handlers.export_handlers import handle_export
from versiontracker.ui import create_progress_bar
from versiontracker.utils import get_json_data


def _get_apps_data() -> list[tuple[str, str]]:
    """Get application data from system profiler.

    Returns:
        List of (app_name, version) tuples
    """
    print(create_progress_bar().color("green")("Getting application data..."))
    apps_data = get_json_data(
        getattr(
            get_config(),
            "system_profiler_cmd",
            "system_profiler -json SPApplicationsDataType",
        )
    )
    return get_applications(apps_data)


def _apply_blocklist_filtering(apps: list[tuple[str, str]], options: Any) -> list[tuple[str, str]]:
    """Apply blocklist/blacklist filtering to applications.

    Args:
        apps: List of (app_name, version) tuples
        options: Command line options

    Returns:
        Filtered list of (app_name, version) tuples
    """
    blocklist_value = getattr(options, "blocklist", None)
    blacklist_value = getattr(options, "blacklist", None)

    if blocklist_value or blacklist_value:
        # Create a temporary config with the specified blocklist / legacy blacklist
        temp_config = Config()
        # Prefer explicit --blocklist over deprecated --blacklist
        provided = []
        if blocklist_value and isinstance(blocklist_value, str):
            provided.extend(blocklist_value.split(","))
        if blacklist_value and isinstance(blacklist_value, str):
            # Merge while preserving order; avoid duplicates
            for item in blacklist_value.split(","):
                if item not in provided:
                    provided.append(item)
        temp_config.set("blacklist", provided)  # config validator currently keyed on 'blacklist'
        return [(app, ver) for app, ver in apps if not temp_config.is_blocklisted(app)]
    else:
        # Use global config for blocklisting
        return [(app, ver) for app, ver in apps if not get_config().is_blocklisted(app)]


def _apply_homebrew_filtering(apps: list[tuple[str, str]], options: Any) -> list[tuple[str, str]]:
    """Apply Homebrew filtering to applications.

    Args:
        apps: List of (app_name, version) tuples
        options: Command line options

    Returns:
        Filtered list of (app_name, version) tuples
    """
    if hasattr(options, "brew_filter") and options.brew_filter:
        print(create_progress_bar().color("green")("Getting Homebrew casks for filtering..."))
        brews = get_homebrew_casks()
        include_brews = getattr(options, "include_brews", False)
        if not include_brews:
            return filter_out_brews(apps, brews)
        else:
            print(
                create_progress_bar().color("yellow")("Showing all applications (including those managed by Homebrew)")
            )
    return apps


def _display_results_table(filtered_apps: list[tuple[str, str]]) -> None:
    """Display applications in a formatted table.

    Args:
        filtered_apps: List of (app_name, version) tuples
    """
    table = []
    for app, version in sorted(filtered_apps, key=lambda x: x[0].lower()):
        table.append(
            [
                create_progress_bar().color("green")(app),
                create_progress_bar().color("blue")(version),
            ]
        )

    if table:
        print(create_progress_bar().color("green")(f"\nFound {len(table)} applications:\n"))
        print(tabulate(table, headers=["Application", "Version"], tablefmt="pretty"))
    else:
        print(create_progress_bar().color("yellow")("\nNo applications found matching the criteria."))


def handle_list_apps(options: Any) -> int:
    """Handle listing applications.

    Retrieves and displays installed applications.
    Can filter by blocklist (preferred, legacy: blacklist), Homebrew management, and more.

    Args:
        options: Command line options containing parameters like blocklist/blacklist,
                brew_filter, include_brews, export_format, and output_file.

    Returns:
        int: Exit code (0 for success, non-zero for failure)

    Raises:
        Exception: For errors retrieving or processing application data
    """
    try:
        logging.info("Starting VersionTracker list command")

        # Get application data
        apps = _get_apps_data()

        # Get additional paths if specified (currently unused)
        if getattr(options, "additional_dirs", None):
            options.additional_dirs.split(",")

        # Apply filtering
        filtered_apps = _apply_blocklist_filtering(apps, options)
        filtered_apps = _apply_homebrew_filtering(filtered_apps, options)

        # Display results
        _display_results_table(filtered_apps)

        # Export if requested
        if hasattr(options, "export_format") and options.export_format:
            export_result = handle_export(
                [{"name": app, "version": ver} for app, ver in filtered_apps],
                options.export_format,
                getattr(options, "output_file", None),
            )
            if isinstance(export_result, str):
                print(export_result)

        return 0
    except Exception as e:
        logging.error("Error listing applications: %s", e)
        traceback.print_exc()
        return 1
