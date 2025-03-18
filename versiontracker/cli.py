"""Command Line Interface for VersionTracker."""

import argparse
import sys
import textwrap

from versiontracker import __version__


def get_arguments():
    """Return a dict of command line arguments (cli).

    Returns:
        argparse.Namespace: The parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
         thomas@dyhr.com 2022
         """
        ),
    )

    # Debug mode
    parser.add_argument(
        "-D", "--debug",
        dest="debug",
        action="store_true",
        help="turn on DEBUG mode"
    )

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
        help=(
            "return recommendations for brew, excluding apps that can already be "
            "installed with brew"
        ),
    )
    group.add_argument(
        "-o",
        "--outdated",
        action="store_true",
        dest="check_outdated",
        help="check for outdated applications compared to Homebrew versions",
    )
    group.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    # If no arguments were provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()
