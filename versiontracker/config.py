"""Configuration management for VersionTracker."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


class Config:
    """Configuration manager for VersionTracker."""
    
    def __init__(self):
        """Initialize the configuration."""
        self._config: Dict[str, Any] = {
            # Default API rate limiting in seconds
            'api_rate_limit': 3,
            
            # Default log level
            'log_level': logging.INFO,
            
            # Default paths
            'log_dir': Path.home() / "Library" / "Logs" / "Versiontracker",
            
            # Default commands
            'system_profiler_cmd': '/usr/sbin/system_profiler -json SPApplicationsDataType',
            
            # Set up Homebrew path based on architecture (Apple Silicon or Intel)
            'brew_path': self._detect_brew_path(),
            
            # Default max workers for parallel processing
            'max_workers': 10,
            
            # Default similarity threshold for app matching (%)
            'similarity_threshold': 75,
            
            # Additional application directories to scan
            'additional_app_dirs': [],
            
            # Blacklisted applications (won't be included in results)
            'blacklist': [],
            
            # Show progress bars
            'show_progress': True,
        }
        
        # Load configuration from environment variables
        self._load_from_env()
        
    def _detect_brew_path(self) -> str:
        """Detect the Homebrew path based on the system architecture.
        
        Returns:
            str: The path to the brew executable
        """
        apple_silicon_path = '/opt/homebrew/bin/brew'
        intel_path = '/usr/local/bin/brew'
        
        if Path(apple_silicon_path).exists():
            return apple_silicon_path
        return intel_path
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # API rate limit
        if os.environ.get('VERSIONTRACKER_API_RATE_LIMIT'):
            try:
                self._config['api_rate_limit'] = int(os.environ['VERSIONTRACKER_API_RATE_LIMIT'])
            except ValueError:
                logging.warning(f"Invalid API rate limit: {os.environ['VERSIONTRACKER_API_RATE_LIMIT']}")
        
        # Debug mode
        if os.environ.get('VERSIONTRACKER_DEBUG', '').lower() in ('1', 'true', 'yes'):
            self._config['log_level'] = logging.DEBUG
        
        # Max workers
        if os.environ.get('VERSIONTRACKER_MAX_WORKERS'):
            try:
                self._config['max_workers'] = int(os.environ['VERSIONTRACKER_MAX_WORKERS'])
            except ValueError:
                logging.warning(f"Invalid max workers: {os.environ['VERSIONTRACKER_MAX_WORKERS']}")
        
        # Similarity threshold
        if os.environ.get('VERSIONTRACKER_SIMILARITY_THRESHOLD'):
            try:
                self._config['similarity_threshold'] = int(os.environ['VERSIONTRACKER_SIMILARITY_THRESHOLD'])
            except ValueError:
                logging.warning(f"Invalid similarity threshold: {os.environ['VERSIONTRACKER_SIMILARITY_THRESHOLD']}")
        
        # Additional app directories
        if os.environ.get('VERSIONTRACKER_ADDITIONAL_APP_DIRS'):
            dirs = os.environ['VERSIONTRACKER_ADDITIONAL_APP_DIRS'].split(':')
            self._config['additional_app_dirs'] = [d for d in dirs if os.path.isdir(d)]
        
        # Blacklist
        if os.environ.get('VERSIONTRACKER_BLACKLIST'):
            self._config['blacklist'] = os.environ['VERSIONTRACKER_BLACKLIST'].split(',')
        
        # Progress bars
        if os.environ.get('VERSIONTRACKER_PROGRESS_BARS', '').lower() in ('0', 'false', 'no'):
            self._config['show_progress'] = False
    
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
        return self._config.get('blacklist', [])
    
    def is_blacklisted(self, app_name: str) -> bool:
        """Check if an application is blacklisted.
        
        Args:
            app_name (str): The application name
            
        Returns:
            bool: True if the application is blacklisted, False otherwise
        """
        blacklist = self.get_blacklist()
        return any(app_name.lower() == item.lower() for item in blacklist)


# Global configuration instance
config = Config()
