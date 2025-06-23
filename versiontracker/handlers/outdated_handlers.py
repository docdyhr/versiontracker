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
import sys
import time
import traceback
from typing import Any, Dict, List, Tuple, Union, cast

try:
    from tabulate import tabulate  # type: ignore[import]
except ImportError:
    # Fallback if tabulate is not installed
    def tabulate(  # type: ignore[misc]
        tabular_data: Any, headers: Any = (), tablefmt: Any = "simple", **kwargs: Any
    ) -> str:
        """Format tabular data into a string representation."""
        _ = tablefmt, kwargs  # Acknowledge unused parameters
        result = []
        if headers:  # Ensure headers is iterable and items are stringifiable
            header_line = " | ".join(str(h) for h in headers)
            if header_line:  # Only add header and separator if header_line is not empty
                result.append(header_line)
                result.append("-" * len(header_line))

        # Ensure tabular_data is iterable and its rows are iterable (if possible)
        if hasattr(tabular_data, "__iter__"):
            for row in tabular_data:
                if hasattr(row, "__iter__"):
                    result.append(" | ".join(str(cell) for cell in row))
                else:
                    # If a row is not iterable, convert it to string (simple fallback behavior)
                    result.append(str(row))
        elif tabular_data is not None:
            # If tabular_data itself is not iterable but not None, convert it to string
            result.append(str(tabular_data))

        return "\n".join(result)


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

# Import macOS notifications if available
try:
    from versiontracker.macos_integration import MacOSNotifications

    _MACOS_NOTIFICATIONS_AVAILABLE = True
except ImportError:
    _MACOS_NOTIFICATIONS_AVAILABLE = False

logger = logging.getLogger(__name__)


def _update_config_from_options(options: Any) -> None:
    """Update configuration based on command-line options.

    Args:
        options: Command line options
    """
    # Update config with no_progress option if specified
    if hasattr(options, "no_progress") and options.no_progress:
        config = get_config()
        if hasattr(config, "set"):
            config.set("no_progress", True)
            config.set("show_progress", False)


def _get_installed_applications() -> List[Tuple[str, str]]:
    """Get installed applications from the system.

    Returns:
        List of (app_name, version) tuples

    Raises:
        PermissionError: If there's an issue accessing application data
        TimeoutError: If operations time out
        Exception: For other unexpected errors
    """
    print(create_progress_bar().color("green")("Getting Apps from Applications/..."))

    apps_data = get_json_data(
        getattr(
            get_config(),
            "system_profiler_cmd",
            "system_profiler -json SPApplicationsDataType",
        )
    )
    return get_applications(apps_data)


def _get_homebrew_casks() -> List[str]:
    """Get installed Homebrew casks.

    Returns:
        List of installed brew cask names

    Raises:
        FileNotFoundError: If Homebrew is not installed
        PermissionError: If there's a permission issue
        Exception: For other unexpected errors
    """
    print(
        create_progress_bar().color("green")(
            "Getting installable casks from Homebrew..."
        )
    )
    return get_homebrew_casks()


def _filter_applications(
    apps: List[Tuple[str, str]], brews: List[str], include_brews: bool
) -> List[Tuple[str, str]]:
    """Filter applications based on whether they're managed by Homebrew.

    Args:
        apps: List of (app_name, version) tuples
        brews: List of brew cask names
        include_brews: Whether to include brew-managed apps

    Returns:
        Filtered list of applications
    """
    if not include_brews:
        try:
            return filter_out_brews(apps, brews)
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
    return apps


def _check_outdated_apps(
    apps: List[Tuple[str, str]], use_enhanced_matching: bool = True
) -> List[Tuple[str, Dict[str, str], Any]]:
    """Check which applications are outdated.

    Args:
        apps: List of (app_name, version) tuples
        use_enhanced_matching: Whether to use enhanced fuzzy matching

    Returns:
        List of (app_name, version_info, status) tuples

    Raises:
        TimeoutError: If operations time out
        NetworkError: If there are connectivity issues
        Exception: For other unexpected errors
    """
    batch_size = getattr(get_config(), "batch_size", 50)
    # Use cast to handle the return type properly
    return cast(
        List[Tuple[str, Dict[str, str], Any]],
        check_outdated_apps(
            apps, batch_size=batch_size, use_enhanced_matching=use_enhanced_matching
        ),
    )


def _process_outdated_info(
    outdated_info: List[Tuple[str, Dict[str, str], Any]],
) -> Tuple[List[List[Union[str, Any]]], Dict[str, int]]:
    """Process outdated information into a table and counters.

    Args:
        outdated_info: List of (app_name, version_info, status) tuples

    Returns:
        Tuple of (table_rows, status_counts)
    """
    table = []
    status_counts = {
        "outdated": 0,
        "uptodate": 0,
        "not_found": 0,
        "error": 0,
        "unknown": 0,
    }

    for app_name, version_info, status in outdated_info:
        icon = get_status_icon(str(status))
        color = get_status_color(str(status))

        if status == "outdated":
            status_counts["outdated"] += 1
        elif status == "uptodate":
            status_counts["uptodate"] += 1
        elif status == "not_found":
            status_counts["not_found"] += 1
        elif status == "error":
            status_counts["error"] += 1
        else:
            status_counts["unknown"] += 1

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
    return table, status_counts


