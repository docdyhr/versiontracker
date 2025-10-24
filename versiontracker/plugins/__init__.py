"""Plugin system architecture for VersionTracker.

This module provides a flexible plugin system that allows extending VersionTracker
functionality through modular plugins. Plugins can add new commands, data sources,
matching algorithms, and export formats.
"""

import importlib
import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

from versiontracker.config import get_config
from versiontracker.exceptions import VersionTrackerError

T = TypeVar("T", bound="BasePlugin")

logger = logging.getLogger(__name__)

__all__ = [
    "BasePlugin",
    "CommandPlugin",
    "DataSourcePlugin",
    "MatchingPlugin",
    "ExportPlugin",
    "PluginManager",
    "plugin_manager",
    "register_plugin",
    "get_plugin",
    "load_plugins",
]


class PluginError(VersionTrackerError):
    """Raised when plugin operations fail."""

    pass


class BasePlugin(ABC):
    """Base class for all VersionTracker plugins."""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    requires_versiontracker: str = ">=0.7.0"

    def __init__(self) -> None:
        """Initialize the plugin."""
        self._enabled = True
        self._initialized = False

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled

    @property
    def initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin. Called when plugin is loaded."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources. Called when plugin is unloaded."""
        pass

    def enable(self) -> None:
        """Enable the plugin."""
        self._enabled = True
        logger.info(f"Plugin '{self.name}' enabled")

    def disable(self) -> None:
        """Disable the plugin."""
        self._enabled = False
        logger.info(f"Plugin '{self.name}' disabled")

    def get_info(self) -> dict[str, Any]:
        """Get plugin information."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "requires_versiontracker": self.requires_versiontracker,
            "enabled": self.enabled,
            "initialized": self.initialized,
        }

    def validate_requirements(self) -> bool:
        """Validate plugin requirements against current VersionTracker version."""
        # This would need version comparison logic
        # For now, return True
        return True


class CommandPlugin(BasePlugin):
    """Base class for command plugins that add new CLI commands."""

    @abstractmethod
    def get_commands(self) -> dict[str, Any]:
        """Get command definitions provided by this plugin.

        Returns:
            Dict mapping command names to command classes
        """
        pass

    @abstractmethod
    def execute_command(self, command: str, options: Any) -> int:
        """Execute a command provided by this plugin.

        Args:
            command: Command name to execute
            options: Parsed command line arguments

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        pass


class DataSourcePlugin(BasePlugin):
    """Base class for data source plugins that add new application/version sources."""

    @abstractmethod
    def discover_applications(self, paths: list[Path] | None = None) -> list[dict[str, Any]]:
        """Discover applications from this data source.

        Args:
            paths: Optional list of paths to search

        Returns:
            List of application dictionaries
        """
        pass

    @abstractmethod
    def get_version_info(self, app_name: str) -> dict[str, Any] | None:
        """Get version information for a specific application.

        Args:
            app_name: Application name

        Returns:
            Version information dictionary or None if not found
        """
        pass

    def supports_platform(self, platform: str) -> bool:
        """Check if this data source supports the given platform.

        Args:
            platform: Platform name (e.g., 'darwin', 'linux', 'windows')

        Returns:
            True if platform is supported
        """
        return True


class MatchingPlugin(BasePlugin):
    """Base class for matching algorithm plugins."""

    @abstractmethod
    def match_applications(
        self, apps: list[dict[str, Any]], casks: list[dict[str, Any]], threshold: float = 0.8
    ) -> list[dict[str, Any]]:
        """Match applications to casks using custom algorithm.

        Args:
            apps: List of application dictionaries
            casks: List of cask dictionaries
            threshold: Matching threshold

        Returns:
            List of match dictionaries
        """
        pass

    @abstractmethod
    def calculate_similarity(self, app_name: str, cask_name: str) -> float:
        """Calculate similarity score between app and cask names.

        Args:
            app_name: Application name
            cask_name: Cask name

        Returns:
            Similarity score between 0.0 and 1.0
        """
        pass


