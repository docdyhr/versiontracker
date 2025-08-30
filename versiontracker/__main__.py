"""Main entry point for the VersionTracker application."""

import logging
import sys
from pathlib import Path

from versiontracker import __version__
from versiontracker.cli import get_arguments
from versiontracker.handlers import (
    handle_blacklist_auto_updates,
    handle_brew_recommendations,
    handle_config_generation,
    handle_configure_from_options,
    handle_filter_management,
    handle_initialize_config,
    handle_list_apps,
    handle_list_brews,
    handle_outdated_check,
    handle_save_filter,
    handle_setup_logging,
    handle_uninstall_auto_updates,
)
from versiontracker.profiling import (
    disable_profiling,
    enable_profiling,
    print_report,
    profile_function,
)
from versiontracker.ui import QueryFilterManager, create_progress_bar

# Import macOS handlers if available
_MACOS_HANDLERS_AVAILABLE = False
_MACOS_HANDLERS = {}
try:
    from versiontracker.handlers import (
        handle_install_service,
        handle_menubar_app,
        handle_service_status,
        handle_test_notification,
        handle_uninstall_service,
    )

    _MACOS_HANDLERS_AVAILABLE = True
    _MACOS_HANDLERS = {
        "install_service": handle_install_service,
        "uninstall_service": handle_uninstall_service,
        "service_status": handle_service_status,
        "test_notification": handle_test_notification,
        "menubar_app": handle_menubar_app,
    }
except ImportError:
    pass

# Logging, configuration, and filter management functions have been moved to handlers modules


def setup_logging(*args, **kwargs):
    """Stub for setup_logging to satisfy test patching in test_integration.py."""
    pass


def handle_main_actions(options) -> int:
    """Handle the main application actions based on parsed options.

    Args:
        options: Parsed command-line arguments

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Handle config generation first if requested
    if hasattr(options, "generate_config") and options.generate_config:
        return handle_config_generation(options)

    # Process the requested action
    if hasattr(options, "apps") and options.apps:
        result = handle_list_apps(options)
    elif hasattr(options, "brews") and options.brews:
        result = handle_list_brews(options)
    elif hasattr(options, "recom") and options.recom:
        # This is the default recommend option
        result = handle_brew_recommendations(options)
    elif hasattr(options, "strict_recom") and options.strict_recom:
        # This is the strict recommend option
        result = handle_brew_recommendations(options)
    elif hasattr(options, "check_outdated") and options.check_outdated:
        result = handle_outdated_check(options)
    elif (hasattr(options, "blocklist_auto_updates") and options.blocklist_auto_updates) or (
        hasattr(options, "blacklist_auto_updates") and options.blacklist_auto_updates
    ):
        # Unified handling for deprecated --blacklist-auto-updates and new --blocklist-auto-updates
        result = handle_blacklist_auto_updates(options)
    elif hasattr(options, "uninstall_auto_updates") and options.uninstall_auto_updates:
        result = handle_uninstall_auto_updates(options)
    elif hasattr(options, "install_service") and options.install_service:
        if _MACOS_HANDLERS_AVAILABLE and "install_service" in _MACOS_HANDLERS:
            result = _MACOS_HANDLERS["install_service"](options)
        else:
            print("macOS integration not available on this platform")
            return 1
    elif hasattr(options, "uninstall_service") and options.uninstall_service:
        if _MACOS_HANDLERS_AVAILABLE and "uninstall_service" in _MACOS_HANDLERS:
            result = _MACOS_HANDLERS["uninstall_service"](options)
        else:
            print("macOS integration not available on this platform")
            return 1
    elif hasattr(options, "service_status") and options.service_status:
        if _MACOS_HANDLERS_AVAILABLE and "service_status" in _MACOS_HANDLERS:
            result = _MACOS_HANDLERS["service_status"](options)
        else:
            print("macOS integration not available on this platform")
            return 1
    elif hasattr(options, "test_notification") and options.test_notification:
        if _MACOS_HANDLERS_AVAILABLE and "test_notification" in _MACOS_HANDLERS:
            result = _MACOS_HANDLERS["test_notification"](options)
        else:
            print("macOS integration not available on this platform")
            return 1
    elif hasattr(options, "menubar") and options.menubar:
        if _MACOS_HANDLERS_AVAILABLE and "menubar_app" in _MACOS_HANDLERS:
            result = _MACOS_HANDLERS["menubar_app"](options)
        else:
            print("macOS integration not available on this platform")
            return 1
    else:
        # No valid option selected
        print("No valid action specified. Use -h for help.")
        return 1

    return result


@profile_function("versiontracker_main")
def versiontracker_main() -> int:
    """Execute the main VersionTracker functionality.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Fast-path: support --version/-V without full argparse
    argv = sys.argv[1:]
    if "--version" in argv or "-V" in argv:
        print(f"versiontracker {__version__}")
        return 0

    # Parse arguments
    options = get_arguments()

    # Enable profiling if requested
    if hasattr(options, "profile") and options.profile:
        enable_profiling()

    # Set up logging
    handle_setup_logging(options)

    # Initialize configuration
    handle_initialize_config(options)

    # Configure settings from command-line options
    handle_configure_from_options(options)

    # Create filter manager
    filter_manager = QueryFilterManager(str(Path.home() / ".config" / "versiontracker"))

    # Handle filter management (list, delete, load)
    filter_result = handle_filter_management(options, filter_manager)
    if filter_result is not None:
        return filter_result

    try:
        # Handle main actions
        result = handle_main_actions(options)

        # Save filter if requested
        if hasattr(options, "save_filter") and options.save_filter:
            handle_save_filter(options, filter_manager)

        # Print performance report if profiling was enabled
        if hasattr(options, "profile") and options.profile:
            print_report(detailed=hasattr(options, "detailed_profile") and options.detailed_profile)
            disable_profiling()

        return result
    except Exception as e:
        logging.exception("An error occurred: %s", str(e))
        print(create_progress_bar().color("red")(f"Error: {str(e)}"))

        # Print performance report even on error if profiling was enabled
        if hasattr(options, "profile") and options.profile:
            print_report(detailed=False)
            disable_profiling()

        return 1


def main() -> int:
    """Execute the console script entry point.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    return versiontracker_main()


# Entry point for running as a script
if __name__ == "__main__":
    sys.exit(versiontracker_main())
