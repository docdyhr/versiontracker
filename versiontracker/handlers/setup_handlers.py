"""Setup handlers for VersionTracker.

This module contains handler functions for initialization and
setup operations for VersionTracker.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

import logging
from typing import Any

from versiontracker.config import Config, get_config


def handle_initialize_config(options: Any) -> int:
    """Initialize or update the configuration.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Initialize config with provided config file if any
        config_file = options.config if hasattr(options, "config") else None

        # Check if config needs initialization (avoid if mocked in tests)
        try:
            if not hasattr(get_config(), "_config"):
                # Create a new Config instance if needed
                Config(config_file=config_file)
        except Exception as e:
            logging.debug(f"Config initialization error: {e}")
            # Create a new Config instance with defaults
            Config()

        return 0
    except Exception as e:
        logging.error(f"Failed to initialize configuration: {e}")
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
            current_config._config["ui"]["use_color"] = False

        if hasattr(options, "no_progress") and options.no_progress:
            current_config._config["ui"]["show_progress"] = False

        if hasattr(options, "no_adaptive_rate") and options.no_adaptive_rate:
            current_config._config["ui"]["adaptive_rate_limiting"] = False

        return 0
    except Exception as e:
        logging.error(f"Failed to configure options: {e}")
        return 1


def handle_setup_logging(options: Any) -> int:
    """Set up logging based on command-line options.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, non-zero for failure)
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
        logging.debug("Logging setup complete with level: %s", logging.getLevelName(logging.getLogger().level))

        return 0
    except Exception as e:
        # If logging setup fails, try a basic configuration and log the error
        try:
            logging.basicConfig(level=logging.WARNING)
            logging.error(f"Error setting up logging: {e}")
        except Exception:
            pass  # Last resort if even basic logging fails
        return 1
