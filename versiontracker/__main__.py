"""Main entry point for the VersionTracker application."""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

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
from versiontracker.profiling import (
    disable_profiling,
    enable_profiling,
    print_report,
    profile_function,
)
from versiontracker.ui import QueryFilterManager, create_progress_bar

# Logging functions have been moved to versiontracker.handlers.setup_handlers


def setup_logging(*args, **kwargs):
    """Stub for setup_logging to satisfy test patching in test_integration.py."""
    pass


def determine_command(options: Any) -> Optional[str]:
    """Determine which command to execute based on the options.

    Args:
        options: Command line options

    Returns:
        str: The command to execute, or None if no command is specified
    """
    if hasattr(options, "apps") and options.apps:
        return "list"
    elif hasattr(options, "brews") and options.brews:
        return "brewfilter"
    elif hasattr(options, "recom") and options.recom:
        return "homebrew"
    elif hasattr(options, "strict_recom") and options.strict_recom:
        return "homebrew"
    elif hasattr(options, "check_outdated") and options.check_outdated:
        return "outdated"
    elif hasattr(options, "version") and options.version:
        return "version"
    else:
        return None


# Configuration functions have been moved to versiontracker.handlers.setup_handlers
# Configuration functions have been moved to versiontracker.handlers.setup_handlers


# Filter management functions have been moved to versiontracker.handlers.filter_handlers


@profile_function("versiontracker_main")
def versiontracker_main() -> int:
    """Main entry point for VersionTracker.

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
    """Main entry point function for console script.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    return versiontracker_main()


# Entry point for running as a script
if __name__ == "__main__":
    sys.exit(versiontracker_main())