class ExportPlugin(BasePlugin):
    """Base class for export format plugins."""

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Get list of supported export formats.

        Returns:
            List of format names (e.g., ['xml', 'yaml'])
        """
        pass

    @abstractmethod
    def export_data(
        self,
        data: list[dict[str, Any]],
        output_file: Path | None = None,
        format_options: dict[str, Any] | None = None,
    ) -> str:
        """Export data in plugin's format.

        Args:
            data: Data to export
            output_file: Optional output file path
            format_options: Format-specific options

        Returns:
            Formatted string
        """
        pass


class PluginManager:
    """Manages loading, registration, and execution of plugins."""

    def __init__(self) -> None:
        """Initialize plugin manager."""
        self._plugins: dict[str, BasePlugin] = {}
        self._plugin_types: dict[str, list[BasePlugin]] = {
            "CommandPlugin": [],
            "DataSourcePlugin": [],
            "MatchingPlugin": [],
            "ExportPlugin": [],
        }
        self._loaded_modules: dict[str, Any] = {}

    def register_plugin(self, plugin: BasePlugin) -> None:
        """Register a plugin instance.

        Args:
            plugin: Plugin instance to register

        Raises:
            PluginError: If plugin registration fails
        """
        if not plugin.name:
            raise PluginError(f"Plugin {plugin.__class__.__name__} must have a name")

        if plugin.name in self._plugins:
            raise PluginError(f"Plugin '{plugin.name}' is already registered")

        if not plugin.validate_requirements():
            raise PluginError(f"Plugin '{plugin.name}' requirements not met")

        try:
            plugin.initialize()
            plugin._initialized = True

            self._plugins[plugin.name] = plugin

            # Add to type-specific lists
            plugin_class_name = plugin.__class__.__name__
            if plugin_class_name in self._plugin_types:
                self._plugin_types[plugin_class_name].append(plugin)

            logger.info(f"Plugin '{plugin.name}' registered successfully")

        except Exception as e:
            raise PluginError(f"Failed to initialize plugin '{plugin.name}': {str(e)}") from e

    def unregister_plugin(self, name: str) -> None:
        """Unregister a plugin by name.

        Args:
            name: Plugin name to unregister

        Raises:
            PluginError: If plugin not found or unregistration fails
        """
        if name not in self._plugins:
            raise PluginError(f"Plugin '{name}' not found")

        plugin = self._plugins[name]

        try:
            plugin.cleanup()

            # Remove from type-specific lists
            plugin_class_name = plugin.__class__.__name__
            if plugin_class_name in self._plugin_types:
                self._plugin_types[plugin_class_name].remove(plugin)

            del self._plugins[name]
            logger.info(f"Plugin '{name}' unregistered successfully")

        except Exception as e:
            raise PluginError(f"Failed to cleanup plugin '{name}': {str(e)}") from e

    def get_plugin(self, name: str) -> BasePlugin | None:
        """Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name)

    def get_plugins_by_type(self, plugin_type_name: str) -> list[BasePlugin]:
        """Get all plugins of a specific type.

        Args:
            plugin_type_name: Plugin type class name

        Returns:
            List of plugins of the specified type
        """
        return self._plugin_types.get(plugin_type_name, [])

    def list_plugins(self) -> list[str]:
        """Get list of registered plugin names.

        Returns:
            List of plugin names
        """
        return list(self._plugins.keys())

    def get_plugin_info(self, name: str) -> dict[str, Any] | None:
        """Get information about a plugin.

        Args:
            name: Plugin name

        Returns:
            Plugin information dictionary or None if not found
        """
        plugin = self.get_plugin(name)
        return plugin.get_info() if plugin else None

    def load_plugin_from_file(self, plugin_file: Path) -> None:
        """Load a plugin from a Python file.

        Args:
            plugin_file: Path to plugin file

        Raises:
            PluginError: If plugin loading fails
        """
        if not plugin_file.exists():
            raise PluginError(f"Plugin file not found: {plugin_file}")

        module_name = f"versiontracker_plugin_{plugin_file.stem}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                raise PluginError(f"Cannot create module spec for {plugin_file}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self._loaded_modules[module_name] = module

            # Look for plugin classes in the module
            for _name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BasePlugin)
                    and obj != BasePlugin
                    and not inspect.isabstract(obj)
                ):
                    plugin_instance = obj()
                    self.register_plugin(plugin_instance)

        except Exception as e:
            raise PluginError(f"Failed to load plugin from {plugin_file}: {str(e)}") from e

    def load_plugins_from_directory(self, plugin_dir: Path) -> None:
        """Load all plugins from a directory.

        Args:
            plugin_dir: Directory containing plugin files
        """
        if not plugin_dir.exists() or not plugin_dir.is_dir():
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return

        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("__"):
                continue

            try:
                self.load_plugin_from_file(plugin_file)
            except PluginError as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")

    def enable_plugin(self, name: str) -> None:
        """Enable a plugin.

        Args:
            name: Plugin name

        Raises:
            PluginError: If plugin not found
        """
        plugin = self.get_plugin(name)
        if not plugin:
            raise PluginError(f"Plugin '{name}' not found")
        plugin.enable()

    def disable_plugin(self, name: str) -> None:
        """Disable a plugin.

        Args:
            name: Plugin name

        Raises:
            PluginError: If plugin not found
        """
        plugin = self.get_plugin(name)
        if not plugin:
            raise PluginError(f"Plugin '{name}' not found")
        plugin.disable()

    def cleanup_all(self) -> None:
        """Cleanup all registered plugins."""
        for name in list(self._plugins.keys()):
            try:
                self.unregister_plugin(name)
            except PluginError as e:
                logger.error(f"Failed to cleanup plugin '{name}': {e}")


# Global plugin manager instance
plugin_manager = PluginManager()


def register_plugin(plugin: BasePlugin) -> None:
    """Register a plugin with the global plugin manager.

    Args:
        plugin: Plugin instance to register
    """
    plugin_manager.register_plugin(plugin)


def get_plugin(name: str) -> BasePlugin | None:
    """Get a plugin by name from the global plugin manager.

    Args:
        name: Plugin name

    Returns:
        Plugin instance or None if not found
    """
    return plugin_manager.get_plugin(name)


def load_plugins() -> None:
    """Load plugins from configured directories."""
    config = get_config()

    # Load from user plugin directory
    user_plugins_dir = Path.home() / ".config" / "versiontracker" / "plugins"
    if user_plugins_dir.exists():
        plugin_manager.load_plugins_from_directory(user_plugins_dir)

    # Load from system plugin directory if configured
    if hasattr(config, "plugin_directories"):
        for plugin_dir in config.plugin_directories:
            plugin_manager.load_plugins_from_directory(Path(plugin_dir))