def _display_results(
    table: List[List[Union[str, Any]]],
    status_counts: Dict[str, int],
    app_count: int,
    elapsed_time: float,
) -> None:
    """Display results table and summary.

    Args:
        table: Table rows to display
        status_counts: Dictionary of status counts
        app_count: Total number of applications checked
        elapsed_time: Time taken to check for updates
    """
    if not table:
        print(create_progress_bar().color("yellow")("No applications found."))
        return

    # Print summary information about processing
    print("")
    print(
        create_progress_bar().color("green")(
            f"✓ Processed {app_count} applications in {elapsed_time:.1f} seconds"
        )
    )

    # Print status summary with counts and colors
    print(create_progress_bar().color("green")("\nStatus Summary:"))
    print(
        f" {create_progress_bar().color('green')('✓')} Up to date: {create_progress_bar().color('green')(str(status_counts['uptodate']))}"
    )
    print(
        f" {create_progress_bar().color('red')('!')} Outdated: {create_progress_bar().color('red')(str(status_counts['outdated']))}"
    )
    print(
        f" {create_progress_bar().color('yellow')('?')} Unknown: {create_progress_bar().color('yellow')(str(status_counts['unknown']))}"
    )
    print(
        f" {create_progress_bar().color('blue')('❓')} Not Found: {create_progress_bar().color('blue')(str(status_counts['not_found']))}"
    )
    print(
        f" {create_progress_bar().color('red')('❌')} Error: {create_progress_bar().color('red')(str(status_counts['error']))}"
    )
    print("")

    # Print the table with headers
    headers = ["", "Application", "Installed Version", "Latest Version"]
    print(tabulate(table, headers=headers, tablefmt="pretty"))

    if status_counts["outdated"] > 0:
        print(
            create_progress_bar().color("red")(
                f"\nFound {status_counts['outdated']} outdated applications."
            )
        )
    else:
        print(
            create_progress_bar().color("green")("\nAll applications are up to date!")
        )


def _send_notification_if_available(
    outdated_info: List[Tuple[str, Dict[str, str], str]], status_counts: Dict[str, int]
) -> None:
    """Send notification about outdated applications if macOS notifications are available.

    Args:
        outdated_info: List of (app_name, version_info, status) tuples
        status_counts: Dictionary with counts of different status types
    """
    if not _MACOS_NOTIFICATIONS_AVAILABLE:
        print(
            create_progress_bar().color("yellow")(
                "macOS notifications not available on this platform"
            )
        )
        return

    if sys.platform != "darwin":
        print(
            create_progress_bar().color("yellow")(
                "macOS notifications only available on macOS"
            )
        )
        return

    try:
        # Prepare list of outdated applications for notification
        outdated_apps = []
        for app_name, version_info, status in outdated_info:
            if status == "outdated":
                outdated_apps.append(
                    {
                        "name": app_name,
                        "installed": version_info.get("installed", "Unknown"),
                        "latest": version_info.get("latest", "Unknown"),
                    }
                )

        # Send notification
        success = MacOSNotifications.notify_outdated_apps(outdated_apps)

        if success:
            print(
                create_progress_bar().color("green")(
                    "✅ Notification sent successfully"
                )
            )
        else:
            print(
                create_progress_bar().color("yellow")("⚠️  Failed to send notification")
            )

    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        print(
            create_progress_bar().color("yellow")(
                f"Warning: Failed to send notification: {e}"
            )
        )


def _export_data(
    outdated_info: List[Tuple[str, Dict[str, str], str]], options: Any
) -> int:
    """Export data to the specified format.

    Args:
        outdated_info: List of (app_name, version_info, status) tuples
        options: Command line options

    Returns:
        int: Exit code (0 for success, 1 for failure)

    Raises:
        ExportError: If there's an error during export
    """
    export_result = handle_export(
        outdated_info,
        options.export_format,
        options.output_file if hasattr(options, "output_file") else None,
    )

    if not hasattr(options, "output_file") or not options.output_file:
        if isinstance(export_result, str):
            print(export_result)

    return 0


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
        # Update configuration from options
        _update_config_from_options(options)

        # Get installed applications
        try:
            apps = _get_installed_applications()
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
        try:
            brews = _get_homebrew_casks()
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

        # Filter applications based on Homebrew management
        include_brews = getattr(options, "include_brews", False)
        apps = _filter_applications(apps, brews, include_brews)

        # Print status update and prepare for checking outdated apps
        print(
            create_progress_bar().color("green")(
                f"Checking {len(apps)} applications for updates..."
            )
        )
        start_time = time.time()

        # Check outdated status
        try:
            # Determine if enhanced matching should be used
            use_enhanced_matching = not getattr(options, "no_enhanced_matching", False)
            outdated_info = _check_outdated_apps(apps, use_enhanced_matching)
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

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        # Process results and display
        table, status_counts = _process_outdated_info(outdated_info)
        _display_results(table, status_counts, len(apps), elapsed_time)

        # Send notification if requested
        if hasattr(options, "notify") and options.notify:
            _send_notification_if_available(outdated_info, status_counts)

        # Export if requested
        if hasattr(options, "export_format") and options.export_format:
            try:
                return _export_data(outdated_info, options)
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
