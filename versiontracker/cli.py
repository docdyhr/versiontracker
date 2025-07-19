"""Command Line Interface for VersionTracker."""

import argparse
import sys
import textwrap
from datetime import datetime

from versiontracker import __version__


def get_arguments():
    """Return a dict of command line arguments (cli).

    Returns:
        argparse.Namespace: The parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Copyright year automatically updates to current year
        epilog=textwrap.dedent(
            f"""\
         thomas@dyhr.com {datetime.now().year}
         """
        ),
    )

    # Debug mode
    parser.add_argument("-D", "--debug", dest="debug", action="store_true", help="turn on DEBUG mode")

    # Performance options
    performance_group = parser.add_argument_group("Performance options")
    performance_group.add_argument(
        "--rate-limit",
        dest="rate_limit",
        type=int,
        help="API rate limit in seconds (default: 3)",
    )
    performance_group.add_argument(
        "--max-workers",
        dest="max_workers",
        type=int,
        help="Maximum number of worker threads (default: 10)",
    )
    performance_group.add_argument(
        "--no-progress",
        dest="no_progress",
        action="store_true",
        help="Disable progress bars",
    )
    performance_group.add_argument(
        "--profile",
        dest="profile",
        action="store_true",
        help="Enable performance profiling and report",
    )
    performance_group.add_argument(
        "--detailed-profile",
        dest="detailed_profile",
        action="store_true",
        help="Include detailed profiling information in report (requires --profile)",
    )

    # UI options
    ui_group = parser.add_argument_group("UI options")
    ui_group.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        help="Disable colored output",
    )
    ui_group.add_argument(
        "--no-resource-monitor",
        dest="no_resource_monitor",
        action="store_true",
        help="Disable system resource monitoring",
    )
    ui_group.add_argument(
        "--no-adaptive-rate",
        dest="no_adaptive_rate",
        action="store_true",
        help="Disable adaptive rate limiting",
    )

    # Filtering options
    filter_group = parser.add_argument_group("Filtering options")
    filter_group.add_argument(
        "--blacklist",
        dest="blacklist",
        help="Comma-separated list of applications to ignore",
    )
    filter_group.add_argument(
        "--additional-dirs",
        dest="additional_dirs",
        help="Colon-separated list of additional directories to scan for applications",
    )
    filter_group.add_argument(
        "--similarity",
        dest="similarity",
        type=int,
        help="Similarity threshold for matching (0-100, default: 75)",
    )
    filter_group.add_argument(
        "--no-enhanced-matching",
        dest="no_enhanced_matching",
        action="store_true",
        help="Disable enhanced fuzzy matching (use basic matching instead)",
    )
    filter_group.add_argument(
        "--exclude-auto-updates",
        dest="exclude_auto_updates",
        action="store_true",
        help="Exclude applications that have auto-updates enabled in Homebrew",
    )
    filter_group.add_argument(
        "--only-auto-updates",
        dest="only_auto_updates",
        action="store_true",
        help="Only show applications that have auto-updates enabled in Homebrew",
    )

    # Filter management
    filter_management_group = parser.add_argument_group("Filter management")
    filter_management_group.add_argument(
        "--save-filter",
        dest="save_filter",
        metavar="NAME",
        help="Save current filter settings with the given name",
    )
    filter_management_group.add_argument(
        "--load-filter",
        dest="load_filter",
        metavar="NAME",
        help="Load saved filter settings with the given name",
    )
    filter_management_group.add_argument(
        "--list-filters",
        dest="list_filters",
        action="store_true",
        help="List all saved filters",
    )
    filter_management_group.add_argument(
        "--delete-filter",
        dest="delete_filter",
        metavar="NAME",
        help="Delete a saved filter",
    )

    # Export options
    export_group = parser.add_argument_group("Export options")
    export_group.add_argument(
        "--export",
        dest="export_format",
        choices=["json", "csv"],
        help="Export results in specified format (json or csv)",
    )
    export_group.add_argument(
        "--output-file",
        dest="output_file",
        help="Specify the output file for export (default: print to stdout)",
    )

    # Configuration options
    config_group = parser.add_argument_group("Configuration options")
    config_group.add_argument(
        "--generate-config",
        dest="generate_config",
        action="store_true",
        help="Generate a default configuration file at ~/.config/versiontracker/config.yaml",
    )
    config_group.add_argument(
        "--config-path",
        dest="config_path",
        help=(
            "Specify an alternative path for the configuration file (can be used both for "
            "generating a config file with --generate-config and for using a custom config "
            "file location when running the application)"
        ),
    )
    config_group.add_argument(
        "--service-interval",
        dest="service_interval",
        type=int,
        default=24,
        help="Interval in hours for scheduled service (default: 24)",
    )
    config_group.add_argument(
        "--notify",
        dest="notify",
        action="store_true",
        help="Send macOS notification with results",
    )

    # Main command group (mutually exclusive)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-a",
        "--apps",
        action="store_true",
        dest="apps",
        help="return Apps in Applications/ that is not updated by App Store",
    )
    group.add_argument(
        "-b",
        "--brews",
        action="store_true",
        dest="brews",
        help="return installable brews",
    )
    group.add_argument(
        "-r",
        "--recommend",
        action="store_true",
        dest="recom",
        help="return recommendations for brew",
    )
    group.add_argument(
        "--strict-recommend",
        action="store_true",
        dest="strict_recom",
        help=("return recommendations for brew, excluding apps that can already be installed with brew"),
    )
    group.add_argument(
        "-o",
        "--outdated",
        action="store_true",
        dest="check_outdated",
        help="check for outdated applications compared to Homebrew versions",
    )
    group.add_argument(
        "--blacklist-auto-updates",
        action="store_true",
        dest="blacklist_auto_updates",
        help="Add all applications with auto-updates to the blacklist",
    )
    group.add_argument(
        "--uninstall-auto-updates",
        action="store_true",
        dest="uninstall_auto_updates",
        help="Uninstall all Homebrew casks that have auto-updates enabled (with confirmation)",
    )
    group.add_argument(
        "--install-service",
        action="store_true",
        dest="install_service",
        help="Install macOS scheduled checker service (launchd)",
    )
    group.add_argument(
        "--uninstall-service",
        action="store_true",
        dest="uninstall_service",
        help="Uninstall macOS scheduled checker service",
    )
    group.add_argument(
        "--service-status",
        action="store_true",
        dest="service_status",
        help="Show status of macOS scheduled checker service",
    )
    group.add_argument(
        "--test-notification",
        action="store_true",
        dest="test_notification",
        help="Send a test macOS notification",
    )
    group.add_argument(
        "--menubar",
        action="store_true",
        dest="menubar",
        help="Launch macOS menubar application",
    )
    group.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    # If no arguments were provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()
