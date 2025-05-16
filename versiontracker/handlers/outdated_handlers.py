"""Outdated check handlers for VersionTracker.

This module contains handler functions for checking outdated applications
in VersionTracker. It provides functionality to compare installed application
versions with the latest available versions from Homebrew.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

import logging
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union

from tabulate import tabulate

from versiontracker.apps import (
    filter_out_brews,
    get_applications,
    get_homebrew_casks,
)
from versiontracker.config import get_config
from versiontracker.exceptions import ConfigError, ExportError, NetworkError
from versiontracker.handlers.export_handlers import handle_export
from versiontracker.handlers.ui_handlers import get_status_color, get_status_icon
from versiontracker.ui import create_progress_bar
from versiontracker.utils import get_json_data
from versiontracker.version import check_outdated_apps


def handle_outdated_check(options: Any) -> int:
    """Handle checking for outdated applications.
    
    Compares installed application versions with the latest available versions
    and displays a summary of which applications need updates. Can export
    results in various formats.

    Args:
        options: Command line options containing parameters like no_progress,
                include_brews, export_format, and output_file.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
        
    Raises:
        PermissionError: If there's an issue accessing application data
        TimeoutError: If operations time out
        NetworkError: If there are connectivity issues
        ConfigError: If there's a configuration error
        ExportError: If there's an error during export
        Exception: For other unexpected errors
    """
    try:
        # Update config with no_progress option if specified
        if hasattr(options, "no_progress") and options.no_progress:
            get_config().no_progress = True
            get_config().show_progress = False

        # Get installed applications
        print(
            create_progress_bar().color("green")("Getting Apps from Applications/...")
        )
        try:
            apps_data = get_json_data(
                getattr(
                    get_config(),
                    "system_profiler_cmd",
                    "system_profiler -json SPApplicationsDataType",
                )
            )
            apps = get_applications(apps_data)
        except PermissionError:
            print(
                create_progress_bar().color("red")(
                    "Error: Permission denied when reading application data."
                )
            )
            print(
                create_progress_bar().color("yellow")(
                    "Try running the command with sudo or check your file permissions."
                )
            )
            return 1
        except TimeoutError:
            print(
                create_progress_bar().color("red")(
                    "Error: Timed out while reading application data."
                )
            )
            print(
                create_progress_bar().color("yellow")(
                    "Check your system load and try again later."
                )
            )
            return 1
        except Exception as e:
            print(
                create_progress_bar().color("red")(
                    f"Error: Failed to get installed applications: {e}"
                )
            )
            return 1

        # Get installed Homebrew casks
        print(
            create_progress_bar().color("green")(
                "Getting installable casks from Homebrew..."
            )
        )
        try:
            brews = get_homebrew_casks()
        except FileNotFoundError:
            print(
                create_progress_bar().color("red")(
                    "Error: Homebrew executable not found."
                )
            )
            print(
                create_progress_bar().color("yellow")(
                    "Please make sure Homebrew is installed and properly configured."
                )
            )
            return 1
        except PermissionError:
            print(
                create_progress_bar().color("red")(
                    "Error: Permission denied when accessing Homebrew."
                )
            )
            print(
                create_progress_bar().color("yellow")(
                    "Check your user permissions and Homebrew installation."
                )
            )
            return 1
        except Exception as e:
            print(
                create_progress_bar().color("red")(
                    f"Error: Failed to get Homebrew casks: {e}"
                )
            )
            return 1

        # Filter out applications already managed by Homebrew
        include_brews = getattr(options, "include_brews", False)
        if not include_brews:
            try:
                apps = filter_out_brews(apps, brews)
            except Exception as e:
                print(
                    create_progress_bar().color("yellow")(
                        f"Warning: Error filtering applications: {e}"
                    )
                )
                print(
                    create_progress_bar().color("yellow")(
                        "Proceeding with all applications."
                    )
                )

        # Print status update
        print(
            create_progress_bar().color("green")(
                f"Checking {len(apps)} applications for updates..."
            )
        )

        # Start time for tracking
        start_time = time.time()

        # Check outdated status
        try:
            batch_size = getattr(get_config(), "batch_size", 50)
            outdated_info = check_outdated_apps(apps, batch_size=batch_size)
        except TimeoutError:
            print(
                create_progress_bar().color("red")(
                    "Error: Network timeout while checking for updates."
                )
            )
            print(
                create_progress_bar().color("yellow")(
                    "Check your internet connection and try again."
                )
            )
            return 1
        except NetworkError:
            print(
                create_progress_bar().color("red")(
                    "Error: Network error while checking for updates."
                )
            )
            print(
                create_progress_bar().color("yellow")(
                    "Check your internet connection and try again."
                )
            )
            return 1
        except Exception as e:
            print(
                create_progress_bar().color("red")(
                    f"Error: Failed to check for updates: {e}"
                )
            )
            return 1

        # End time and calculation
        elapsed_time = time.time() - start_time

        # Prepare results table
        table = []
        total_outdated = 0
        total_up_to_date = 0
        total_unknown = 0
        total_not_found = 0
        total_error = 0

        for app_name, version_info, status in outdated_info:
            icon = get_status_icon(str(status))
            color = get_status_color(str(status))

            if status == "outdated":
                total_outdated += 1
            elif status == "uptodate":
                total_up_to_date += 1
            elif status == "not_found":
                total_not_found += 1
            elif status == "error":
                total_error += 1
            else:
                total_unknown += 1

            # Add row to table with colored status
            installed_version = (
                version_info["installed"] if "installed" in version_info else "Unknown"
            )
            latest_version = (
                version_info["latest"] if "latest" in version_info else "Unknown"
            )

            table.append(
                [
                    icon,
                    app_name,
                    color(installed_version),
                    color(latest_version),
                ]
            )

        # Sort table by application name
        table.sort(key=lambda x: x[1].lower())

        # Print results
        if table:
            # Print summary information about processing
            print("")
            print(
                create_progress_bar().color("green")(
                    f"✓ Processed {len(apps)} applications in {elapsed_time:.1f} seconds"
                )
            )

            # Print status summary with counts and colors
            print(create_progress_bar().color("green")("\nStatus Summary:"))
            print(
                f" {create_progress_bar().color('green')('✓')} Up to date: {create_progress_bar().color('green')(str(total_up_to_date))}"
            )
            print(
                f" {create_progress_bar().color('red')('!')} Outdated: {create_progress_bar().color('red')(str(total_outdated))}"
            )
            print(
                f" {create_progress_bar().color('yellow')('?')} Unknown: {create_progress_bar().color('yellow')(str(total_unknown))}"
            )
            print(
                f" {create_progress_bar().color('blue')('❓')} Not Found: {create_progress_bar().color('blue')(str(total_not_found))}"
            )
            print(
                f" {create_progress_bar().color('red')('❌')} Error: {create_progress_bar().color('red')(str(total_error))}"
            )
            print("")

            # Print the table with headers
            headers = ["", "Application", "Installed Version", "Latest Version"]
            print(tabulate(table, headers=headers, tablefmt="pretty"))

            if total_outdated > 0:
                print(
                    create_progress_bar().color("red")(
                        f"\nFound {total_outdated} outdated applications."
                    )
                )
            else:
                print(
                    create_progress_bar().color("green")(
                        "\nAll applications are up to date!"
                    )
                )
        else:
            print(create_progress_bar().color("yellow")("No applications found."))

        # Export if requested
        if hasattr(options, "export_format") and options.export_format:
            try:
                export_result = handle_export(
                    outdated_info,
                    options.export_format,
                    options.output_file if hasattr(options, "output_file") else None,
                )
                if not options.output_file and isinstance(export_result, str):
                    print(export_result)
                return 0
            except ExportError as e:
                print(create_progress_bar().color("red")(f"Error exporting data: {e}"))
                return 1

        return 0
    except ConfigError as e:
        print(create_progress_bar().color("red")(f"Configuration Error: {e}"))
        print(
            create_progress_bar().color("yellow")(
                "Please check your configuration file and try again."
            )
        )
        return 1
    except KeyboardInterrupt:
        print(create_progress_bar().color("yellow")("\nOperation canceled by user."))
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logging.error(f"Error checking outdated applications: {e}")
        print(create_progress_bar().color("red")(f"Error: {e}"))
        if get_config().debug:
            traceback.print_exc()
        else:
            print(
                create_progress_bar().color("yellow")(
                    "Run with --debug for more information."
                )
            )
        return 1