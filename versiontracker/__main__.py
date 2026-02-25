"""Main entry point for the VersionTracker application."""

import logging
import sys
from pathlib import Path
from typing import Any

from versiontracker import __version__
from versiontracker.cli import get_arguments
from versiontracker.deprecation import warn_deprecated_flag
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


def setup_logging(*args: Any, **kwargs: Any) -> None:
    """Stub for setup_logging to satisfy test patching in test_integration.py."""
    pass


def _check_ml_availability() -> None:
    """Check ML feature availability and inform user if unavailable.

    This function is called at runtime only when needed (debug mode),
    avoiding top-level import failures that could crash the CLI.
    """
    try:
        from versiontracker.ml import is_ml_available

        if not is_ml_available():
            logging.info("ML features are not available. Install with: pip install homebrew-versiontracker[ml]")
    except ImportError:
        logging.info("ML features are not available. Install with: pip install homebrew-versiontracker[ml]")


def _handle_macos_service_action(options: Any, action_name: str) -> int:
    """Handle macOS service actions (install, uninstall, status, test_notification, menubar).

    Args:
        options: Parsed command-line arguments
        action_name: The action name to look up in _MACOS_HANDLERS

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    if _MACOS_HANDLERS_AVAILABLE and action_name in _MACOS_HANDLERS:
        return _MACOS_HANDLERS[action_name](options)
    else:
        print("macOS integration not available on this platform")
        return 1


def _get_basic_action_result(options: Any) -> int | None:
    """Get result for basic application actions.

    Args:
        options: Parsed command-line arguments

    Returns:
        int | None: Result code or None if no basic action matched
    """
    if options.apps:
        return handle_list_apps(options)
    elif options.brews:
        return handle_list_brews(options)
    elif options.recom:
        return handle_brew_recommendations(options)
    elif options.strict_recom:
        return handle_brew_recommendations(options)
    elif options.check_outdated:
        return handle_outdated_check(options)
    return None


def _get_auto_update_action_result(options: Any) -> int | None:
    """Get result for auto-update actions.

    Args:
        options: Parsed command-line arguments

    Returns:
        int | None: Result code or None if no auto-update action matched
    """
    if options.blocklist_auto_updates or options.blacklist_auto_updates:
        return handle_blacklist_auto_updates(options)
    elif options.uninstall_auto_updates:
        return handle_uninstall_auto_updates(options)
    return None


def handle_main_actions(options: Any) -> int:
    """Handle the main application actions based on parsed options.

    Args:
        options: Parsed command-line arguments

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Handle config generation first if requested
    if options.generate_config:
        return handle_config_generation(options)

    # Try basic actions first
    result = _get_basic_action_result(options)
    if result is not None:
        return result

    # Try auto-update actions
    result = _get_auto_update_action_result(options)
    if result is not None:
        return result

    # Handle macOS service actions
    if options.install_service:
        return _handle_macos_service_action(options, "install_service")
    elif options.uninstall_service:
        return _handle_macos_service_action(options, "uninstall_service")
    elif options.service_status:
        return _handle_macos_service_action(options, "service_status")
    elif options.test_notification:
        return _handle_macos_service_action(options, "test_notification")
    elif options.menubar:
        return _handle_macos_service_action(options, "menubar_app")
    else:
        # No valid option selected
        print("No valid action specified. Use -h for help.")
        return 1


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

    # Emit deprecation warnings for legacy flags (once per process)
    if options.blacklist:
        warn_deprecated_flag(
            "--blacklist",
            replacement="--blocklist",
            removal_version="1.0.0",
        )
    if options.blacklist_auto_updates:
        warn_deprecated_flag(
            "--blacklist-auto-updates",
            replacement="--blocklist-auto-updates",
            removal_version="1.0.0",
        )

    # Enable profiling if requested
    if options.profile:
        enable_profiling()

    # Set up logging
    handle_setup_logging(options)

    # Check and inform about ML features if debug mode is enabled
    if options.debug:
        _check_ml_availability()

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
        if options.save_filter:
            handle_save_filter(options, filter_manager)

        # Print performance report if profiling was enabled
        if options.profile:
            print_report(detailed=options.detailed_profile)
            disable_profiling()

        return result
    except Exception as e:
        logging.exception("An error occurred: %s", str(e))
        print(create_progress_bar().color("red")(f"Error: {str(e)}"))

        # Print performance report even on error if profiling was enabled
        if options.profile:
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
