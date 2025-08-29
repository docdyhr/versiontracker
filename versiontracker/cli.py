"""
Command-line interface for VersionTracker.

This module provides the main entry point for the versiontracker command.
"""

import argparse
import sys
import traceback
from typing import Any

import click

from versiontracker import __version__
from versiontracker.exceptions import VersionTrackerError


@click.command()
@click.version_option(version=__version__, prog_name="versiontracker")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
def main(config: str | None, verbose: bool) -> None:
    """
    VersionTracker - Application version management for macOS.

    A command-line tool for tracking and managing applications installed
    outside of the Mac App Store, with Homebrew cask integration.
    """
    try:
        # Load configuration

        from versiontracker.config import Config, get_config

        if config:
            cfg = Config(config_file=config)
        else:
            cfg = get_config()

        if verbose:
            click.echo(f"VersionTracker v{__version__}")
            click.echo(f"Configuration loaded from: {config or 'defaults'}")
            max_workers = getattr(cfg, "max_workers", "N/A")
            cache_dir = getattr(cfg, "cache_dir", "N/A")
            click.echo(f"Max workers: {max_workers}")
            click.echo(f"Cache directory: {cache_dir}")

        # Placeholder for main functionality
        click.echo(f"VersionTracker v{__version__} - Ready for commands")
        click.echo("Use --help for available options")

    except VersionTrackerError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        # Intentional broad exception catch to ensure all errors
        # are reported to the user
        click.echo(f"Unexpected error: {e}", err=True)
        if verbose:
            traceback.print_exc()
        sys.exit(1)


def get_arguments() -> Any:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=("VersionTracker - Application version management for macOS"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Main action flags (mutually exclusive for actions)
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--apps",
        action="store_true",
        help="List installed applications",
    )
    action_group.add_argument(
        "--brews",
        action="store_true",
        help="List Homebrew casks",
    )
    action_group.add_argument(
        "--recom",
        "--recommend",
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
        dest="check_outdated",
        action="store_true",
        help="Check for outdated applications",
    )

    # Auto-update management (mutually exclusive)
    auto_update_group = parser.add_mutually_exclusive_group()
    auto_update_group.add_argument(
        "--blacklist-auto-updates",
        dest="blacklist_auto_updates",
        action="store_true",
        help="Add all applications with auto-updates to the blocklist",
    )
    auto_update_group.add_argument(
        "--blocklist-auto-updates",
        dest="blocklist_auto_updates",
        action="store_true",
        help="Blocklist applications with auto-update features",
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
        help="Exclude applications that have auto-updates",
    )
    parser.add_argument(
        "--only-auto-updates",
        dest="only_auto_updates",
        action="store_true",
        help="Only show applications that have auto-updates",
    )

    # Service management options
    parser.add_argument(
        "--install-service",
        dest="install_service",
        action="store_true",
        help="Install macOS service",
    )
    parser.add_argument(
        "--uninstall-service",
        dest="uninstall_service",
        action="store_true",
        help="Uninstall macOS service",
    )
    parser.add_argument(
        "--service-status",
        dest="service_status",
        action="store_true",
        help="Check macOS service status",
    )
    parser.add_argument(
        "--test-notification",
        dest="test_notification",
        action="store_true",
        help="Test macOS notification",
    )
    parser.add_argument(
        "--menubar",
        action="store_true",
        help="Launch menubar app",
    )

    # Configuration options
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--generate-config",
        dest="generate_config",
        action="store_true",
        help="Generate default configuration file",
    )

    # Export options
    parser.add_argument(
        "--export",
        dest="export_format",
        choices=["json", "yaml", "csv"],
        help="Export results in specified format",
    )

    # Filter management
    parser.add_argument(
        "--save-filter",
        dest="save_filter",
        type=str,
        help="Save current query as named filter",
    )

    # Debugging and profiling
    parser.add_argument(
        "--debug",
        "-d",
        action="count",
        default=0,
        help="Enable debug output (use -dd for verbose debug)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable performance profiling",
    )
    parser.add_argument(
        "--detailed-profile",
        dest="detailed_profile",
        action="store_true",
        help="Show detailed profiling information",
    )

    # Other common options
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--max-workers",
        dest="max_workers",
        type=int,
        help="Maximum number of worker threads",
    )
    parser.add_argument(
        "--rate-limit",
        dest="rate_limit",
        type=float,
        help="Rate limit for network requests",
    )
    parser.add_argument(
        "--blacklist",
        type=str,
        help="Blacklist of applications to exclude",
    )
    parser.add_argument(
        "--blocklist",
        type=str,
        help="Blocklist of applications to exclude",
    )
    parser.add_argument(
        "--brew-filter",
        dest="brew_filter",
        action="store_true",
        help="Filter out Homebrew casks from results",
    )
    parser.add_argument(
        "--no-progress",
        dest="no_progress",
        action="store_true",
        help="Disable progress bar",
    )
    parser.add_argument(
        "--similarity",
        type=float,
        help="Similarity threshold for matching",
    )
    parser.add_argument(
        "--additional-dirs",
        dest="additional_dirs",
        type=str,
        help="Additional directories to search",
    )

    return parser.parse_args()


if __name__ == "__main__":
    # Provide default arguments for main() if run directly
    main(None, False)
