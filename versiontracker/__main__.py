"""Main entry point for the VersionTracker application."""

import logging
import sys
from typing import Any, Dict, List

from versiontracker import __version__
from versiontracker.apps import (
    check_brew_install_candidates,
    filter_out_brews,
    get_applications,
    get_homebrew_casks,
)
from versiontracker.cli import get_arguments
from versiontracker.config import config
from versiontracker.utils import check_dependencies, get_json_data, setup_logging


def main() -> int:
    """Main entry point for the VersionTracker application.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    options = get_arguments()

    # Setup logging based on debug flag
    setup_logging(debug=bool(options.debug))

    # Log program start
    logging.info(f"VersionTracker {__version__} starting")

    # Check dependencies
    if not check_dependencies():
        logging.error("Missing required dependencies")
        print("Error: Missing required dependencies. See log for details.")
        return 1

    try:
        # Handle commands
        if options.apps:
            # Get and display applications
            raw_data = get_json_data(config.get("system_profiler_cmd"))
            apps_folder = get_applications(raw_data)

            # Filter out blacklisted apps
            filtered_apps = []
            for item in apps_folder:
                app, ver = item
                if not config.is_blacklisted(app):
                    filtered_apps.append(item)
                    print(f"{app} - ({ver})")
                else:
                    logging.debug(f"Skipping blacklisted app: {app}")

            print(
                f"\nFound {len(filtered_apps)} applications (excluding blacklisted apps)"
            )

        elif options.brews:
            # Get installed Homebrew casks
            apps_homebrew = get_homebrew_casks()
            for brew in apps_homebrew:
                logging.debug("\tbrew cask: %s", brew)
                print(brew)

            print(f"\nFound {len(apps_homebrew)} installed Homebrew casks")

        elif options.recom or options.strict_recom:
            # Get application data
            raw_data = get_json_data(config.get("system_profiler_cmd"))
            apps_folder = get_applications(raw_data)

            # Filter out blacklisted apps
            apps_folder = [
                app for app in apps_folder if not config.is_blacklisted(app[0])
            ]

            # Get installed Homebrew casks
            apps_homebrew = get_homebrew_casks()

            # Filter out apps already manageable by Homebrew
            search_candidates = filter_out_brews(apps_folder, apps_homebrew)

            # Determine if strict mode is enabled
            strict_mode = options.strict_recom

            # Check which apps can be installed with Homebrew
            brew_options = check_brew_install_candidates(
                search_candidates,
                rate_limit=config.get("api_rate_limit"),
                strict=strict_mode,
            )

            # Display results
            if brew_options:
                if strict_mode:
                    print(
                        "\nRecommended NEW apps to install with Homebrew (not already in Homebrew):"
                    )
                else:
                    print("\nRecommended apps to install with Homebrew:")

                for brew in brew_options:
                    logging.debug("\trecommended install: %s", brew)
                    print(f"- {brew}")

                # Print homebrew install command
                if len(brew_options) > 0:
                    print("\nInstall command:")
                    brew_cmd = f"brew install --cask {' '.join(brew_options)}"
                    print(f"{brew_cmd}")
            else:
                if strict_mode:
                    print(
                        "No new applications found that can be installed with Homebrew."
                    )
                else:
                    print("No recommendations found for Homebrew installations.")

        logging.info("VersionTracker completed successfully")
        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        logging.info("Operation cancelled by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logging.exception(f"Error in VersionTracker: {e}")
        print(f"Error: {e}. See log for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
