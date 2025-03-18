"""Configuration management for VersionTracker."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


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
            "config_file": config_file if config_file else Path.home() / ".config" / "versiontracker" / "config.yaml",
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
            "blacklist": [],
            # Whether to show progress bars
            "show_progress": True,
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
        apple_silicon_path = "/opt/homebrew/bin/brew"
        intel_path = "/usr/local/bin/brew"

        if Path(apple_silicon_path).exists():
            return apple_silicon_path
        return intel_path

    def _load_from_file(self) -> None:
        """Load configuration from YAML configuration file."""
        config_path = Path(self._config["config_file"])
        
        if not config_path.exists():
            logging.debug(f"Configuration file not found: {config_path}")
            return
            
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
                
            if not yaml_config:
                logging.debug("Configuration file is empty")
                return
                
            logging.debug(f"Loaded configuration from {config_path}")
            
            # Update configuration with values from file
            for key, value in yaml_config.items():
                # Convert config keys to lowercase and from kebab-case to snake_case
                config_key = key.lower().replace("-", "_")
                
                # Special handling for lists
                if config_key in ["additional_app_dirs", "blacklist"]:
                    if isinstance(value, list):
                        self._config[config_key] = value
                    else:
                        logging.warning(f"Invalid value for {key} in config file: expected list")
                else:
                    self._config[config_key] = value
                
        except Exception as e:
            logging.warning(f"Error loading configuration from {config_path}: {e}")

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # API rate limit
        if os.environ.get("VERSIONTRACKER_API_RATE_LIMIT"):
            try:
                self._config["api_rate_limit"] = int(os.environ["VERSIONTRACKER_API_RATE_LIMIT"])
            except ValueError:
                logging.warning(
                    f"Invalid API rate limit: {os.environ['VERSIONTRACKER_API_RATE_LIMIT']}"
                )

        # Debug mode
        if os.environ.get("VERSIONTRACKER_DEBUG", "").lower() in ("1", "true", "yes"):
            self._config["log_level"] = logging.DEBUG

        # Max workers
        if os.environ.get("VERSIONTRACKER_MAX_WORKERS"):
            try:
                self._config["max_workers"] = int(os.environ["VERSIONTRACKER_MAX_WORKERS"])
            except ValueError:
                logging.warning(f"Invalid max workers: {os.environ['VERSIONTRACKER_MAX_WORKERS']}")

        # Similarity threshold
        if os.environ.get("VERSIONTRACKER_SIMILARITY_THRESHOLD"):
            try:
                self._config["similarity_threshold"] = int(
                    os.environ["VERSIONTRACKER_SIMILARITY_THRESHOLD"]
                )
            except ValueError:
                logging.warning(
                    f"Invalid similarity threshold: {os.environ['VERSIONTRACKER_SIMILARITY_THRESHOLD']}"
                )

        # Additional app directories
        if os.environ.get("VERSIONTRACKER_ADDITIONAL_APP_DIRS"):
            dirs = os.environ["VERSIONTRACKER_ADDITIONAL_APP_DIRS"].split(":")
            self._config["additional_app_dirs"] = [d for d in dirs if os.path.isdir(d)]

        # Blacklist
        if os.environ.get("VERSIONTRACKER_BLACKLIST"):
            self._config["blacklist"] = os.environ["VERSIONTRACKER_BLACKLIST"].split(",")

        # Progress bars
        if os.environ.get("VERSIONTRACKER_PROGRESS_BARS", "").lower() in ("0", "false", "no"):
            self._config["show_progress"] = False

        # Version comparison rate limit
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT"):
            try:
                self._config["version_comparison"]["rate_limit"] = int(
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT"]
                )
            except ValueError:
                logging.warning(
                    f"Invalid version comparison rate limit: {os.environ['VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT']}"
                )

        # Version comparison cache TTL
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_CACHE_TTL"):
            try:
                self._config["version_comparison"]["cache_ttl"] = int(
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_CACHE_TTL"]
                )
            except ValueError:
                logging.warning(
                    f"Invalid version comparison cache TTL: {os.environ['VERSIONTRACKER_VERSION_COMPARISON_CACHE_TTL']}"
                )

        # Version comparison similarity threshold
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_SIMILARITY_THRESHOLD"):
            try:
                self._config["version_comparison"]["similarity_threshold"] = int(
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_SIMILARITY_THRESHOLD"]
                )
            except ValueError:
                logging.warning(
                    f"Invalid version comparison similarity threshold: {os.environ['VERSIONTRACKER_VERSION_COMPARISON_SIMILARITY_THRESHOLD']}"
                )

        # Version comparison include beta versions
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_INCLUDE_BETA_VERSIONS", "").lower() in ("1", "true", "yes"):
            self._config["version_comparison"]["include_beta_versions"] = True

        # Version comparison sort by outdated status
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_SORT_BY_OUTDATED", "").lower() in ("1", "true", "yes"):
            self._config["version_comparison"]["sort_by_outdated"] = True

        # Outdated detection enabled
        if os.environ.get("VERSIONTRACKER_OUTDATED_DETECTION_ENABLED", "").lower() in ("1", "true", "yes"):
            self._config["outdated_detection"]["enabled"] = True

        # Outdated detection minimum version difference
        if os.environ.get("VERSIONTRACKER_OUTDATED_DETECTION_MIN_VERSION_DIFF"):
            try:
                self._config["outdated_detection"]["min_version_diff"] = int(
                    os.environ["VERSIONTRACKER_OUTDATED_DETECTION_MIN_VERSION_DIFF"]
                )
            except ValueError:
                logging.warning(
                    f"Invalid outdated detection minimum version difference: {os.environ['VERSIONTRACKER_OUTDATED_DETECTION_MIN_VERSION_DIFF']}"
                )

        # Outdated detection include pre-releases
        if os.environ.get("VERSIONTRACKER_OUTDATED_DETECTION_INCLUDE_PRE_RELEASES", "").lower() in ("1", "true", "yes"):
            self._config["outdated_detection"]["include_pre_releases"] = True

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get a configuration value.

        Args:
            key (str): The configuration key
            default (Any, optional): The default value if key doesn't exist

        Returns:
            Any: The configuration value
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key (str): The configuration key
            value (Any): The configuration value
        """
        self._config[key] = value

    def get_blacklist(self) -> List[str]:
        """Get the blacklisted applications.

        Returns:
            List[str]: List of blacklisted application names
        """
        return self._config.get("blacklist", [])

    def is_blacklisted(self, app_name: str) -> bool:
        """Check if an application is blacklisted.

        Args:
            app_name (str): The application name

        Returns:
            bool: True if the application is blacklisted, False otherwise
        """
        blacklist = self.get_blacklist()
        return any(app_name.lower() == item.lower() for item in blacklist)
        
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
            "version-comparison": {
                "rate-limit": self._config["version_comparison"]["rate_limit"],
                "cache-ttl": self._config["version_comparison"]["cache_ttl"],
                "similarity-threshold": self._config["version_comparison"]["similarity_threshold"],
                "include-beta-versions": self._config["version_comparison"]["include_beta_versions"],
                "sort-by-outdated": self._config["version_comparison"]["sort_by_outdated"],
            },
            "outdated-detection": {
                "enabled": self._config["outdated_detection"]["enabled"],
                "min-version-diff": self._config["outdated_detection"]["min_version_diff"],
                "include-pre-releases": self._config["outdated_detection"]["include_pre_releases"],
            },
        }
        
        # Write the configuration to a file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False)
            
        logging.info(f"Generated configuration file: {config_path}")
        return str(config_path)


# Global configuration instance - we create a default instance that can be 
# replaced by any module that needs a custom configuration
config = Config()

# Function to update the global config instance with a custom one
def set_global_config(new_config: Config) -> None:
    """Replace the global config instance with a custom one.
    
    Args:
        new_config: The new config instance to use globally
    """
    global config
    config = new_config
