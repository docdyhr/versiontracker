"""Main entry point for the VersionTracker application."""

import logging
import sys
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
        # Get applications not updated by App Store
        raw_data = get_json_data(config.get("system_profiler_cmd"))
        apps_folder = get_applications(raw_data)

        # Apply blacklist filtering
        filtered_apps: List[Tuple[str, str]] = [
            (item[0], item[1]) for item in apps_folder if not config.is_blacklisted(item[0])
        ]

        # Check for outdated applications
        print("Checking for outdated applications...")
        version_info_list = check_outdated_apps(filtered_apps)

        # Count by status
        status_counts = {
            VersionStatus.OUTDATED: 0,
            VersionStatus.UP_TO_DATE: 0,
            VersionStatus.NEWER: 0,
            VersionStatus.UNKNOWN: 0,
        }

        # Display results
        if not options.export_format:
            # Print outdated apps first
            print("\nOutdated Applications:")
            print("---------------------")
            outdated_found = False

            for info in version_info_list:
                status_counts[info.status] += 1

                if info.status == VersionStatus.OUTDATED:
                    outdated_found = True
                    latest = f" → {info.latest_version}" if info.latest_version else ""
                    print(
                        f"{info.name} (version: {info.version_string}{latest}) - "
                        f"UPDATE AVAILABLE"
                    )

            if not outdated_found:
                print("No outdated applications found.")

            # Print summary
            print("\nApplication Version Summary:")
            print("--------------------------")
            print(f"Outdated: {status_counts[VersionStatus.OUTDATED]}")
            print(f"Up to date: {status_counts[VersionStatus.UP_TO_DATE]}")
            print(f"Newer than Homebrew: {status_counts[VersionStatus.NEWER]}")
            print(f"Unknown status: {status_counts[VersionStatus.UNKNOWN]}")
            print(f"Total applications checked: {len(version_info_list)}")

        # Handle export if requested
        if options.export_format:
            # Convert to serializable format
            export_data_dict = {
                "applications": [
                    {
                        "name": info.name,
                        "current_version": info.version_string,
                        "latest_version": info.latest_version or "unknown",
                        "status": info.status.value,
                    }
                    for info in version_info_list
                ],
                "summary": {
                    "outdated": status_counts[VersionStatus.OUTDATED],
                    "up_to_date": status_counts[VersionStatus.UP_TO_DATE],
                    "newer": status_counts[VersionStatus.NEWER],
                    "unknown": status_counts[VersionStatus.UNKNOWN],
                    "total": len(version_info_list),
                },
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
        logging.error(f"Error checking outdated apps: {e}")
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
