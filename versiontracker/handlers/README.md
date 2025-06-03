# VersionTracker Handlers Package

This directory contains modules that implement command handlers for the VersionTracker CLI.

## Purpose

The handlers package was created as part of the refactoring of the `__main__.py` file, breaking down the monolithic design into smaller, more maintainable modules. Each handler module is responsible for a specific subset of the CLI's functionality.

## Structure

- **app_handlers.py**: Functions for handling application listing operations
- **brew_handlers.py**: Functions for handling Homebrew-related operations
- **config_handlers.py**: Functions for configuration generation and management
- **export_handlers.py**: Functions for exporting data in various formats
- **outdated_handlers.py**: Functions for checking outdated applications
- **ui_handlers.py**: Functions for UI elements like status icons and colors
- **utils_handlers.py**: Utility functions for logging, error handling, etc.

## Design Patterns

These modules follow a command pattern approach, where each handler:

1. Takes command-line options as input
2. Performs actions based on those options
3. Returns an exit code (0 for success, non-zero for failure)

## Usage

Handler functions are imported and called from the main entry point in `__main__.py`. They should not be called directly by other parts of the application.

Example:

```python
from versiontracker.handlers import handle_list_apps

# In the main function:
result = handle_list_apps(options)
```

## Testing

Each handler module should have corresponding test files in the `tests/handlers/` directory.

## Future Development

When adding new CLI commands, create appropriate handler functions in these modules or add new modules as needed. Keep handler functions focused on a single responsibility.
