"""Configuration management for VersionTracker.

This module handles configuration loading, validation and access for VersionTracker.
Configuration can be sourced from YAML files, environment variables, or defaults.
"""

import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import yaml

from versiontracker.exceptions import ConfigError
from versiontracker.utils import run_command

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration parameters against defined rules."""

    @staticmethod
    def validate_int_range(value: int, min_value: int, max_value: int) -> bool:
        """Validate an integer is within the specified range.

        Args:
            value: The integer value to validate
            min_value: The minimum allowed value (inclusive)
            max_value: The maximum allowed value (inclusive)

        Returns:
            bool: True if the value is valid, False otherwise
        """
        return min_value <= value <= max_value

    @staticmethod
    def validate_float_range(value: float, min_value: float, max_value: float) -> bool:
        """Validate a float is within the specified range.

        Args:
            value: The float value to validate
            min_value: The minimum allowed value (inclusive)
            max_value: The maximum allowed value (inclusive)

        Returns:
            bool: True if the value is valid, False otherwise
        """
        return min_value <= value <= max_value

    @staticmethod
    def validate_string_list(value: List[str]) -> bool:
        """Validate a list contains only strings.

        Args:
            value: The list to validate

        Returns:
            bool: True if the list contains only strings, False otherwise
        """
        return all(isinstance(item, str) for item in value)

    @staticmethod
    def validate_path_list(value: List[str]) -> bool:
        """Validate a list contains valid directory paths.

        Args:
            value: The list of directory paths to validate

        Returns:
            bool: True if all paths are valid directories, False otherwise
        """
        # Allow empty list
        if not value:
            return True

        # Check all items are strings and exist as directories
        if not ConfigValidator.validate_string_list(value):
            return False

        # Don't require directories to exist; just validate format
        return True

    @staticmethod
    def validate_positive_int(value: int) -> bool:
        """Validate an integer is positive.

        Args:
            value: The integer value to validate

        Returns:
            bool: True if the value is positive, False otherwise
        """
        return isinstance(value, int) and value > 0

    @staticmethod
    def validate_non_negative_int(value: int) -> bool:
        """Validate an integer is non-negative.

        Args:
            value: The integer value to validate

        Returns:
            bool: True if the value is non-negative, False otherwise
        """
        return isinstance(value, int) and value >= 0

    @staticmethod
    def validate_percentage(value: int) -> bool:
        """Validate a value is a valid percentage (0-100).

        Args:
            value: The value to validate

        Returns:
            bool: True if the value is a valid percentage, False otherwise
        """
        return isinstance(value, (int, float)) and 0 <= value <= 100

    @staticmethod
    def _get_validation_rules():
        """Get all validation rules organized by section."""
        return {
            "top_level": {
                "api_rate_limit": [
                    (lambda v: isinstance(v, (int, float)), "Must be a number"),
                    (
                        lambda v: ConfigValidator.validate_float_range(float(v), 0, 60),
                        "Must be between 0 and 60 seconds",
                    ),
                ],
                "max_workers": [
                    (lambda v: isinstance(v, int), "Must be an integer"),
                    (
                        lambda v: ConfigValidator.validate_int_range(v, 1, 100),
                        "Must be between 1 and 100",
                    ),
                ],
                "similarity_threshold": [
                    (lambda v: isinstance(v, (int, float)), "Must be a number"),
                    (
                        lambda v: ConfigValidator.validate_percentage(v),
                        "Must be between 0 and 100",
                    ),
                ],
                "additional_app_dirs": [
                    (lambda v: isinstance(v, list), "Must be a list"),
                    (
                        lambda v: ConfigValidator.validate_path_list(v),
                        "Must be a list of directory paths",
                    ),
                ],
                "blacklist": [
                    (lambda v: isinstance(v, list), "Must be a list"),
                    (
                        lambda v: ConfigValidator.validate_string_list(v),
                        "Must be a list of application names",
                    ),
                ],
                "log_level": [
                    (lambda v: isinstance(v, int), "Must be an integer"),
                    (
                        lambda v: v
                        in [
                            logging.DEBUG,
                            logging.INFO,
                            logging.WARNING,
                            logging.ERROR,
                            logging.CRITICAL,
                        ],
                        "Must be a valid logging level",
                    ),
                ],
                "show_progress": [(lambda v: isinstance(v, bool), "Must be a boolean")],
            },
            "ui": {
                "use_color": [(lambda v: isinstance(v, bool), "Must be a boolean")],
                "monitor_resources": [
                    (lambda v: isinstance(v, bool), "Must be a boolean")
                ],
                "adaptive_rate_limiting": [
                    (lambda v: isinstance(v, bool), "Must be a boolean")
                ],
                "enhanced_progress": [
                    (lambda v: isinstance(v, bool), "Must be a boolean")
                ],
            },
            "version_comparison": {
                "rate_limit": [
                    (lambda v: isinstance(v, (int, float)), "Must be a number"),
                    (
                        lambda v: ConfigValidator.validate_float_range(float(v), 0, 60),
                        "Must be between 0 and 60 seconds",
                    ),
                ],
                "cache_ttl": [
                    (lambda v: isinstance(v, (int, float)), "Must be a number"),
                    (lambda v: v > 0, "Must be greater than 0"),
                ],
                "similarity_threshold": [
                    (lambda v: isinstance(v, (int, float)), "Must be a number"),
                    (
                        lambda v: ConfigValidator.validate_percentage(v),
                        "Must be between 0 and 100",
                    ),
                ],
                "include_beta_versions": [
                    (lambda v: isinstance(v, bool), "Must be a boolean")
                ],
                "sort_by_outdated": [
                    (lambda v: isinstance(v, bool), "Must be a boolean")
                ],
            },
            "outdated_detection": {
                "enabled": [(lambda v: isinstance(v, bool), "Must be a boolean")],
                "min_version_diff": [
                    (lambda v: isinstance(v, (int, float)), "Must be a number"),
                    (lambda v: v >= 0, "Must be non-negative"),
                ],
                "include_pre_releases": [
                    (lambda v: isinstance(v, bool), "Must be a boolean")
                ],
            },
        }

    @staticmethod
    def _validate_rules_for_config(
        config: Dict[str, Any],
        rules: Dict[str, List],
        errors: Dict[str, List[str]],
        prefix: str = "",
    ) -> None:
        """Apply validation rules to a configuration section."""
        for key, rule_list in rules.items():
            if key in config:
                value = config[key]
                error_key = f"{prefix}.{key}" if prefix else key
                for rule, error_msg in rule_list:
                    if not rule(value):
                        errors.setdefault(error_key, []).append(error_msg)

    @staticmethod
    def _validate_nested_section(
        config: Dict[str, Any],
        section_name: str,
        rules: Dict[str, List],
        errors: Dict[str, List[str]],
    ) -> None:
        """Validate a nested configuration section."""
        if section_name in config:
            if not isinstance(config[section_name], dict):
                errors.setdefault(section_name, []).append("Must be a dictionary")
            else:
                ConfigValidator._validate_rules_for_config(
                    config[section_name], rules, errors, section_name
                )

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate configuration values against rules.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Dict[str, List[str]]: Dictionary of validation errors by parameter
        """
        errors: Dict[str, List[str]] = {}
        validation_rules = ConfigValidator._get_validation_rules()

        # Apply top-level validation rules
        ConfigValidator._validate_rules_for_config(
            config, validation_rules["top_level"], errors
        )

        # Validate nested sections
        for section_name in ["ui", "version_comparison", "outdated_detection"]:
            if section_name in validation_rules:
                ConfigValidator._validate_nested_section(
                    config, section_name, validation_rules[section_name], errors
                )

        return errors


