"""Main entry point for the VersionTracker application."""

import logging
import sys
import gc
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, Iterable
from concurrent.futures import as_completed
from pathlib import Path
import json

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
from versiontracker.config import Config, check_dependencies, config
from versiontracker.export import export_data
from versiontracker.utils import get_json_data
from versiontracker.version import VersionStatus, check_outdated_apps
from versiontracker.exceptions import (
    VersionTrackerError,
    NetworkError,
    TimeoutError,
    PermissionError,
    ConfigError,
    HomebrewError,
    ExportError
)

def get_status_icon(status: VersionStatus) -> str:
    """Get a status icon for a version status.

    Args:
        status: The version status

    Returns:
        str: An icon representing the status
    """
    try:
        if status == VersionStatus.UPTODATE:
            return colored("✅", "green")
        elif status == VersionStatus.OUTDATED:
            return colored("🔄", "yellow")
        elif status == VersionStatus.NOT_FOUND:
            return colored("❓", "blue")
        elif status == VersionStatus.ERROR:
            return colored("❌", "red")
        return ""
    except Exception:
        # Fall back to text-based icons if colored package is not available
        if status == VersionStatus.UPTODATE:
            return "[OK]"
        elif status == VersionStatus.OUTDATED:
            return "[OUTDATED]"
        elif status == VersionStatus.NOT_FOUND:
            return "[NOT FOUND]"
        elif status == VersionStatus.ERROR:
            return "[ERROR]"
        return ""


def get_status_color(status: VersionStatus) -> Any:
    """Get a color function for the given version status.
    
    Args:
        status: Version status
        
    Returns:
        function: Color function that takes a string and returns a colored string
    """
    if status == VersionStatus.UPTODATE:
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
        try:
            apps_data = get_json_data(getattr(config, "system_profiler_cmd", "system_profiler -json SPApplicationsDataType"))
            apps = get_applications(apps_data)
        except PermissionError:
            print(colored("Error: Permission denied when reading application data.", "red"))
            print(colored("Try running the command with sudo or check your file permissions.", "yellow"))
            return 1
        except TimeoutError:
            print(colored("Error: Timed out while reading application data.", "red"))
            print(colored("Check your system load and try again later.", "yellow"))
            return 1
        except Exception as e:
            print(colored(f"Error: Failed to get installed applications: {e}", "red"))
            return 1

        # Get installed Homebrew casks
        print(colored("Getting installable casks from Homebrew...", "blue"))
        try:
            brews = get_homebrew_casks()
        except FileNotFoundError:
            print(colored("Error: Homebrew executable not found.", "red"))
            print(colored("Please make sure Homebrew is installed and properly configured.", "yellow"))
            return 1
        except PermissionError:
            print(colored("Error: Permission denied when accessing Homebrew.", "red"))
            print(colored("Check your user permissions and Homebrew installation.", "yellow"))
            return 1
        except Exception as e:
            print(colored(f"Error: Failed to get Homebrew casks: {e}", "red"))
            return 1

        # Filter out applications already managed by Homebrew
        include_brews = getattr(options, "include_brews", False)
        if not include_brews:
            try:
                apps = filter_out_brews(apps, brews)
            except Exception as e:
                print(colored(f"Warning: Error filtering applications: {e}", "yellow"))
                print(colored("Proceeding with all applications.", "yellow"))

        # Print status update
        print(colored(f"Checking {len(apps)} applications for updates...", "blue"))

        # Start time for tracking
        start_time = time.time()

        # Check outdated status
        try:
            batch_size = getattr(config, "batch_size", 50)
            outdated_info = check_outdated_apps(apps, batch_size=batch_size)
        except TimeoutError:
            print(colored("Error: Network timeout while checking for updates.", "red"))
            print(colored("Check your internet connection and try again.", "yellow"))
            return 1
        except NetworkError:
            print(colored("Error: Network error while checking for updates.", "red"))
            print(colored("Check your internet connection and try again.", "yellow"))
            return 1
        except Exception as e:
            print(colored(f"Error: Failed to check for updates: {e}", "red"))
            return 1

        # End time and calculation
        elapsed_time = time.time() - start_time
        
        # Prepare results table
        table = []
        total_outdated = 0
        total_up_to_date = 0
        total_unknown = 0
        total_not_found = 0
        total_error = 0

        for app_name, version_info, status in outdated_info:
            icon = get_status_icon(status)
            color = get_status_color(status)
            
            if status == VersionStatus.OUTDATED:
                total_outdated += 1
            elif status == VersionStatus.UPTODATE:
                total_up_to_date += 1
            elif status == VersionStatus.NOT_FOUND:
                total_not_found += 1
            elif status == VersionStatus.ERROR:
                total_error += 1
            else:
                total_unknown += 1
                
            # Add row to table with colored status
            installed_version = version_info["installed"] if "installed" in version_info else "Unknown"
            latest_version = version_info["latest"] if "latest" in version_info else "Unknown"
            
            table.append([
                icon,
                app_name,
                color(installed_version),
                color(latest_version),
            ])
        
        # Sort table by application name
        table.sort(key=lambda x: x[1].lower())
        
        # Print results
        if table:
            # Print summary information about processing
            print("")
            print(colored(f"✓ Processed {len(apps)} applications in {elapsed_time:.1f} seconds", "blue"))
            
            # Print status summary with counts and colors
            print(colored(f"\nStatus Summary:", "blue"))
            print(f" {colored('✓', 'green')} Up to date: {colored(str(total_up_to_date), 'green')}")
            print(f" {colored('!', 'red')} Outdated: {colored(str(total_outdated), 'red')}")
            print(f" {colored('?', 'yellow')} Unknown: {colored(str(total_unknown), 'yellow')}")
            print(f" {colored('❓', 'blue')} Not Found: {colored(str(total_not_found), 'blue')}")
            print(f" {colored('❌', 'red')} Error: {colored(str(total_error), 'red')}")
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
            try:
                return handle_export(outdated_info, options.export, options.output_file if hasattr(options, "output_file") else None)
            except ExportError as e:
                print(colored(f"Error exporting data: {e}", "red"))
                return 1

        return 0
    except ConfigError as e:
        print(colored(f"Configuration Error: {e}", "red"))
        print(colored("Please check your configuration file and try again.", "yellow"))
        return 1
    except KeyboardInterrupt:
        print(colored("\nOperation canceled by user.", "yellow"))
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logging.error(f"Error checking outdated applications: {e}")
        print(colored(f"Error: {e}", "red"))
        if config.debug:
            traceback.print_exc()
        else:
            print(colored("Run with --debug for more information.", "yellow"))
        return 1


