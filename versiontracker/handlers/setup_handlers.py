"""Setup handlers for VersionTracker.

This module contains handler functions for initialization and
setup operations for VersionTracker.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from versiontracker.config import Config, get_config, set_global_config
from versiontracker.exceptions import ConfigError


def handle_initialize_config(options: Any) -> int:
    """Initialize the global configuration, honoring --config PATH if given.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    config_file = getattr(options, "config", None)

    if config_file:
        config_path = Path(config_file)
        if not config_path.exists():
            logging.error("Configuration file not found: %s", config_path)
            return 1
        try:
            new_config = Config(config_file=config_file)
        except ConfigError as e:
            logging.error("Failed to load configuration file %s: %s", config_path, e)
            return 1
        set_global_config(new_config)
        logging.debug("Loaded configuration from %s", config_path)
        return 0

    try:
        get_config()
        return 0
    except (OSError, ValueError, ConfigError) as e:
        logging.error("Failed to initialize configuration: %s", e)
        return 1


def handle_configure_from_options(options: Any) -> int:
    """Configure settings based on command-line options.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Retrieve the potentially updated config instance
        current_config = get_config()

        # Configure UI options from command-line arguments
        if hasattr(options, "no_color") and options.no_color:
            current_config.set("ui.use_color", False)

        if hasattr(options, "no_progress") and options.no_progress:
            # no_progress is the canonical key; Config.show_progress is derived from it
            current_config.set("no_progress", True)

        if hasattr(options, "no_adaptive_rate") and options.no_adaptive_rate:
            current_config.set("ui.adaptive_rate_limiting", False)

        if hasattr(options, "max_workers") and options.max_workers:
            current_config.set("max_workers", options.max_workers)

        return 0
    except (AttributeError, ValueError, ConfigError) as e:
        logging.error("Failed to configure options: %s", e)
        return 1


def handle_setup_logging(options: Any) -> None:
    """Set up logging based on command-line options.

    Args:
        options: Command line options
    """
    try:
        # Configure logging based on debug option
        debug_level = getattr(options, "debug", 0)

        if debug_level == 1:
            logging.basicConfig(level=logging.INFO)
        elif debug_level >= 2:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)

        # Log some initial debug information
        logging.debug(
            "Logging setup complete with level: %s",
            logging.getLevelName(logging.getLogger().level),
        )
    except (ValueError, TypeError, OSError) as e:
        # If logging setup fails, try a basic configuration and log the error
        try:
            logging.basicConfig(level=logging.WARNING)
            logging.error("Error setting up logging: %s", e)
        except (ValueError, OSError) as basic_error:
            # Last resort if even basic logging fails - print to stderr
            print(f"Critical error: Unable to set up logging: {e}", file=sys.stderr)
            print(f"Basic logging also failed: {basic_error}", file=sys.stderr)
