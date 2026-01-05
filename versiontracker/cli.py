"""Command-line interface for VersionTracker.

This module provides argument parsing for the versiontracker command.
The actual entry point is in __main__.py which uses get_arguments() from here.
"""

import argparse
from typing import Any

from versiontracker import __version__


def get_arguments() -> Any:
    """Parse command line arguments.

    Returns:
        Parsed command-line arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="VersionTracker - Application version management for macOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  versiontracker --apps              List installed applications
  versiontracker --brews             List Homebrew casks
  versiontracker --recom             Recommend Homebrew casks for installed apps
  versiontracker --check-outdated    Check for outdated applications

For more information, visit: https://github.com/docdyhr/versiontracker
        """,
    )

    # Global options
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit",
    )

    # Main action flags (mutually exclusive for actions)
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--apps",
        "-a",
        action="store_true",
        help="List installed applications not from App Store",
    )
    action_group.add_argument(
        "--brews",
        "-b",
        action="store_true",
        help="List installed Homebrew casks",
    )
    action_group.add_argument(
        "--recom",
        "--recommend",
        "-r",
        dest="recom",
        action="store_true",
        help="Recommend Homebrew casks for installed apps",
    )
    action_group.add_argument(
        "--strict-recom",
        "--strict-recommend",
        dest="strict_recom",
        action="store_true",
        help="Strict recommendations for Homebrew casks",
    )
    action_group.add_argument(
        "--check-outdated",
        "-o",
        dest="check_outdated",
        action="store_true",
        help="Check for outdated applications",
    )

    # Auto-update management (mutually exclusive)
    auto_update_group = parser.add_mutually_exclusive_group()
    auto_update_group.add_argument(
        "--blocklist-auto-updates",
        dest="blocklist_auto_updates",
        action="store_true",
        help="Add applications with auto-updates to the blocklist",
    )
    auto_update_group.add_argument(
        "--blacklist-auto-updates",
        dest="blacklist_auto_updates",
        action="store_true",
        help="(Deprecated) Use --blocklist-auto-updates instead",
    )
    auto_update_group.add_argument(
        "--uninstall-auto-updates",
        dest="uninstall_auto_updates",
        action="store_true",
        help="Uninstall all Homebrew casks that have auto-updates",
    )

    # Filter options for auto-updates
    parser.add_argument(
        "--exclude-auto-updates",
        dest="exclude_auto_updates",
        action="store_true",
        help="Exclude applications that have auto-updates enabled",
    )
    parser.add_argument(
        "--only-auto-updates",
        dest="only_auto_updates",
        action="store_true",
        help="Only show applications that have auto-updates enabled",
    )

    # Service management options
    service_group = parser.add_argument_group("macOS Service Options")
    service_group.add_argument(
        "--install-service",
        dest="install_service",
        action="store_true",
        help="Install scheduled checker service",
    )
    service_group.add_argument(
        "--uninstall-service",
        dest="uninstall_service",
        action="store_true",
        help="Uninstall scheduled checker service",
    )
    service_group.add_argument(
        "--service-status",
        dest="service_status",
        action="store_true",
        help="Check service status",
    )
    service_group.add_argument(
        "--test-notification",
        dest="test_notification",
        action="store_true",
        help="Test macOS notification",
    )
    service_group.add_argument(
        "--menubar",
        action="store_true",
        help="Launch menubar application",
    )

    # Configuration options
    config_group = parser.add_argument_group("Configuration Options")
    config_group.add_argument(
        "--config",
        "-c",
        type=str,
        metavar="PATH",
        help="Path to configuration file",
    )
    config_group.add_argument(
        "--generate-config",
        dest="generate_config",
        action="store_true",
        help="Generate default configuration file",
    )

    # Export options
    export_group = parser.add_argument_group("Export Options")
    export_group.add_argument(
        "--export",
        dest="export_format",
        choices=["json", "yaml", "csv"],
        metavar="FORMAT",
        help="Export results in specified format (json, yaml, csv)",
    )

    # Filter management
    filter_group = parser.add_argument_group("Filter Management")
    filter_group.add_argument(
        "--save-filter",
        dest="save_filter",
        type=str,
        metavar="NAME",
        help="Save current query settings as named filter",
    )
    filter_group.add_argument(
        "--load-filter",
        dest="load_filter",
        type=str,
        metavar="NAME",
        help="Load a saved filter by name",
    )
    filter_group.add_argument(
        "--list-filters",
        dest="list_filters",
        action="store_true",
        help="List all saved filters",
    )
    filter_group.add_argument(
        "--delete-filter",
        dest="delete_filter",
        type=str,
        metavar="NAME",
        help="Delete a saved filter",
    )

    # Debugging and profiling
    debug_group = parser.add_argument_group("Debugging Options")
    debug_group.add_argument(
        "--debug",
        "-d",
        action="count",
        default=0,
        help="Enable debug output (use -dd for verbose debug)",
    )
    debug_group.add_argument(
        "--profile",
        action="store_true",
        help="Enable performance profiling",
    )
    debug_group.add_argument(
        "--detailed-profile",
        dest="detailed_profile",
        action="store_true",
        help="Show detailed profiling information",
    )

    # Performance options
    perf_group = parser.add_argument_group("Performance Options")
    perf_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    perf_group.add_argument(
        "--max-workers",
        dest="max_workers",
        type=int,
        metavar="N",
        help="Maximum number of worker threads",
    )
    perf_group.add_argument(
        "--rate-limit",
        dest="rate_limit",
        type=float,
        metavar="SECONDS",
        help="Rate limit for network requests (seconds)",
    )
    perf_group.add_argument(
        "--no-progress",
        dest="no_progress",
        action="store_true",
        help="Disable progress bar",
    )

    # Filtering options
    filtering_group = parser.add_argument_group("Filtering Options")
    filtering_group.add_argument(
        "--blocklist",
        type=str,
        metavar="APPS",
        help="Comma-separated list of applications to exclude",
    )
    filtering_group.add_argument(
        "--blacklist",
        type=str,
        metavar="APPS",
        help="(Deprecated) Use --blocklist instead",
    )
    filtering_group.add_argument(
        "--brew-filter",
        dest="brew_filter",
        action="store_true",
        help="Filter out applications already managed by Homebrew",
    )
    filtering_group.add_argument(
        "--similarity",
        type=float,
        metavar="THRESHOLD",
        help="Similarity threshold for matching (0-100, default: 75)",
    )
    filtering_group.add_argument(
        "--additional-dirs",
        dest="additional_dirs",
        type=str,
        metavar="DIRS",
        help="Colon-separated list of additional directories to scan",
    )

    return parser.parse_args()
