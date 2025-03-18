"""Main entry point for the VersionTracker application."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from versiontracker import __version__
from versiontracker.apps import (
    check_brew_install_candidates,
    filter_out_brews,
    get_applications,
    get_homebrew_casks,
)
from versiontracker.cli import get_arguments
from versiontracker.config import Config, config, set_global_config
from versiontracker.export import export_data
from versiontracker.utils import check_dependencies, get_json_data, setup_logging


def main() -> int:
    """Main entry point for the VersionTracker application.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    options = get_arguments()

    # Initialize configuration with custom path if provided
    if options.config_path:
        custom_config = Config(config_file=options.config_path)
        set_global_config(custom_config)

    # Setup logging based on debug flag
    setup_logging(debug=bool(options.debug))

    # Log program start
    logging.info(f"VersionTracker {__version__} starting")

    # Handle configuration file generation
    if options.generate_config:
        try:
            config_path = None
            if options.config_path:
                config_path = Path(options.config_path)
            
            path = config.generate_default_config(config_path)
            print(f"Configuration file generated: {path}")
            print("You can now edit this file to customize VersionTracker's behavior.")
            return 0
        except Exception as e:
            logging.error(f"Failed to generate configuration file: {e}")
            print(f"Error: Failed to generate configuration file: {e}")
            return 1

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
                    filtered_apps.append((app, ver))

                if not options.export_format:
                    if not config.is_blacklisted(app):
                        logging.debug("\tapp: %s, version: %s", app, ver)
                        print(f"{app} (version: {ver})")

            if not options.export_format:
                print(
                    f"\nFound {len(filtered_apps)} applications (excluding blacklisted apps)"
                )

            # Handle export if requested
            if options.export_format:
                export_result = handle_export(
                    {"applications": filtered_apps},
                    options.export_format,
                    options.output_file,
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
                    options.output_file,
                )
                if not options.output_file:
                    print(export_result)

        elif options.recom or options.strict_recom:
            # Get recommendations for installing with Homebrew
            strict_mode = bool(options.strict_recom)
            raw_data = get_json_data(config.get("system_profiler_cmd"))
            apps_folder = get_applications(raw_data)
            apps_homebrew = get_homebrew_casks()

            # Filter out blacklisted apps
            apps_folder = [
                (app, ver) for app, ver in apps_folder if not config.is_blacklisted(app)
            ]

            if not options.export_format:
                # Log detected applications
                for app, _ in apps_folder:
                    logging.debug("\tapp: %s", app)

                # Log installed Homebrew casks
                logging.debug("\n*** Installed homebrew casks ***")
                for brew in apps_homebrew:
                    logging.debug("\tbrew cask: %s", brew)

            # Get candidates for search
            search_candidates = filter_out_brews(apps_folder, apps_homebrew, strict_mode)

            if not options.export_format:
                logging.debug("\n*** Candidates for search (not found as brew casks) ***")
                for candidate in search_candidates:
                    logging.debug("\tcandidate: %s", candidate)

            # Check for available Homebrew casks
            brew_options = check_brew_install_candidates(
                search_candidates,
                rate_limit=config.get("api_rate_limit"),
                strict=strict_mode
            )

            if not options.export_format:
                # Print recommendations
                if brew_options:
                    print("Recommended Homebrew casks to install:")
                    for brew in brew_options:
                        print(f"  {brew}")
                    print(f"\nInstall with: brew install --cask {' '.join(brew_options)}")
                elif len(search_candidates) > 0:
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
                    "install_command": (
                        f"brew install --cask {' '.join(brew_options)}"
                        if brew_options
                        else ""
                    ),
                }

                export_result = handle_export(
                    export_data, options.export_format, options.output_file
                )
                if not options.output_file:
                    print(export_result)

        return 0

    except Exception as e:
        logging.exception("An error occurred: %s", str(e))
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
            logging.info(f"Data exported to {filename}")
            return f"Data exported to {filename}"
        else:
            return result
    except Exception as e:
        logging.error(f"Export error: {e}")
        raise RuntimeError(f"Failed to export data: {e}")


if __name__ == "__main__":
    sys.exit(main())
