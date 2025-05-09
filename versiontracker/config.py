"""Configuration management for VersionTracker."""

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
                "Microsoft Defender", "Microsoft OneNote", "Microsoft PowerPoint",
                "Microsoft Excel", "Microsoft Word", "Microsoft Outlook",
                "Little Snitch", "VMware Fusion"
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
            "/usr/local/bin/brew",     # Intel default
            "/usr/local/Homebrew/bin/brew",  # Alternative Intel location
            "/homebrew/bin/brew",      # Custom installation
            "brew"                     # PATH-based installation
        ]
        
        # First try the architecture-appropriate path
        is_arm = platform.machine().startswith('arm')
        prioritized_paths = paths if is_arm else [paths[1]] + [p for p in paths if p != paths[1]]
        
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
        """Load configuration from YAML configuration file."""
        config_path = Path(self._config["config_file"])

        if not config_path.exists():
            logging.debug("Configuration file not found: %s", config_path)
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)

            if not yaml_config:
                logging.debug("Configuration file is empty")
                return

            logging.debug("Loaded configuration from %s", config_path)

            # Update configuration with values from file
            for key, value in yaml_config.items():
                # Convert config keys to lowercase and from kebab-case to snake_case
                config_key = key.lower().replace("-", "_")

                # Special handling for lists
                if config_key in ["additional_app_dirs", "blacklist"]:
                    if isinstance(value, list):
                        self._config[config_key] = value
                    else:
                        logging.warning("Invalid value for %s in config file: expected list", key)
                else:
                    self._config[config_key] = value

        except (yaml.YAMLError, IOError) as e:
            logging.warning("Error loading configuration from %s: %s", config_path, e)

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # API rate limit
        if os.environ.get("VERSIONTRACKER_API_RATE_LIMIT"):
            try:
                self._config["api_rate_limit"] = int(os.environ["VERSIONTRACKER_API_RATE_LIMIT"])
            except ValueError:
                logging.warning("Invalid API rate limit: %s", os.environ["VERSIONTRACKER_API_RATE_LIMIT"])

        # Debug mode
        if os.environ.get("VERSIONTRACKER_DEBUG", "").lower() in ("1", "true", "yes"):
            self._config["log_level"] = logging.DEBUG

        # Max workers
        if os.environ.get("VERSIONTRACKER_MAX_WORKERS"):
            try:
                self._config["max_workers"] = int(os.environ["VERSIONTRACKER_MAX_WORKERS"])
            except ValueError:
                logging.warning("Invalid max workers: %s", os.environ["VERSIONTRACKER_MAX_WORKERS"])

        # Similarity threshold
        if os.environ.get("VERSIONTRACKER_SIMILARITY_THRESHOLD"):
            try:
                self._config["similarity_threshold"] = int(
                    os.environ["VERSIONTRACKER_SIMILARITY_THRESHOLD"]
                )
            except ValueError:
                logging.warning(
                    "Invalid similarity threshold: %s",
                    os.environ["VERSIONTRACKER_SIMILARITY_THRESHOLD"]
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

        # UI options
        if os.environ.get("VERSIONTRACKER_UI_USE_COLOR", "").lower() in ("0", "false", "no"):
            self._config["ui"]["use_color"] = False
        if os.environ.get("VERSIONTRACKER_UI_MONITOR_RESOURCES", "").lower() in (
            "0",
            "false",
            "no",
        ):
            self._config["ui"]["monitor_resources"] = False
        if os.environ.get("VERSIONTRACKER_UI_ADAPTIVE_RATE_LIMITING", "").lower() in (
            "0",
            "false",
            "no",
        ):
            self._config["ui"]["adaptive_rate_limiting"] = False
        if os.environ.get("VERSIONTRACKER_UI_ENHANCED_PROGRESS", "").lower() in (
            "0",
            "false",
            "no",
        ):
            self._config["ui"]["enhanced_progress"] = False

        # Version comparison rate limit
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT"):
            try:
                self._config["version_comparison"]["rate_limit"] = int(
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT"]
                )
            except ValueError:
                logging.warning(
                    "Invalid version comparison rate limit: %s",
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT"]
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
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_CACHE_TTL"]
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
                    os.environ["VERSIONTRACKER_VERSION_COMPARISON_SIMILARITY_THRESHOLD"]
                )

        # Version comparison include beta versions
        if os.environ.get(
            "VERSIONTRACKER_VERSION_COMPARISON_INCLUDE_BETA_VERSIONS", ""
        ).lower() in ("1", "true", "yes"):
            self._config["version_comparison"]["include_beta_versions"] = True

        # Version comparison sort by outdated status
        if os.environ.get("VERSIONTRACKER_VERSION_COMPARISON_SORT_BY_OUTDATED", "").lower() in (
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
                    os.environ["VERSIONTRACKER_OUTDATED_DETECTION_MIN_VERSION_DIFF"]
                )

        # Outdated detection include pre-releases
        if os.environ.get("VERSIONTRACKER_OUTDATED_DETECTION_INCLUDE_PRE_RELEASES", "").lower() in (
            "1",
            "true",
            "yes",
        ):
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
                "use-color": self._config["ui"]["use_color"],
                "monitor-resources": self._config["ui"]["monitor_resources"],
                "adaptive-rate-limiting": self._config["ui"]["adaptive_rate_limiting"],
                "enhanced-progress": self._config["ui"]["enhanced_progress"],
            },
            "version-comparison": {
                "rate-limit": self._config["version_comparison"]["rate_limit"],
                "cache-ttl": self._config["version_comparison"]["cache_ttl"],
                "similarity-threshold": self._config["version_comparison"]["similarity_threshold"],
                "include-beta-versions": self._config["version_comparison"][
                    "include_beta_versions"
                ],
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
