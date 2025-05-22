"""VersionTracker - CLI versiontracker and update tool for macOS.

This package provides tools to track and manage application versions on macOS,
with a focus on applications installed outside of the App Store. It helps
identify which applications can be managed via Homebrew, checks for outdated
applications, and provides recommendations for better application management.

Key features:
- List applications in /Applications/ not updated by the App Store
- List all currently installed Homebrew casks
- Recommend which applications could be managed through Homebrew
- Check for outdated applications by comparing with latest Homebrew versions
- Export results in machine-readable formats (JSON and CSV)

This package is designed for macOS users who want to keep their applications
up to date and well-managed, especially those who use a mix of App Store and
non-App Store applications.

Main components:
- apps.py: Core functionality for application discovery and version checking
- cli.py: Command-line interface parsing and handling
- config.py: Configuration management and validation
- handlers/: Command handler implementations
- ui.py: User interface components including progress bars and colored output

For detailed usage instructions, see the README.md or run:
    versiontracker --help
"""

__version__ = "0.6.4"

# Define public exports for better usability when importing
from versiontracker.apps import get_applications, get_homebrew_casks
from versiontracker.config import Config, get_config
from versiontracker.exceptions import VersionTrackerError

# Explicitly define what should be imported with "from versiontracker import *"
__all__ = [
    "__version__",
    "get_applications",
    "get_homebrew_casks",
    "Config",
    "get_config",
    "VersionTrackerError",
]
