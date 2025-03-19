"""User interface utilities for VersionTracker."""

import os
import shutil
import sys
import time
import psutil
from functools import wraps
from typing import Any, List, Dict, Optional, Union, Callable, Iterator, TypeVar, Generic, cast, Iterable, Type

# Initialize progress bar handling
HAS_TQDM = False
TQDM_CLASS: Any = None  # Will hold the tqdm class

try:
    from tqdm import tqdm
    HAS_TQDM = True
    TQDM_CLASS = tqdm
except ImportError:
    # If tqdm is not available, create a simple fallback
    HAS_TQDM = False
    
    # Define a simple fallback class for tqdm
    class FallbackTqdm:
        def __init__(self, iterable=None, **kwargs):
            self.iterable = iterable
                
        def __iter__(self):
            if self.iterable is None:
                return iter([])
            return iter(self.iterable)
                
        def set_postfix_str(self, s):
            # No-op for fallback
            pass
    
    TQDM_CLASS = FallbackTqdm

try:
    from termcolor import colored, cprint
    HAS_TERMCOLOR = True
except ImportError:
    HAS_TERMCOLOR = False
    # Fallback implementation if termcolor is not available
    def colored(text, color=None, on_color=None, attrs=None):
        """Fallback implementation of colored."""
        return text
    
    def cprint(text, color=None, on_color=None, attrs=None, **kwargs):
        """Fallback implementation of cprint."""
        print(text, **kwargs)

# Constants for terminal output
SUCCESS = 'green'
INFO = 'blue'
WARNING = 'yellow'
ERROR = 'red'
DEBUG = 'cyan'

# Type variables for generics
T = TypeVar('T')
R = TypeVar('R')

# Terminal size detection
def get_terminal_size():
    """Get the terminal size."""
    columns, lines = shutil.get_terminal_size()
    return columns, lines

# Enhanced colored output
def print_success(message: str, **kwargs):
    """Print a success message in green."""
    if HAS_TERMCOLOR:
        cprint(message, SUCCESS, **kwargs)
    else:
        print(message, **kwargs)

def print_info(message: str, **kwargs):
    """Print an info message in blue."""
    if HAS_TERMCOLOR:
        cprint(message, INFO, **kwargs)
    else:
        print(message, **kwargs)

def print_warning(message: str, **kwargs):
    """Print a warning message in yellow."""
    if HAS_TERMCOLOR:
        cprint(message, WARNING, **kwargs)
    else:
        print(message, **kwargs)

def print_error(message: str, **kwargs):
    """Print an error message in red."""
    if HAS_TERMCOLOR:
        cprint(message, ERROR, **kwargs)
    else:
        print(message, **kwargs)

def print_debug(message: str, **kwargs):
    """Print a debug message in cyan."""
    if HAS_TERMCOLOR:
        cprint(message, DEBUG, **kwargs)
    else:
        print(message, **kwargs)

# Smart progress indicators
class SmartProgress(Generic[T]):
    """Enhanced progress indicator with system resource monitoring."""
    
    def __init__(
        self, 
        iterable: Optional[Iterable[T]] = None, 
        desc: str = "", 
        total: Optional[int] = None,
        monitor_resources: bool = True,
        update_interval: float = 0.5,
        **kwargs
    ):
        """Initialize the smart progress indicator.
        
        Args:
            iterable: The iterable to iterate over
            desc: Description of the progress bar
            total: Total number of items
            monitor_resources: Whether to monitor system resources
            update_interval: How often to update resource usage (seconds)
            **kwargs: Additional arguments to pass to tqdm
        """
        self.iterable = iterable
        self.desc = desc
        self.total = total
        self.monitor_resources = monitor_resources
        self.update_interval = update_interval
        self.kwargs = kwargs
        self.progress_bar: Any = None  # Will be initialized in __iter__
        self.last_update_time = time.time()
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        
        # Check if we're in a terminal that supports progress bars
        self.use_tqdm = HAS_TQDM and sys.stdout.isatty()
        
    def __iter__(self) -> Iterator[T]:
        """Iterate over the iterable with a progress bar."""
        if self.iterable is None:
            return iter([])  # type: ignore
            
        iter_obj = iter(self.iterable)
            
        if self.use_tqdm:
            # Set up the progress bar with our custom postfix
            self.progress_bar = TQDM_CLASS(
                iter_obj,
                desc=self.desc,
                total=self.total,
                **self.kwargs
            )
            
            for item in self.progress_bar:
                # Update system resource information
                if self.monitor_resources and time.time() - self.last_update_time > self.update_interval:
                    self._update_resource_info()
                    
                yield item
        else:
            # Fallback for non-terminal environments
            for item in iter_obj:
                yield item
                
    def _update_resource_info(self):
        """Update resource usage information."""
        if not self.monitor_resources:
            return
            
        try:
            # Get current CPU and memory usage
            self.cpu_usage = psutil.cpu_percent()
            self.memory_usage = psutil.virtual_memory().percent
            
            # Update the progress bar postfix with resource information
            if self.progress_bar is not None:
                self.progress_bar.set_postfix_str(
                    f"CPU: {self.cpu_usage:.1f}% | MEM: {self.memory_usage:.1f}%"
                )
            
            self.last_update_time = time.time()
        except Exception:
            # If we can't get resource information, just continue without it
            pass

