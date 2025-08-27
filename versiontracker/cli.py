"""
Command-line interface for VersionTracker.

This module provides the main entry point for the versiontracker command.
"""

import sys

import click

from versiontracker import __version__
from versiontracker.config import get_config
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
        if config:
            from versiontracker.config import Config

            cfg = Config(config_file=config)
        else:
            cfg = get_config()

        if verbose:
            click.echo(f"VersionTracker v{__version__}")
            click.echo(f"Configuration loaded from: {config or 'defaults'}")
            click.echo(f"Max workers: {cfg.max_workers}")
            click.echo(f"Cache directory: {cfg.cache_dir}")

        # Placeholder for main functionality
        click.echo(f"VersionTracker v{__version__} - Ready for commands")
        click.echo("Use --help for available options")

    except VersionTrackerError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def get_arguments():
    """Legacy function for test compatibility."""
    import argparse

    parser = argparse.Namespace()
    parser.config = None
    parser.verbose = False
    return parser


if __name__ == "__main__":
    main()
