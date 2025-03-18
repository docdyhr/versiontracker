"""Main entry point for the VersionTracker application."""

import logging
import sys
import gc
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, Iterable
from concurrent.futures import as_completed

try:
    from termcolor import colored
except ImportError:
    # Fallback if termcolor is not available
    def colored(text: str, color: Optional[str] = None, on_color: Optional[str] = None, attrs: Optional[Iterable[str]] = None) -> str:
        return text

try:
    from tabulate import tabulate
except ImportError:
    # Simple fallback if tabulate is not available
    def tabulate(tabular_data: Union[Dict[str, List[Any]], List[List[Any]]], 
                 headers: Union[str, Dict[str, str], List[str]] = 'keys', 
                 tablefmt: Optional[str] = None) -> str:
        result = []
        if headers == 'keys' and isinstance(tabular_data, dict):
            headers = list(tabular_data.keys())
        if isinstance(tabular_data, dict):
            tabular_data = [list(tabular_data[key]) for key in headers]
        if headers and headers != 'keys':
            result.append('\t'.join([str(h) for h in headers]))
        for row in tabular_data:
            result.append('\t'.join([str(cell) for cell in row]))
        return '\n'.join(result)

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
from versiontracker.utils import check_dependencies, setup_logging, get_json_data
from versiontracker.version import VersionStatus, check_outdated_apps

def get_status_icon(status: VersionStatus) -> str:
    """Get a status icon for the given version status.
    
    Args:
        status: Version status
        
    Returns:
        str: Status icon
    """
    if status == VersionStatus.UP_TO_DATE:
        return "✓"
    elif status == VersionStatus.OUTDATED:
        return "!"
    elif status == VersionStatus.NEWER:
        return "+"
    else:
        return "?"

def get_status_color(status: VersionStatus) -> Any:
    """Get a color function for the given version status.
    
    Args:
        status: Version status
        
    Returns:
        function: Color function that takes a string and returns a colored string
    """
    if status == VersionStatus.UP_TO_DATE:
        return lambda text: colored(text, "green")
    elif status == VersionStatus.OUTDATED:
        return lambda text: colored(text, "red")
    elif status == VersionStatus.NEWER:
        return lambda text: colored(text, "cyan")
    else:
        return lambda text: colored(text, "yellow")


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
        print(colored("Getting application data...", "blue"))
        # Get data from system_profiler
        apps_data = get_json_data(
            getattr(config, "system_profiler_cmd", "system_profiler -json SPApplicationsDataType")
        )
        
        # Get applications
        apps = get_applications(apps_data)
        
        # Get additional paths if specified
        additional_paths = []
        if getattr(options, "additional_dirs", None):
            additional_paths = options.additional_dirs.split(",")
        
        # Apply filtering
        if getattr(options, "blacklist", None):
            # Create a temporary config with the specified blacklist
            temp_config = Config()
            temp_config.set("blacklist", options.blacklist.split(","))
            filtered_apps = [(app, ver) for app, ver in apps if not temp_config.is_blacklisted(app)]
        else:
            # Use global config for blacklisting
            filtered_apps = [(app, ver) for app, ver in apps if not config.is_blacklisted(app)]
        
        # Get Homebrew casks if needed for filtering
        if hasattr(options, "brew_filter") and options.brew_filter:
            print(colored("Getting Homebrew casks for filtering...", "blue"))
            brews = get_homebrew_casks()
            include_brews = getattr(options, "include_brews", False)
            if not include_brews:
                filtered_apps = filter_out_brews(filtered_apps, brews)
            else:
                print(colored("Showing all applications (including those managed by Homebrew)", "yellow"))
                
        # Prepare table data
        table = []
        for app, version in sorted(filtered_apps, key=lambda x: x[0].lower()):
            table.append([colored(app, "green"), colored(version, "blue")])
            
        # Display results
        if table:
            print(colored(f"\nFound {len(table)} applications:\n", "blue"))
            print(tabulate(table, headers=["Application", "Version"], tablefmt="pretty"))
        else:
            print(colored("\nNo applications found matching the criteria.", "yellow"))
            
        # Export if requested
        if hasattr(options, "export") and options.export:
            return handle_export(
                [{"name": app, "version": ver} for app, ver in filtered_apps],
                options.export
            )
            
        return 0
    except Exception as e:
        logging.error(f"Error listing applications: {e}")
        traceback.print_exc()
        return 1


