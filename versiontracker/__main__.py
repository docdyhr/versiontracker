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
from versiontracker.export import export_data
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
                    if not options.export_format:
                        print(f"{app} - ({ver})")
                else:
                    logging.debug(f"Skipping blacklisted app: {app}")

            if not options.export_format:
                print(
                    f"\nFound {len(filtered_apps)} applications (excluding blacklisted apps)"
                )
            
            # Handle export if requested
            if options.export_format:
                export_result = handle_export(
                    {"applications": filtered_apps}, 
                    options.export_format, 
                    options.output_file
                )
                if not options.output_file:
                    print(export_result)

        elif options.brews:
            # Get installed Homebrew casks
            apps_homebrew = get_homebrew_casks()
            
            if not options.export_format:
                for brew in apps_homebrew:
                    logging.debug("\tbrew cask: %s", brew)
                    print(brew)

                print(f"\nFound {len(apps_homebrew)} installed Homebrew casks")
            
            # Handle export if requested
            if options.export_format:
                export_result = handle_export(
                    {"homebrew_casks": apps_homebrew}, 
                    options.export_format, 
                    options.output_file
                )
                if not options.output_file:
                    print(export_result)

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

            # Display results if not exporting
            if brew_options and not options.export_format:
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
            elif not brew_options and not options.export_format:
                if strict_mode:
                    print(
                        "No new applications found that can be installed with Homebrew."
                    )
                else:
                    print("No recommendations found for Homebrew installations.")
            
            # Handle export if requested
            if options.export_format:
                # Create a more detailed export with more information
                export_data = {
                    "recommendations": brew_options,
                    "applications": apps_folder,
                    "homebrew_casks": apps_homebrew,
                    "search_candidates": search_candidates,
                    "strict_mode": strict_mode,
                    "install_command": f"brew install --cask {' '.join(brew_options)}" if brew_options else ""
                }
                
                export_result = handle_export(
                    export_data, 
                    options.export_format, 
                    options.output_file
                )
                if not options.output_file:
                    print(export_result)

        return 0

    except Exception as e:
        logging.exception("An error occurred")
        print(f"Error: {str(e)}")
        return 1


def handle_export(data: Dict[str, Any], format_type: str, filename: str = None) -> str:
    """Handle data export in the specified format.
    
    Args:
        data: The data to export
        format_type: The format to export to (json or csv)
        filename: Optional filename to write to
        
    Returns:
        str: The exported data as a string or the path to the exported file
    """
    try:
        logging.info(f"Exporting data in {format_type} format")
        result = export_data(data, format_type, filename)
        if filename:
            print(f"Data exported to {result}")
        return result
    except Exception as e:
        logging.exception(f"Error exporting data to {format_type}")
        print(f"Error exporting data: {str(e)}")
        return ""


if __name__ == "__main__":
    sys.exit(main())
