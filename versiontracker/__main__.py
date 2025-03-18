"""Main entry point for the VersionTracker application."""

import logging
import sys
import gc
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
from versiontracker.version import VersionStatus, check_outdated_apps


def handle_config_generation(options: Any) -> int:
    """Handle configuration file generation.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
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
        return 1


def handle_list_apps(options: Any) -> int:
    """Handle listing applications.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        raw_data = get_json_data(config.get("system_profiler_cmd"))
        apps_folder = get_applications(raw_data)

        # Apply blacklist filtering
        filtered_apps: List[Tuple[str, str]] = []
        for item in apps_folder:
            app, ver = item
            if not config.is_blacklisted(app):
                filtered_apps.append((app, ver))

            if not options.export_format:
                if not config.is_blacklisted(app):
                    logging.debug("\tapp: %s, version: %s", app, ver)
                    print(f"{app} (version: {ver})")

        if not options.export_format:
            print(f"\nFound {len(filtered_apps)} applications (excluding blacklisted apps)")

        # Handle export if requested
        if options.export_format:
            export_result = handle_export(
                {"applications": filtered_apps},
                options.export_format,
                options.output_file,
            )
            if not options.output_file:
                print(export_result)
        return 0
    except Exception as e:
        logging.error(f"Error listing apps: {e}")
        return 1


def handle_list_brews(options: Any) -> int:
    """Handle listing Homebrew casks.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
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
        return 0
    except Exception as e:
        logging.error(f"Error listing brews: {e}")
        return 1


def handle_brew_recommendations(options: Any) -> int:
    """Handle Homebrew installation recommendations.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Get recommendations for installing with Homebrew
        strict_mode = bool(options.strict_recom)
        raw_data = get_json_data(config.get("system_profiler_cmd"))
        apps_folder = get_applications(raw_data)
        apps_homebrew = get_homebrew_casks()

        # Apply blacklist filtering
        filtered_apps: List[Tuple[str, str]] = [
            (item[0], item[1]) for item in apps_folder if not config.is_blacklisted(item[0])
        ]

        # Debug output if requested
        if options.debug:
            logging.debug("\n*** Applications not managed by App Store ***")
            for app, ver in filtered_apps:
                logging.debug("\tapp: %s", app)

            logging.debug("\n*** Installed homebrew casks ***")
            for brew in apps_homebrew:
                logging.debug("\tbrew cask: %s", brew)

        # Get installable candidates
        search_list = filter_out_brews(filtered_apps, apps_homebrew, strict_mode)

        if options.debug:
            logging.debug("\n*** Candidates for search (not found as brew casks) ***")
            for candidate in search_list:
                logging.debug("\tcandidate: %s", candidate)

        # Rate limit if specified
        rate_limit = options.rate_limit if options.rate_limit else config.get("rate_limit")

        # Get Homebrew installation recommendations
        installables = check_brew_install_candidates(search_list, rate_limit, strict_mode)

        # Display results
        if not options.export_format:
            for installable in installables:
                print(f"{installable} (installable with Homebrew)")

            print(f"\nFound {len(installables)} applications installable with Homebrew")

        # Handle export if requested
        if options.export_format:
            export_data_dict = {
                "installable_with_homebrew": installables,
                "total_installable": len(installables),
            }
            export_result = handle_export(
                export_data_dict,
                options.export_format,
                options.output_file,
            )
            if not options.output_file:
                print(export_result)
        return 0
    except Exception as e:
        logging.error(f"Error checking brew recommendations: {e}")
        return 1


def handle_outdated_check(options: Any) -> int:
    """Handle checking for outdated applications.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Check for required dependencies
        if not check_dependencies():
            return 1

        # Get system profiler data with application information
        profiler_data = get_json_data(config.get("system_profiler_cmd"))

        # Get all installed applications
        all_apps = get_applications(profiler_data)
        
        # Use a smaller memory footprint for the check
        gc.collect()
        
        # Get list of installed brews
        brews = get_homebrew_casks()

        # Memory cleanup again
        gc.collect()

        # Check outdated apps using memory-optimized batching
        outdated_batch_size = 20  # Process in smaller batches to reduce memory usage
        outdated_info = check_outdated_apps(all_apps, batch_size=outdated_batch_size)

        # Sort by status (outdated first, then up to date, then newer, then unknown)
        status_priority = {
            VersionStatus.OUTDATED: 0,
            VersionStatus.UP_TO_DATE: 1,
            VersionStatus.NEWER: 2,
            VersionStatus.UNKNOWN: 3,
        }

        outdated_info.sort(key=lambda x: (status_priority[x[2]], x[0].casefold()))

        # Prepare table output
        table = []
        total_outdated = 0

        for app_name, version_info, status in outdated_info:
            icon = get_status_icon(status)
            color = get_status_color(status)
            
            # Count outdated applications
            if status == VersionStatus.OUTDATED:
                total_outdated += 1

            # Format the versions
            current_ver = version_info["current"] if version_info["current"] else "Unknown"
            latest_ver = version_info["latest"] if version_info["latest"] else "Unknown"

            # Add row to table with colored output
            table.append(
                [
                    icon,
                    color(app_name),
                    color(current_ver),
                    color(latest_ver),
                ]
            )

        # Print the results
        if table:
            # Print summary header with count of outdated apps
            outdated_text = f"({total_outdated} outdated)" if total_outdated > 0 else ""
            print(f"\nFound {len(table)} applications {outdated_text}:\n")

            headers = ["", "Application", "Current Version", "Latest Version"]
            print(tabulate(table, headers=headers, tablefmt="simple"))
            
            # Memory cleanup after generating report
            del table
            gc.collect()

            # Print summary of outdated applications
            if total_outdated > 0:
                print(f"\n{colored('!', 'red')} {total_outdated} applications can be updated.")
                if options.export:
                    print(
                        colored(
                            "Outdated applications are marked with '!' in the exported file.",
                            "yellow",
                        )
                    )
            else:
                print(colored("\nAll applications are up to date!", "green"))
        else:
            print("No applications found.")

        # Export if requested
        if options.export:
            return export_data(outdated_info, options.export)

        return 0
    except Exception as e:
        logging.error(f"Error checking outdated applications: {e}")
        traceback.print_exc()
        return 1


def handle_export(data: Dict[str, Any], format_type: str, filename: Optional[str] = None) -> str:
    """Handle exporting data in the specified format.

    Args:
        data: The data to export
        format_type: The format to export to ('json' or 'csv')
        filename: Optional filename to write to

    Returns:
        str: Export result or empty string on error
    """
    try:
        logging.info(f"Exporting data in {format_type} format")

        result = export_data(data, format_type=format_type, filename=filename)

        if filename:
            logging.info(f"Data exported to {filename}")

        # Convert the result to string if it's not already
        if not isinstance(result, str):
            result = str(result)

        return result
    except Exception as e:
        logging.error(f"Export error: {e}")
        print(f"Error during export: {e}")
        return ""


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
        return handle_config_generation(options)

    # Check dependencies
    if not check_dependencies():
        logging.error("Missing required dependencies")
        return 1

    try:
        # Process the requested action
        if options.apps:
            return handle_list_apps(options)
        elif options.brews:
            return handle_list_brews(options)
        elif options.recom or options.strict_recom:
            return handle_brew_recommendations(options)
        elif options.check_outdated:
            return handle_outdated_check(options)
        else:
            # No valid option selected
            print("No valid action specified. Use -h for help.")
            return 1

    except Exception as e:
        logging.exception("An error occurred: %s", str(e))
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
