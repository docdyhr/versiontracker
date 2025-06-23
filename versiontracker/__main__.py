"""Main entry point for the VersionTracker application."""

import logging
import sys
from pathlib import Path

from versiontracker.cli import get_arguments
from versiontracker.handlers import (
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
)

# Import macOS handlers if available
try:
    from versiontracker.handlers import (
        handle_install_service,
        handle_menubar_app,
        handle_service_status,
        handle_test_notification,
        handle_uninstall_service,
    )

    _MACOS_HANDLERS_AVAILABLE = True
except ImportError:
    _MACOS_HANDLERS_AVAILABLE = False
from versiontracker.profiling import (
    disable_profiling,
    enable_profiling,
    print_report,
    profile_function,
)
from versiontracker.ui import QueryFilterManager, create_progress_bar

# Logging, configuration, and filter management functions have been moved to handlers modules


def setup_logging(*args, **kwargs):
    """Stub for setup_logging to satisfy test patching in test_integration.py."""
    pass


@profile_function("versiontracker_main")
def versiontracker_main() -> int:
    """Execute the main VersionTracker functionality.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
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
        elif hasattr(options, "install_service") and options.install_service:
            if _MACOS_HANDLERS_AVAILABLE:
                result = handle_install_service(options)
            else:
                print("macOS integration not available on this platform")
                return 1
        elif hasattr(options, "uninstall_service") and options.uninstall_service:
            if _MACOS_HANDLERS_AVAILABLE:
                result = handle_uninstall_service(options)
            else:
                print("macOS integration not available on this platform")
                return 1
        elif hasattr(options, "service_status") and options.service_status:
            if _MACOS_HANDLERS_AVAILABLE:
                result = handle_service_status(options)
            else:
                print("macOS integration not available on this platform")
                return 1
        elif hasattr(options, "test_notification") and options.test_notification:
            if _MACOS_HANDLERS_AVAILABLE:
                result = handle_test_notification(options)
            else:
                print("macOS integration not available on this platform")
                return 1
        elif hasattr(options, "menubar") and options.menubar:
            if _MACOS_HANDLERS_AVAILABLE:
                result = handle_menubar_app(options)
            else:
                print("macOS integration not available on this platform")
                return 1
        else:
            # No valid option selected
            print("No valid action specified. Use -h for help.")
            return 1

        # Save filter if requested
        if hasattr(options, "save_filter") and options.save_filter:
            handle_save_filter(options, filter_manager)

        # Print performance report if profiling was enabled
        if hasattr(options, "profile") and options.profile:
            print_report(
                detailed=hasattr(options, "detailed_profile")
                and options.detailed_profile
            )
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
