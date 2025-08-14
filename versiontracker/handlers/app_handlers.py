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

from versiontracker.app_finder import (
    filter_out_brews,
    get_applications,
    get_homebrew_casks,
)
from versiontracker.config import Config, get_config
from versiontracker.handlers.export_handlers import handle_export
from versiontracker.ui import create_progress_bar
from versiontracker.utils import get_json_data


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

        # Get app data
        print(create_progress_bar().color("green")("Getting application data..."))

        # Get data from system_profiler
        apps_data = get_json_data(
            getattr(
                get_config(),
                "system_profiler_cmd",
                "system_profiler -json SPApplicationsDataType",
            )
        )

        # Get applications
        apps = get_applications(apps_data)

        # Get additional paths if specified
        if getattr(options, "additional_dirs", None):
            options.additional_dirs.split(",")

        # Apply filtering
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
            filtered_apps = [(app, ver) for app, ver in apps if not temp_config.is_blocklisted(app)]
        else:
            # Use global config for blocklisting
            filtered_apps = [(app, ver) for app, ver in apps if not get_config().is_blocklisted(app)]

        # Get Homebrew casks if needed for filtering
        if hasattr(options, "brew_filter") and options.brew_filter:
            print(create_progress_bar().color("green")("Getting Homebrew casks for filtering..."))
            brews = get_homebrew_casks()
            include_brews = getattr(options, "include_brews", False)
            if not include_brews:
                filtered_apps = filter_out_brews(filtered_apps, brews)
            else:
                print(
                    create_progress_bar().color("yellow")(
                        "Showing all applications (including those managed by Homebrew)"
                    )
                )

        # Prepare table data
        table = []
        for app, version in sorted(filtered_apps, key=lambda x: x[0].lower()):
            table.append(
                [
                    create_progress_bar().color("green")(app),
                    create_progress_bar().color("blue")(version),
                ]
            )

        # Display results
        if table:
            print(create_progress_bar().color("green")("\nFound {} applications:\n".format(len(table))))
            print(tabulate(table, headers=["Application", "Version"], tablefmt="pretty"))
        else:
            print(create_progress_bar().color("yellow")("\nNo applications found matching the criteria."))

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

        return 0
    except Exception as e:
        logging.error(f"Error listing applications: {e}")
        traceback.print_exc()
        return 1