def handle_list_brews(options: Any) -> int:
    """Handle listing Homebrew casks.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        print(colored("Getting installed Homebrew casks...", "blue"))
        brews = get_homebrew_casks()
        
        # Prepare table data
        table = []
        for i, brew in enumerate(sorted(brews), 1):
            table.append([i, colored(brew, "cyan")])
            
        # Print the results
        if table:
            print(colored(f"\nFound {len(table)} installed Homebrew casks:\n", "blue"))
            print(tabulate(table, headers=["#", "Cask Name"], tablefmt="pretty"))
        else:
            print(colored("\nNo Homebrew casks found. You may need to install Homebrew.", "yellow"))
            
        # Export if requested
        if hasattr(options, "export") and options.export:
            # Format for export
            export_data = {"homebrew_casks": brews, "total_casks": len(brews)}
            return handle_export(export_data, options.export)
            
        return 0
    except Exception as e:
        logging.error(f"Error listing Homebrew casks: {e}")
        traceback.print_exc()
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
        print(colored("Getting application data...", "blue"))
        raw_data = get_json_data(getattr(config, "system_profiler_cmd", "system_profiler -json SPApplicationsDataType"))
        apps_folder = get_applications(raw_data)
        
        print(colored("Getting Homebrew casks...", "blue"))
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

        # Rate limit if specified - always convert to integer for consistency
        # If options.rate_limit is specified, use that, otherwise get from config or default to 10
        rate_limit_int = 10  # Default value
        if options.rate_limit is not None:
            rate_limit_int = int(options.rate_limit)
        elif hasattr(config, "rate_limit"):
            try:
                # Try to get as integer or from config.get
                if isinstance(config.rate_limit, int):
                    rate_limit_int = config.rate_limit
                elif hasattr(config, "get"):
                    rate_limit_int = int(config.get("rate_limit", 10))
            except (ValueError, TypeError, AttributeError):
                # If any conversion fails, use default
                rate_limit_int = 10
        
        # Start time for tracking
        start_time = time.time()
                
        # Get Homebrew installation recommendations - always use integer
        print(colored(f"\nSearching for {len(search_list)} applications in Homebrew repository...", "blue"))
        print(colored(f"Using rate limit of {rate_limit_int} seconds between API calls", "blue"))
        print(colored("This process may take some time, please be patient...", "blue"))
        
        installables = check_brew_install_candidates(search_list, rate_limit_int, strict_mode)
        
        # End time and calculation
        elapsed_time = time.time() - start_time
        
        # Display results
        if not options.export_format:
            # Print summary information about processing
            print("")
            print(colored(f"✓ Processed {len(search_list)} applications in {elapsed_time:.1f} seconds", "blue"))
            print(colored(f"Found {len(installables)} applications installable with Homebrew", "green"))
            print("")
            
            # If we found installable applications, list them in a nice format
            if installables:
                for i, installable in enumerate(installables, 1):
                    print(f"{i:2d}. {colored(installable, 'green')} (installable with Homebrew)")
            else:
                print(colored("No applications found that can be installed with Homebrew.", "yellow"))

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
        logging.error(f"Error in brew recommendations: {e}")
        traceback.print_exc()
        return 1


def handle_outdated_check(options: Any) -> int:
    """Handle checking for outdated applications.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Validate required dependencies
        check_dependencies()

        # Update config with no_progress option if specified
        if hasattr(options, "no_progress") and options.no_progress:
            config.no_progress = True
            config.show_progress = False

        # Get installed applications
        print(colored("Getting Apps from Applications/...", "blue"))
        apps_data = get_json_data(getattr(config, "system_profiler_cmd", "system_profiler -json SPApplicationsDataType"))
        apps = get_applications(apps_data)

        # Get installed Homebrew casks
        print(colored("Getting installable casks from Homebrew...", "blue"))
        brews = get_homebrew_casks()

        # Filter out applications already managed by Homebrew
        include_brews = getattr(options, "include_brews", False)
        if not include_brews:
            apps = filter_out_brews(apps, brews)

        # Print status update
        print(colored(f"Checking {len(apps)} applications for updates...", "blue"))

        # Start time for tracking
        start_time = time.time()

        # Check outdated status
        batch_size = getattr(config, "batch_size", 50)
        outdated_info = check_outdated_apps(apps, batch_size=batch_size)

        # End time and calculation
        elapsed_time = time.time() - start_time
        
        # Prepare results table
        table = []
        total_outdated = 0
        total_up_to_date = 0
        total_unknown = 0

        for app_name, version_info, status in outdated_info:
            icon = get_status_icon(status)
            color = get_status_color(status)
            
            # Count by status
            if status == VersionStatus.OUTDATED:
                total_outdated += 1
            elif status == VersionStatus.UP_TO_DATE:
                total_up_to_date += 1
            elif status == VersionStatus.UNKNOWN:
                total_unknown += 1

            # Format the versions
            current_ver = version_info.get("installed", "") if version_info.get("installed") else "Unknown"
            latest_ver = version_info.get("latest", "") if version_info.get("latest") else "Unknown"

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
            # Print summary information about processing
            print("")
            print(colored(f"✓ Processed {len(apps)} applications in {elapsed_time:.1f} seconds", "blue"))
            
            # Print status summary with counts and colors
            print(colored(f"\nStatus Summary:", "blue"))
            print(f" {colored('✓', 'green')} Up to date: {colored(str(total_up_to_date), 'green')}")
            print(f" {colored('!', 'red')} Outdated: {colored(str(total_outdated), 'red')}")
            print(f" {colored('?', 'yellow')} Unknown: {colored(str(total_unknown), 'yellow')}")
            print("")
            
            # Print the table with headers
            headers = ["", "Application", "Installed Version", "Latest Version"]
            print(
                tabulate(
                    table,
                    headers=headers,
                    tablefmt="pretty"
                )
            )
            
            if total_outdated > 0:
                print(colored(f"\nFound {total_outdated} outdated applications.", "red"))
            else:
                print(colored("\nAll applications are up to date!", "green"))
        else:
            print(colored("No applications found.", "yellow"))

        # Export if requested
        if hasattr(options, "export") and options.export:
            return handle_export(outdated_info, options.export)

        return 0
    except Exception as e:
        logging.error(f"Error checking outdated applications: {e}")
        traceback.print_exc()
        return 1


def handle_export(data: Union[Dict[str, Any], List[Tuple[str, Dict[str, str], VersionStatus]]], format_type: str, filename: Optional[str] = None) -> int:
    """Handle exporting data in the specified format.

    Args:
        data: The data to export
        format_type: The format to export to ('json' or 'csv')
        filename: Optional filename to write to

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        if not data:
            print("No data to export")
            return 1

        result = export_data(data, format_type, filename)
        if result:
            print(f"Data exported to {result}")
            return 0
        else:
            print("Failed to export data")
            return 1
    except Exception as e:
        logging.error(f"Error exporting data: {e}")
        return 1


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
