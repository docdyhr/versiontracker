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
    parser.add_argument("-D", "--debug", dest="debug", help="turn on DEBUG mode")

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
        help="return recommendations for brew, excluding apps that can already be installed with brew",
    )
    group.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    # If no arguments were provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args()
