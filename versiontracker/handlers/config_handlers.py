"""Configuration handlers for VersionTracker.

This module contains handler functions for configuration-related commands
in VersionTracker, specifically for generating and managing configuration files.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

import logging
from pathlib import Path
from typing import Any

from versiontracker.config import get_config


def handle_config_generation(options: Any) -> int:
    """Handle configuration file generation.
    
    Creates a default configuration file at the specified path or at
    the default location (~/.config/versiontracker/config.yaml).

    Args:
        options: Command line options containing parameters like config_path.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
        
    Raises:
        Exception: If there's an error generating the configuration file
    """
    try:
        config_path = None
        if options.config_path:
            config_path = Path(options.config_path)

        path = get_config().generate_default_config(config_path)
        print(f"Configuration file generated: {path}")
        print("You can now edit this file to customize VersionTracker's behavior.")
        return 0
    except Exception as e:
        logging.error(f"Failed to generate configuration file: {e}")
        return 1