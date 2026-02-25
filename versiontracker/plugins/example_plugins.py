"""Example plugins to demonstrate the VersionTracker plugin system.

This module contains example implementations of various plugin types
to show how to extend VersionTracker functionality.
"""

import datetime
import difflib
import logging
import xml.etree.ElementTree as ET  # nosec B405
from pathlib import Path
from typing import Any

import yaml

from versiontracker.plugins import (
    CommandPlugin,
    DataSourcePlugin,
    ExportPlugin,
    MatchingPlugin,
)

logger = logging.getLogger(__name__)


class XMLExportPlugin(ExportPlugin):
    """Example plugin for exporting data in XML format."""

    name = "xml_export"
    version = "1.0.0"
    description = "Export VersionTracker data in XML format"
    author = "VersionTracker Team"

    def initialize(self) -> None:
        """Initialize the XML export plugin."""
        logger.info("XML Export plugin initialized")

    def cleanup(self) -> None:
        """Cleanup XML export plugin resources."""
        logger.info("XML Export plugin cleaned up")

    def get_supported_formats(self) -> list[str]:
        """Get supported export formats."""
        return ["xml"]

    def export_data(
        self,
        data: list[dict[str, Any]],
        output_file: Path | None = None,
        format_options: dict[str, Any] | None = None,
    ) -> str:
        """Export data in XML format."""
        options = format_options or {}
        root_element = options.get("root_element", "versiontracker_data")
        item_element = options.get("item_element", "item")

        root = ET.Element(root_element)
        root.set("version", "1.0")
        root.set("timestamp", str(datetime.datetime.now().isoformat()))

        for item in data:
            item_elem = ET.SubElement(root, item_element)
            self._dict_to_xml(item, item_elem)

        # Pretty print XML
        self._indent(root)
        xml_string = ET.tostring(root, encoding="unicode")

        if output_file:
            output_file.write_text(xml_string, encoding="utf-8")
            logger.info("XML data exported to %s", output_file)

        return xml_string

    def _dict_to_xml(self, data: dict[str, Any], parent: ET.Element) -> None:
        """Convert dictionary to XML elements."""
        for key, value in data.items():
            # Sanitize key for XML element name
            clean_key = key.replace(" ", "_").replace("-", "_")
            if isinstance(value, dict):
                elem = ET.SubElement(parent, clean_key)
                self._dict_to_xml(value, elem)
            elif isinstance(value, list):
                for item in value:
                    elem = ET.SubElement(parent, clean_key)
                    if isinstance(item, dict):
                        self._dict_to_xml(item, elem)
                    else:
                        elem.text = str(item)
            else:
                elem = ET.SubElement(parent, clean_key)
                elem.text = str(value) if value is not None else ""

    def _indent(self, elem: ET.Element, level: int = 0) -> None:
        """Add indentation to XML for pretty printing."""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self._indent(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i


class YAMLExportPlugin(ExportPlugin):
    """Example plugin for exporting data in YAML format."""

    name = "yaml_export"
    version = "1.0.0"
    description = "Export VersionTracker data in YAML format"
    author = "VersionTracker Team"

    def initialize(self) -> None:
        """Initialize the YAML export plugin."""
        logger.info("YAML Export plugin initialized")

    def cleanup(self) -> None:
        """Cleanup YAML export plugin resources."""
        logger.info("YAML Export plugin cleaned up")

    def get_supported_formats(self) -> list[str]:
        """Get supported export formats."""
        return ["yaml", "yml"]

    def export_data(
        self,
        data: list[dict[str, Any]],
        output_file: Path | None = None,
        format_options: dict[str, Any] | None = None,
    ) -> str:
        """Export data in YAML format."""
        options = format_options or {}

        # Prepare metadata
        export_data = {
            "metadata": {
                "version": "1.0",
                "timestamp": str(datetime.datetime.now().isoformat()),
                "total_items": len(data),
                "export_plugin": self.name,
            },
            "data": data,
        }

        yaml_string = yaml.dump(
            export_data,
            default_flow_style=options.get("flow_style", False),
            indent=options.get("indent", 2),
            sort_keys=options.get("sort_keys", True),
        )

        if output_file:
            output_file.write_text(yaml_string, encoding="utf-8")
            logger.info("YAML data exported to %s", output_file)

        return str(yaml_string)


class AdvancedMatchingPlugin(MatchingPlugin):
    """Example plugin with advanced matching algorithms."""

    name = "advanced_matching"
    version = "1.0.0"
    description = "Advanced application matching with multiple algorithms"
    author = "VersionTracker Team"

    def initialize(self) -> None:
        """Initialize the advanced matching plugin."""
        self.algorithms = {
            "levenshtein": self._levenshtein_similarity,
            "jaro_winkler": self._jaro_winkler_similarity,
            "set_based": self._set_based_similarity,
            "phonetic": self._phonetic_similarity,
        }
        logger.info("Advanced Matching plugin initialized")

    def cleanup(self) -> None:
        """Cleanup advanced matching plugin resources."""
        logger.info("Advanced Matching plugin cleaned up")

    def match_applications(
        self, apps: list[dict[str, Any]], casks: list[dict[str, Any]], threshold: float = 0.8
    ) -> list[dict[str, Any]]:
        """Match applications using ensemble of algorithms."""
        matches = []

        for app in apps:
            app_name = app.get("name", "").lower()
            best_match = None
            best_score = 0.0

            for cask in casks:
                cask_name = cask.get("name", "").lower()
                score = self.calculate_similarity(app_name, cask_name)

                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = cask

            if best_match:
                matches.append(
                    {
                        "app": app,
                        "cask": best_match,
                        "similarity_score": best_score,
                        "matching_algorithm": "ensemble",
                    }
                )

        return matches

    def calculate_similarity(self, app_name: str, cask_name: str) -> float:
        """Calculate similarity using ensemble of algorithms."""
        scores = []

        for algorithm_name, algorithm_func in self.algorithms.items():
            try:
                score = algorithm_func(app_name, cask_name)
                scores.append(score)
            except Exception as e:
                logger.warning("Algorithm %s failed: %s", algorithm_name, e)

        # Return weighted average of scores
        if scores:
            return sum(scores) / len(scores)
        return 0.0

    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        """Calculate Levenshtein distance-based similarity."""
        if not s1 or not s2:
            return 0.0

        ratio = difflib.SequenceMatcher(None, s1, s2).ratio()
        return ratio

    def _jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Approximate Jaro-Winkler similarity (simplified implementation)."""
        if not s1 or not s2:
            return 0.0

        # Simplified version using difflib
        return difflib.SequenceMatcher(None, s1, s2).ratio()

    def _set_based_similarity(self, s1: str, s2: str) -> float:
        """Calculate set-based similarity using word sets."""
        if not s1 or not s2:
            return 0.0

        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _phonetic_similarity(self, s1: str, s2: str) -> float:
        """Simple phonetic similarity based on first letters and length."""
        if not s1 or not s2:
            return 0.0

        # Simple phonetic matching - starts with same letter
        first_letter_match = s1[0].lower() == s2[0].lower()
        length_similarity = 1.0 - abs(len(s1) - len(s2)) / max(len(s1), len(s2))

        return (0.3 if first_letter_match else 0.0) + (0.7 * length_similarity)


class SystemInfoCommand(CommandPlugin):
    """Example plugin that adds a system info command."""

    name = "system_info"
    version = "1.0.0"
    description = "Add system information command"
    author = "VersionTracker Team"

    def initialize(self) -> None:
        """Initialize the system info command plugin."""
        logger.info("System Info command plugin initialized")

    def cleanup(self) -> None:
        """Cleanup system info command plugin resources."""
        logger.info("System Info command plugin cleaned up")

    def get_commands(self) -> dict[str, Any]:
        """Get command definitions provided by this plugin."""
        return {
            "system-info": {
                "description": "Show system information",
                "handler": self.execute_command,
            }
        }

    def execute_command(self, command: str, options: Any) -> int:
        """Execute the system info command."""
        if command != "system-info":
            return 1

        try:
            import platform

            import psutil

            print("=== System Information ===")
            print(f"OS: {platform.system()} {platform.release()}")
            print(f"Architecture: {platform.machine()}")
            print(f"Python: {platform.python_version()}")
            print(f"CPU Cores: {psutil.cpu_count()}")
            print(f"Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")

            # Homebrew info
            try:
                import subprocess

                result = subprocess.run(["brew", "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    homebrew_version = result.stdout.strip().split("\n")[0]
                    print(f"Homebrew: {homebrew_version}")
                else:
                    print("Homebrew: Not installed or not in PATH")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print("Homebrew: Not available")

            print("========================")
            return 0

        except Exception as e:
            print(f"Error getting system information: {e}")
            return 1


class MacAppStoreDataSource(DataSourcePlugin):
    """Example data source plugin for Mac App Store applications."""

    name = "mac_app_store"
    version = "1.0.0"
    description = "Data source for Mac App Store applications"
    author = "VersionTracker Team"

    def initialize(self) -> None:
        """Initialize the Mac App Store data source."""
        logger.info("Mac App Store data source initialized")

    def cleanup(self) -> None:
        """Cleanup Mac App Store data source resources."""
        logger.info("Mac App Store data source cleaned up")

    def discover_applications(self, paths: list[Path] | None = None) -> list[dict[str, Any]]:
        """Discover Mac App Store applications."""
        mas_apps = []

        # Look for applications in Mac App Store directory
        mas_path = Path("/Applications")

        if mas_path.exists():
            for app_path in mas_path.glob("*.app"):
                if self._is_mas_app(app_path):
                    app_info = self._get_app_info(app_path)
                    if app_info:
                        mas_apps.append(app_info)

        logger.info("Discovered %s Mac App Store applications", len(mas_apps))
        return mas_apps

    def get_version_info(self, app_name: str) -> dict[str, Any] | None:
        """Get version information for a Mac App Store app."""
        # This would typically query the Mac App Store API
        # For this example, return mock data
        return {
            "name": app_name,
            "version": "Unknown",
            "source": "mac_app_store",
            "update_available": False,
        }

    def supports_platform(self, platform: str) -> bool:
        """Check if this data source supports the platform."""
        return platform.lower() == "darwin"

    def _is_mas_app(self, app_path: Path) -> bool:
        """Check if application is from Mac App Store."""
        # Check for App Store receipt
        receipt_path = app_path / "Contents" / "_MASReceipt" / "receipt"
        return receipt_path.exists()

    def _get_app_info(self, app_path: Path) -> dict[str, Any] | None:
        """Get application information."""
        try:
            import plistlib

            info_plist_path = app_path / "Contents" / "Info.plist"
            if not info_plist_path.exists():
                return None

            with open(info_plist_path, "rb") as f:
                plist_data = plistlib.load(f)

            return {
                "name": plist_data.get("CFBundleDisplayName") or plist_data.get("CFBundleName", app_path.stem),
                "version": plist_data.get("CFBundleShortVersionString", "Unknown"),
                "bundle_id": plist_data.get("CFBundleIdentifier", ""),
                "path": str(app_path),
                "source": "mac_app_store",
            }

        except Exception as e:
            logger.warning("Failed to parse app info for %s: %s", app_path, e)
            return None


class PluginStatsCommand(CommandPlugin):
    """Command plugin for displaying plugin statistics."""

    name = "plugin_stats"
    version = "1.0.0"
    description = "Display plugin system statistics"
    author = "VersionTracker Team"

    def initialize(self) -> None:
        """Initialize the plugin stats command."""
        logger.info("Plugin Stats command plugin initialized")

    def cleanup(self) -> None:
        """Cleanup plugin stats command resources."""
        logger.info("Plugin Stats command plugin cleaned up")

    def get_commands(self) -> dict[str, Any]:
        """Get command definitions provided by this plugin."""
        return {
            "plugin-stats": {
                "description": "Show plugin system statistics",
                "handler": self.execute_command,
            }
        }

    def execute_command(self, command: str, options: Any) -> int:
        """Execute the plugin stats command."""
        if command != "plugin-stats":
            return 1

        try:
            from versiontracker.plugins import plugin_manager

            print("=== Plugin System Statistics ===")

            all_plugins = plugin_manager.list_plugins()
            print(f"Total Plugins: {len(all_plugins)}")

            # Count by type
            command_plugins = len(plugin_manager._plugin_types.get("CommandPlugin", []))
            data_source_plugins = len(plugin_manager._plugin_types.get("DataSourcePlugin", []))
            matching_plugins = len(plugin_manager._plugin_types.get("MatchingPlugin", []))
            export_plugins = len(plugin_manager._plugin_types.get("ExportPlugin", []))

            print(f"Command Plugins: {command_plugins}")
            print(f"Data Source Plugins: {data_source_plugins}")
            print(f"Matching Plugins: {matching_plugins}")
            print(f"Export Plugins: {export_plugins}")

            print("\n=== Registered Plugins ===")
            for plugin_name in all_plugins:
                plugin_info = plugin_manager.get_plugin_info(plugin_name)
                if plugin_info:
                    status = "Enabled" if plugin_info["enabled"] else "Disabled"
                    print(f"- {plugin_name} v{plugin_info['version']} ({status})")
                    print(f"  Description: {plugin_info['description']}")
                    print(f"  Author: {plugin_info['author']}")
                    print()

            print("===============================")
            return 0

        except Exception as e:
            print(f"Error getting plugin statistics: {e}")
            return 1