def handle_export(data: Union[Dict[str, Any], List[Tuple[str, Dict[str, str], VersionStatus]]], 
                 format_type: str, 
                 filename: Optional[str] = None) -> int:
    """Handle exporting data in the specified format.

    Args:
        data: The data to export
        format_type: The format to export to ('json' or 'csv')
        filename: Optional filename to write to

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Export data
        result = export_data(data, format_type, filename)
        
        # If we're exporting to stdout, print the result
        if result and not filename:
            print(result)
            
        return 0
    except ValueError as e:
        print(colored(f"Export Error: {e}", "red"))
        print(colored("Supported formats are 'json' and 'csv'", "yellow"))
        return 1
    except PermissionError as e:
        print(colored(f"Permission Error: {e}", "red"))
        print(colored("Check your write permissions for the output file", "yellow"))
        return 1
    except ExportError as e:
        print(colored(f"Export Error: {e}", "red"))
        return 1
    except Exception as e:
        logging.error(f"Error exporting data: {e}")
        print(colored(f"Error: Failed to export data: {e}", "red"))
        if config.debug:
            traceback.print_exc()
        return 1


def setup_logging(debug: bool = False) -> None:
    """Set up logging configuration.
    
    Args:
        debug: Whether to enable debug logging
    """
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Ensure log directory exists
    log_dir = config.log_dir
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "versiontracker.log")
        ]
    )
    
    # Set log level for specific loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logging.debug("Logging initialized")


def main() -> int:
    """Main entry point for the VersionTracker application.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    options = get_arguments()

    # Initialize configuration with custom path if provided
    if options.config_path:
        # If a config path is provided and we're generating a config file, do that and exit
        if options.generate_config:
            path = Path(options.config_path)
            try:
                config_path = config.generate_default_config(path)
                print(f"Generated default configuration at: {config_path}")
                return 0
            except Exception as e:
                print(f"Error generating config file: {e}")
                return 1
        else:
            # Otherwise, use the provided config file path
            config_path = options.config_path
            try:
                new_config = Config(config_path)
                set_global_config(new_config)
            except Exception as e:
                print(f"Error loading config file: {e}")
                if getattr(options, "debug", False):
                    traceback.print_exc()
                return 1

    # Generate default config if requested
    elif options.generate_config:
        try:
            config_path = config.generate_default_config()
            print(f"Generated default configuration at: {config_path}")
            return 0
        except Exception as e:
            print(f"Error generating config file: {e}")
            return 1

    # Set debug mode in config
    config.debug = bool(getattr(options, "debug", False))
    
    # Set up logging
    setup_logging(debug=config.debug)
    
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
