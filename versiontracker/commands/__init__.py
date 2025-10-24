"""
Commands package for VersionTracker CLI operations.

This package contains modular command implementations that can be used
to organize CLI functionality into smaller, more maintainable pieces.
"""

from typing import Any

__all__ = [
    "BaseCommand",
    "CommandRegistry",
]


class BaseCommand:
    """Base class for all VersionTracker commands."""

    name: str = ""
    description: str = ""

    def execute(self, options: Any) -> int:
        """Execute the command with the given options.

        Args:
            options: Parsed command-line arguments

        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        raise NotImplementedError("Subclasses must implement execute method")

    def validate_options(self, options: Any) -> bool:
        """Validate command-specific options.

        Args:
            options: Parsed command-line arguments

        Returns:
            bool: True if options are valid, False otherwise
        """
        return True


class CommandRegistry:
    """Registry for managing available commands."""

    def __init__(self) -> None:
        """Initialize the command registry."""
        self._commands: dict[str, type[BaseCommand]] = {}

    def register(self, command_class: type[BaseCommand]) -> None:
        """Register a command class.

        Args:
            command_class: Command class to register
        """
        if not command_class.name:
            raise ValueError(f"Command {command_class.__name__} must have a name")

        self._commands[command_class.name] = command_class

    def get_command(self, name: str) -> type[BaseCommand] | None:
        """Get a command class by name.

        Args:
            name: Command name

        Returns:
            type[BaseCommand] | None: Command class or None if not found
        """
        return self._commands.get(name)

    def list_commands(self) -> list[str]:
        """Get list of registered command names.

        Returns:
            list[str]: List of command names
        """
        return list(self._commands.keys())


# Global command registry instance
registry = CommandRegistry()