# Enhanced version of tqdm with smart capabilities
def smart_progress(
    iterable: Optional[Iterable[T]] = None, 
    desc: str = "", 
    total: Optional[int] = None,
    monitor_resources: bool = True,
    **kwargs
) -> Iterator[T]:
    """Create a smart progress bar.
    
    Args:
        iterable: Iterable to track progress of
        desc: Description to display
        total: Total number of items
        monitor_resources: Whether to monitor system resources
        **kwargs: Additional arguments to pass to the progress bar
        
    Returns:
        Iterator that yields items from the iterable
    """
    progress = SmartProgress(iterable, desc, total, monitor_resources, **kwargs)
    return progress.__iter__()

# Adaptive rate limiting
class AdaptiveRateLimiter:
    """Adaptive rate limiter based on system resources."""
    
    def __init__(
        self, 
        base_rate_limit_sec: float = 1.0,
        min_rate_limit_sec: float = 0.1,
        max_rate_limit_sec: float = 5.0,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 90.0
    ):
        """Initialize the adaptive rate limiter.
        
        Args:
            base_rate_limit_sec: Base rate limit in seconds
            min_rate_limit_sec: Minimum rate limit in seconds
            max_rate_limit_sec: Maximum rate limit in seconds
            cpu_threshold: CPU usage threshold to adjust rate limit (%)
            memory_threshold: Memory usage threshold to adjust rate limit (%)
        """
        self.base_rate_limit_sec = base_rate_limit_sec
        self.min_rate_limit_sec = min_rate_limit_sec
        self.max_rate_limit_sec = max_rate_limit_sec
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.last_call_time = 0.0
        
    def get_current_limit(self) -> float:
        """Get the current rate limit based on system resources.
        
        Returns:
            float: The current rate limit in seconds
        """
        try:
            # Get current CPU and memory usage
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent
            
            # Calculate adjustment factor based on resource usage
            cpu_factor = min(1.0, max(0.0, cpu_usage / self.cpu_threshold))
            memory_factor = min(1.0, max(0.0, memory_usage / self.memory_threshold))
            
            # Use the higher of the two factors to determine throttling
            resource_factor = max(cpu_factor, memory_factor)
            
            # Calculate rate limit: start with base limit and then scale up 
            # towards max_rate_limit as resource usage increases
            rate_limit = self.base_rate_limit_sec + resource_factor * (
                self.max_rate_limit_sec - self.base_rate_limit_sec
            )
            
            # Ensure we're within bounds
            return float(max(self.min_rate_limit_sec, min(self.max_rate_limit_sec, rate_limit)))
        except Exception:
            # If we can't get resource information, fall back to base rate
            return float(self.base_rate_limit_sec)
        
    def wait(self):
        """Wait for the appropriate amount of time."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if self.last_call_time > 0:  # Skip wait on first call
            rate_limit = self.get_current_limit()
            
            # If we haven't waited long enough, sleep for the remaining time
            if time_since_last_call < rate_limit:
                time.sleep(rate_limit - time_since_last_call)
        
        # Update last call time
        self.last_call_time = time.time()

# Query filter management
class QueryFilterManager:
    """Manager for saving and loading query filters."""
    
    def __init__(self, config_dir: str):
        """Initialize the query filter manager.
        
        Args:
            config_dir: Directory where filter configurations are stored
        """
        from pathlib import Path
        
        self.config_dir = Path(config_dir)
        self.filters_dir = self.config_dir / "filters"
        
        # Create the filters directory if it doesn't exist
        self.filters_dir.mkdir(parents=True, exist_ok=True)
        
    def save_filter(self, name: str, filter_data: Dict[str, Any]) -> bool:
        """Save a filter configuration.
        
        Args:
            name: Name of the filter
            filter_data: Filter configuration data
            
        Returns:
            bool: True if the filter was saved successfully
        """
        import json
        
        try:
            # Ensure the name is valid as a filename
            safe_name = name.replace(" ", "-").replace("/", "_").lower()
            filter_path = self.filters_dir / f"{safe_name}.json"
            
            # Write the filter data to a JSON file
            with open(filter_path, 'w') as f:
                json.dump(filter_data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving filter: {e}")
            return False
            
    def load_filter(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a filter configuration.
        
        Args:
            name: Name of the filter
            
        Returns:
            Dict[str, Any]: Filter configuration data or None if not found
        """
        import json
        
        try:
            # Ensure the name is valid as a filename
            safe_name = name.replace(" ", "-").replace("/", "_").lower()
            filter_path = self.filters_dir / f"{safe_name}.json"
            
            # Check if the filter exists
            if not filter_path.exists():
                return None
                
            # Read the filter data from the JSON file
            with open(filter_path, 'r') as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except Exception as e:
            print(f"Error loading filter: {e}")
            return None
            
    def list_filters(self) -> List[str]:
        """List all available filters.
        
        Returns:
            List[str]: List of filter names
        """
        # Get all JSON files in the filters directory
        filter_files = list(self.filters_dir.glob("*.json"))
        
        # Extract the filter names (without extension)
        return [f.stem for f in filter_files]
        
    def delete_filter(self, name: str) -> bool:
        """Delete a filter configuration.
        
        Args:
            name: Name of the filter
            
        Returns:
            bool: True if the filter was deleted successfully
        """
        try:
            # Ensure the name is valid as a filename
            safe_name = name.replace(" ", "-").replace("/", "_").lower()
            filter_path = self.filters_dir / f"{safe_name}.json"
            
            # Check if the filter exists
            if not filter_path.exists():
                return False
                
            # Delete the filter file
            filter_path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting filter: {e}")
            return False