class Config:
    """Configuration manager for VersionTracker."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize the configuration.

        Args:
            config_file: Optional path to a configuration file to use instead of the default
        """
        self._config: Dict[str, Any] = {
            # Default API rate limiting in seconds
            "api_rate_limit": 3,
            # Default log level
            "log_level": logging.INFO,
            # Default paths
            "log_dir": Path.home() / "Library" / "Logs" / "Versiontracker",
            # Config file path
            "config_file": (
                config_file
                if config_file
                else Path.home() / ".config" / "versiontracker" / "config.yaml"
            ),
            # Default commands
            "system_profiler_cmd": "/usr/sbin/system_profiler -json SPApplicationsDataType",
            # Set up Homebrew path based on architecture (Apple Silicon or Intel)
            "brew_path": self._detect_brew_path(),
            # Default max workers for parallel processing
            "max_workers": 10,
            # Default similarity threshold for app matching (%)
            "similarity_threshold": 75,
            # Additional directories to scan for applications
            "additional_app_dirs": [],
            # List of applications to blacklist (never include)
            "blacklist": [
                "Microsoft Defender",
                "Microsoft OneNote",
                "Microsoft PowerPoint",
                "Microsoft Excel",
                "Microsoft Word",
                "Microsoft Outlook",
                "Little Snitch",
                "VMware Fusion",
            ],
            # Whether to show progress bars
            "show_progress": True,
            # UI options
            "ui": {
                # Whether to use color in output
                "use_color": True,
                # Whether to monitor system resources
                "monitor_resources": True,
                # Whether to use adaptive rate limiting
                "adaptive_rate_limiting": True,
                # Whether to use enhanced progress bars
                "enhanced_progress": True,
            },
            # Version comparison options
            "version_comparison": {
                # Rate limit for Homebrew version checks (seconds)
                "rate_limit": 2,
                # Maximum age of cached version data (hours)
                "cache_ttl": 24,
                # Minimum similarity threshold for version matching (%)
                "similarity_threshold": 75,
                # Whether to include beta/development versions
                "include_beta_versions": False,
                # Sort results by outdated status
                "sort_by_outdated": True,
            },
            # Outdated detection options
            "outdated_detection": {
                # Whether to detect outdated applications
                "enabled": True,
                # Minimum version difference to consider an application outdated
                "min_version_diff": 1,
                # Whether to include pre-release versions in outdated detection
                "include_pre_releases": False,
            },
        }

        # Load configuration values
        self._load_from_file()
        self._load_from_env()

    def _detect_brew_path(self) -> str:
        """Detect the Homebrew path based on the system architecture.

        Returns:
            str: The path to the brew executable
        """
        # Define all possible Homebrew paths
        paths = [
            "/opt/homebrew/bin/brew",  # Apple Silicon default
            "/usr/local/bin/brew",  # Intel default
            "/usr/local/Homebrew/bin/brew",  # Alternative Intel location
            "/homebrew/bin/brew",  # Custom installation
            "brew",  # PATH-based installation
        ]

        # First try the architecture-appropriate path
        is_arm = platform.machine().startswith("arm")
        prioritized_paths = (
            paths if is_arm else [paths[1]] + [p for p in paths if p != paths[1]]
        )

        for path in prioritized_paths:
            try:
                cmd = f"{path} --version"
                _, returncode = run_command(cmd, timeout=2)
                if returncode == 0:
                    logging.debug("Found working Homebrew at: %s", path)
                    return path
            except (FileNotFoundError, PermissionError, TimeoutError) as e:
                logging.debug("Failed to check Homebrew at %s: %s", path, e)
                continue

        # Fallback to Intel path if nothing else works
        logging.warning("No working Homebrew found, falling back to default Intel path")
        return "/usr/local/bin/brew"

    def _load_from_file(self) -> None:
        """Load configuration from YAML configuration file.

        Validates configuration values according to rules and updates the
        current configuration with values from the file.

        Raises:
            ConfigError: If configuration validation fails
            IOError: If file operations fail
        """
        config_path = Path(self._config["config_file"])

        if not config_path.exists():
            logging.debug("Configuration file not found: %s", config_path)
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)

            if not yaml_config:
                logging.debug("Empty configuration file: %s", config_path)
                return

            logging.debug("Loaded configuration from %s", config_path)

            # Parse and normalize configuration
            normalized_config = self._normalize_config_keys(yaml_config)

            # Validate configuration values
            validation_errors = ConfigValidator.validate_config(normalized_config)
            if validation_errors:
                error_msg = "Configuration validation failed:"
                for param, errors in validation_errors.items():
                    for error in errors:
                        error_msg += f"\n  - {param}: {error}"
                logging.error(error_msg)
                raise ConfigError(error_msg)

            # Update configuration with validated values
            self._config.update(normalized_config)
            logging.debug(f"Successfully updated configuration from {config_path}")

        except yaml.YAMLError as e:
            logging.error(
                f"YAML parsing error in configuration file {config_path}: {e}"
            )
            raise ConfigError(f"Invalid YAML in configuration file: {str(e)}")
        except IOError as e:
            logging.error(f"Error reading configuration file {config_path}: {e}")
            raise ConfigError(f"Error loading configuration: {str(e)}")
        except Exception as e:
            logging.error(
                f"Unexpected error loading configuration from {config_path}: {e}"
            )
            raise ConfigError(f"Error in configuration processing: {str(e)}")

    def _normalize_config_keys(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize configuration keys from kebab-case to snake_case recursively.

        Args:
            config: Raw configuration dictionary

        Returns:
            Dict[str, Any]: Normalized configuration dictionary
        """
        if not isinstance(config, dict):
            return config  # type: ignore

        normalized = {}
        for key, value in config.items():
            normalized_key = key.lower().replace("-", "_")

            # Recursively normalize nested dictionaries
            if isinstance(value, dict):
                normalized[normalized_key] = self._normalize_config_keys(value)
            elif isinstance(value, list):
                # Normalize dictionaries in lists
                normalized_value = []
                for item in value:
                    if isinstance(item, dict):
                        normalized_value.append(self._normalize_config_keys(item))
                    else:
                        normalized_value.append(item)
                normalized[normalized_key] = normalized_value  # type: ignore
            else:
                normalized[normalized_key] = value

        return normalized

    def _load_integer_env_var(
        self, env_var: str, config_key: str, env_config: dict
    ) -> None:
        """Load and validate an integer environment variable."""
        if os.environ.get(env_var):
            try:
                env_config[config_key] = int(os.environ[env_var])
            except ValueError:
                logging.warning("Invalid %s: %s", config_key, os.environ[env_var])

    def _load_boolean_env_var(
        self,
        env_var: str,
        config_key: str,
        env_config: dict,
        nested_key: Optional[str] = None,
    ) -> None:
        """Load and validate a boolean environment variable."""
        if os.environ.get(env_var, "").lower() in ("0", "false", "no"):
            if nested_key:
                if nested_key not in env_config:
                    env_config[nested_key] = {}
                env_config[nested_key][config_key] = False
            else:
                env_config[config_key] = False

    def _load_basic_env_vars(self, env_config: dict) -> None:
        """Load basic environment variables."""
        # Debug mode
        if os.environ.get("VERSIONTRACKER_DEBUG", "").lower() in ("1", "true", "yes"):
            self._config["log_level"] = logging.DEBUG

        # Integer configurations
        self._load_integer_env_var(
            "VERSIONTRACKER_API_RATE_LIMIT", "api_rate_limit", env_config
        )
        self._load_integer_env_var(
            "VERSIONTRACKER_MAX_WORKERS", "max_workers", env_config
        )
        self._load_integer_env_var(
            "VERSIONTRACKER_SIMILARITY_THRESHOLD", "similarity_threshold", env_config
        )

        # Additional app directories
        if os.environ.get("VERSIONTRACKER_ADDITIONAL_APP_DIRS"):
            dirs = os.environ["VERSIONTRACKER_ADDITIONAL_APP_DIRS"].split(":")
            env_config["additional_app_dirs"] = [d for d in dirs if os.path.isdir(d)]

        # Blacklist
        if os.environ.get("VERSIONTRACKER_BLACKLIST"):
            env_config["blacklist"] = os.environ["VERSIONTRACKER_BLACKLIST"].split(",")

    def _load_ui_env_vars(self, env_config: dict) -> None:
        """Load UI-related environment variables."""
        # Progress bars
        self._load_boolean_env_var(
            "VERSIONTRACKER_PROGRESS_BARS", "show_progress", env_config
        )

        # UI options
        ui_vars = [
            ("VERSIONTRACKER_UI_USE_COLOR", "use_color"),
            ("VERSIONTRACKER_UI_MONITOR_RESOURCES", "monitor_resources"),
            ("VERSIONTRACKER_UI_ADAPTIVE_RATE_LIMITING", "adaptive_rate_limiting"),
            ("VERSIONTRACKER_UI_ENHANCED_PROGRESS", "enhanced_progress"),
        ]

        for env_var, config_key in ui_vars:
            self._load_boolean_env_var(env_var, config_key, env_config, "ui")

    def _validate_and_apply_env_config(self, env_config: dict) -> None:
        """Validate and apply environment configuration."""
        if not env_config:
            return

        validation_errors = ConfigValidator.validate_config(env_config)
        if validation_errors:
            self._handle_validation_errors(validation_errors, env_config)
        else:
            logging.debug(
                f"Applying all environment variables: {list(env_config.keys())}"
            )
            self._config.update(env_config)

    def _handle_validation_errors(
        self, validation_errors: dict, env_config: dict
    ) -> None:
        """Handle validation errors for environment configuration."""
        error_msg = "Environment configuration validation failed:"
        for param, errors in validation_errors.items():
            for error in errors:
                error_msg += f"\n  - {param}: {error}"
        logging.warning(error_msg)

        # Filter out invalid configuration values
        valid_env_config = {}
        for key, value in env_config.items():
            if key not in validation_errors:
                valid_env_config[key] = value
            else:
                logging.warning(
                    f"Ignoring invalid environment configuration for '{key}'"
                )

        # Update configuration with valid values only
        if valid_env_config:
            logging.debug(
                f"Applying valid environment variables: {list(valid_env_config.keys())}"
            )
            self._config.update(valid_env_config)

    def _load_version_comparison_env_vars(self) -> None:
        """Load version comparison specific environment variables."""
        # Version comparison rate limit
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT"):
            try:
                self._config["version_comparison"]["rate_limit"] = int(
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT"]
                )
            except ValueError:
                logging.warning(
                    "Invalid version comparison rate limit: %s",
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT"],
                )

        # Version comparison cache TTL
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_CACHE_TTL"):
            try:
                self._config["version_comparison"]["cache_ttl"] = int(
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_CACHE_TTL"]
                )
            except ValueError:
                logging.warning(
                    "Invalid version comparison cache TTL: %s",
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_CACHE_TTL"],
                )

        # Version comparison similarity threshold
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_SIMILARITY_THRESHOLD"):
            try:
                self._config["version_comparison"]["similarity_threshold"] = int(
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_SIMILARITY_THRESHOLD"]
                )
            except ValueError:
                logging.warning(
                    "Invalid version comparison similarity threshold: %s",
                    os.environ[
                        "VERSIONTRACKER_VERSION_COMPARISON_SIMILARITY_THRESHOLD"
                    ],
                )

        # Version comparison include beta versions
        if os.environ.get(
            "VERSIONTRACKER_VERSION_COMPARISON_INCLUDE_BETA_VERSIONS", ""
        ).lower() in ("1", "true", "yes"):
            self._config["version_comparison"]["include_beta_versions"] = True

        # Version comparison sort by outdated status
        if os.environ.get(
            "VERSIONTRACKER_VERSION_COMPARISON_SORT_BY_OUTDATED", ""
        ).lower() in (
            "1",
            "true",
            "yes",
        ):
            self._config["version_comparison"]["sort_by_outdated"] = True

        # Outdated detection enabled
        if os.environ.get("VERSIONTRACKER_OUTDATED_DETECTION_ENABLED", "").lower() in (
            "1",
            "true",
            "yes",
        ):
            self._config["outdated_detection"]["enabled"] = True

        # Outdated detection minimum version difference
        if os.environ.get("VERSIONTRACKER_OUTDATED_DETECTION_MIN_VERSION_DIFF"):
            try:
                self._config["outdated_detection"]["min_version_diff"] = int(
                    os.environ["VERSIONTRACKER_OUTDATED_DETECTION_MIN_VERSION_DIFF"]
                )
            except ValueError:
                logging.warning(
                    "Invalid outdated detection minimum version difference: %s",
                    os.environ["VERSIONTRACKER_OUTDATED_DETECTION_MIN_VERSION_DIFF"],
                )

        # Outdated detection include pre-releases
        if os.environ.get(
            "VERSIONTRACKER_OUTDATED_DETECTION_INCLUDE_PRE_RELEASES", ""
        ).lower() in (
            "1",
            "true",
            "yes",
        ):
            self._config["outdated_detection"]["include_pre_releases"] = True

    def _load_from_env(self) -> None:
        """Load configuration from environment variables.

        Validates and applies configuration values from environment variables.
        Environment variables take precedence over file configuration.

        Environment variables are in the format VERSIONTRACKER_UPPER_SNAKE_CASE,
        which maps to the configuration keys in lower_snake_case.
        """
        env_config: Dict[str, Any] = {}

        # Load different categories of environment variables
        self._load_basic_env_vars(env_config)
        self._load_ui_env_vars(env_config)

        # Validate and apply standard environment configuration
        self._validate_and_apply_env_config(env_config)

        # Load version comparison specific variables (these update config directly)
        self._load_version_comparison_env_vars()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Retrieves a configuration value by key, optionally returning a default
        value if the key doesn't exist. Supports nested configuration access
        with dot notation.

        Args:
            key: The configuration key, can use dot notation for nested access
            default: Optional default value to return if key doesn't exist

        Returns:
            Any: Configuration value

        Raises:
            KeyError: If the key does not exist and no default is provided
        """
        # Handle nested keys with dot notation
        if "." in key:
            parts = key.split(".")
            current = self._config
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    if default is not None:
                        return default
                    raise KeyError(
                        f"Configuration key '{key}' not found and no default provided"
                    )
            return current

        # Direct key access
        if key in self._config:
            return self._config[key]
        elif key == "log_level":
            # Return DEBUG if set in config or by environment variable, otherwise INFO
            if "log_level" in self._config:
                return self._config["log_level"]
            if os.environ.get("VERSIONTRACKER_DEBUG", "").lower() in (
                "1",
                "true",
                "yes",
            ):
                return logging.DEBUG
            return logging.INFO
        else:
            return default

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Sets a configuration value, optionally creating nested dictionaries
        if the key uses dot notation. Validates the value before setting it.

        Args:
            key: The configuration key to set, supports dot notation
            value: The value to set

        Raises:
            ConfigError: If validation fails for the key/value
        """
        # Prepare a config fragment for validation
        config_fragment: Dict[str, Any] = {}

        # Handle nested keys with dot notation
        if "." in key:
            parts = key.split(".")

            # Create nested structure for validation
            current = config_fragment
            for i, part in enumerate(parts[:-1]):
                current[part] = {}
                current = current[part]
            current[parts[-1]] = value

            # Validate the fragment
            validation_errors = ConfigValidator.validate_config(config_fragment)
            if validation_errors:
                error_msg = f"Configuration validation failed for '{key}':"
                for param, errors in validation_errors.items():
                    for error in errors:
                        error_msg += f"\n  - {param}: {error}"
                raise ConfigError(error_msg)

            # Apply the value - only reached if validation passes
            current = self._config  # type: ignore
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            # Simple key - validate and set
            config_fragment[key] = value
            validation_errors = ConfigValidator.validate_config(config_fragment)
            if validation_errors:
                error_msg = f"Invalid configuration value for '{key}':"
                for param, errors in validation_errors.items():
                    for error in errors:
                        error_msg += f"\n  - {param}: {error}"
                raise ConfigError(error_msg)

            # Set the value
            self._config[key] = value

    def get_blacklist(self) -> List[str]:
        """Get the blacklisted applications.

        Returns:
            List[str]: List of blacklisted application names
        """
        blacklist = cast(List[str], self._config.get("blacklist", []))
        return blacklist

    def is_blacklisted(self, app_name: str) -> bool:
        """Check if an application is blacklisted.

        Args:
            app_name (str): The application name

        Returns:
            bool: True if the application is blacklisted, False otherwise
        """
        blacklist = self.get_blacklist()
        return any(app_name.lower() == item.lower() for item in blacklist)

    @property
    def log_dir(self) -> Path:
        """Get the log directory path.

        Returns:
            Path: Path to the log directory
        """
        return Path(self._config["log_dir"])

    @property
    def debug(self) -> bool:
        """Get the debug flag.

        Returns:
            bool: Whether debug mode is enabled
        """
        return bool(self._config.get("debug", False))

    @debug.setter
    def debug(self, value: bool) -> None:
        """Set the debug flag.

        Args:
            value: Whether to enable debug mode
        """
        self._config["debug"] = value

    @property
    def no_progress(self) -> bool:
        """Get the no_progress flag.

        Returns:
            bool: Whether progress bars are disabled
        """
        return bool(self._config.get("no_progress", False))

    @property
    def show_progress(self) -> bool:
        """Get the show_progress flag.

        Returns:
            bool: Whether progress bars are enabled
        """
        return not self.no_progress

    def generate_default_config(self, path: Optional[Path] = None) -> str:
        """Generate a default configuration file.

        Args:
            path (Path, optional): The path to write the configuration file.
                                  If not provided, will use the default path.

        Returns:
            str: The path to the generated configuration file
        """
        config_path = path or Path(self._config["config_file"])

        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a dictionary with the current configuration
        config_dict = {
            "api-rate-limit": self._config["api_rate_limit"],
            "max-workers": self._config["max_workers"],
            "similarity-threshold": self._config["similarity_threshold"],
            "additional-app-dirs": self._config["additional_app_dirs"],
            "blacklist": self._config["blacklist"],
            "show-progress": self._config["show_progress"],
            "ui": {
                "use-color": self._config["ui"].get("use_color", True),
                "monitor-resources": self._config["ui"].get("monitor_resources", True),
                "adaptive-rate-limiting": self._config["ui"].get(
                    "adaptive_rate_limiting", True
                ),
                "enhanced-progress": self._config["ui"].get("enhanced_progress", True),
            },
            "version-comparison": {
                "rate-limit": self._config["version_comparison"]["rate_limit"],
                "cache-ttl": self._config["version_comparison"]["cache_ttl"],
                "similarity-threshold": self._config["version_comparison"][
                    "similarity_threshold"
                ],
                "include-beta-versions": self._config["version_comparison"][
                    "include_beta_versions"
                ],
                "sort-by-outdated": self._config["version_comparison"][
                    "sort_by_outdated"
                ],
            },
            "outdated-detection": {
                "enabled": self._config["outdated_detection"]["enabled"],
                "min-version-diff": self._config["outdated_detection"][
                    "min_version_diff"
                ],
                "include-pre-releases": self._config["outdated_detection"][
                    "include_pre_releases"
                ],
            },
        }

        # Write the configuration to a file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False)

        logging.info("Generated configuration file: %s", config_path)
        return str(config_path)


def check_dependencies() -> bool:
    """Check if all required dependencies are available.

    Returns:
        bool: True if all dependencies are present, False otherwise

    Raises:
        ConfigError: If critical dependencies are missing
    """
    missing_deps = []

    # Check for system_profiler on macOS
    if platform.system() == "Darwin":
        if not shutil.which("system_profiler"):
            missing_deps.append("system_profiler")

    # Check if any critical dependencies are missing
    if missing_deps:
        error_msg = f"Missing required dependencies: {', '.join(missing_deps)}"
        logging.error(error_msg)
        raise ConfigError(error_msg)

    return True


# Global configuration instance - we create a default instance that can be
# replaced by any module that needs a custom configuration
_config_instance = Config()


def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
        Config: The global configuration instance
    """
    return _config_instance


def setup_logging(debug: bool = False):
    """Set up logging for the application.

    Args:
        debug: Whether to enable debug logging
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Ensure log directory exists
    log_dir = get_config().log_dir
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "versiontracker.log"),
            logging.StreamHandler(),
        ],
    )


def set_global_config(new_config: Config):
    """Replace the global config instance with a custom one.

    Args:
        new_config: The new config instance to use globally
    """
    global _config_instance
    _config_instance = new_config
