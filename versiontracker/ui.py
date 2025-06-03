"""User interface utilities for VersionTracker."""

import shutil
import sys
import time
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    TypeVar,
)

import psutil

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
        """Fallback implementation for tqdm progress bar.

        This class provides a minimal implementation of the tqdm interface
        for use when the tqdm package is not available.
        """

        def __init__(self, iterable=None, desc=None, total=None, **kwargs):
            """Initialize the fallback progress bar.

            Args:
                iterable: Iterable to wrap
                desc: Description to display
                total: Total number of items (optional)
                **kwargs: Additional arguments (ignored)
            """
            self.iterable = iterable
            self.desc = desc
            self.total = total
            self.n = 0

            # Print initial message
            if desc:
                print(f"{desc}: started")

        def __iter__(self):
            """Iterate over the wrapped iterable."""
            if self.iterable is None:
                return iter([])

            # Print start
            count = 0
            for item in self.iterable:
                count += 1
                self.n = count
                yield item

            # Print completion
            if self.desc:
                print(f"{self.desc}: completed ({count} items)")

        def update(self, n=1):
            """Update progress by n items."""
            self.n += n

        def set_description(self, desc=None):
            """Set the description of the progress bar."""
            if desc:
                self.desc = desc
                print(f"Progress: {desc}")

        def refresh(self):
            """Refresh the display (no-op in fallback)."""
            pass

        def close(self):
            """Close the progress bar."""
            pass

        def __enter__(self):
            """Context manager entry."""
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            """Context manager exit."""
            _ = exc_type, exc_val, exc_tb
            self.close()

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
    def colored(text: object, color=None, on_color=None, attrs=None, *, no_color=None, force_color=None) -> str:
        """Fallback implementation of colored.

        Returns the text unmodified since color formatting is not available.

        Args:
            text: Text to format
            color: Foreground color (ignored in fallback)
            on_color: Background color (ignored in fallback)
            attrs: Text attributes (ignored in fallback)
            no_color: Disable color (ignored in fallback)
            force_color: Force color (ignored in fallback)

        Returns:
            str: The unmodified text
        """
        _ = color, on_color, attrs, no_color, force_color
        return str(text)

    def cprint(text: object, color=None, on_color=None, attrs=None, *, no_color=None, force_color=None, **kwargs) -> None:
        """Fallback implementation of cprint.

        Simply prints the text without color formatting.

        Args:
            text: Text to print
            color: Foreground color (ignored in fallback)
            on_color: Background color (ignored in fallback)
            attrs: Text attributes (ignored in fallback)
            no_color: Disable color (ignored in fallback)
            force_color: Force color (ignored in fallback)
            **kwargs: Additional arguments passed to print
        """
        _ = color, on_color, attrs, no_color, force_color
        print(text, **kwargs)


# Constants for terminal output
SUCCESS = "green"
INFO = "blue"
WARNING = "yellow"
ERROR = "red"
DEBUG = "cyan"

# Type variables for generics
T = TypeVar("T")
R = TypeVar("R")


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
        **kwargs,
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

    def color(self, color_name: str):
        """Return a function that applies the specified color to a string.

        Args:
            color_name: Name of the color to use

        Returns:
            Function that applies the color to a string
        """
        return lambda text: colored(text, color_name)

    def __iter__(self) -> Iterator[T]:
        """Iterate over the iterable with a progress bar."""
        if self.iterable is None:
            return iter([])  # type: ignore

        iter_obj = iter(self.iterable)

        if self.use_tqdm:
            # Set up the progress bar with our custom postfix
            self.progress_bar = TQDM_CLASS(
                iter_obj, desc=self.desc, total=self.total, **self.kwargs
            )

            for item in self.progress_bar:
                # Update system resource information
                if (
                    self.monitor_resources
                    and time.time() - self.last_update_time > self.update_interval
                ):
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


# Create a progress bar function (adapter for smart_progress)
def create_progress_bar():
    """Create a simple progress bar object that supports basic operations.

    This is a simplified adapter that provides compatibility with code expecting
    a progress bar object with basic operations.

    Returns:
        SmartProgress: A progress indicator object with color method
    """
    return SmartProgress()


# Enhanced version of tqdm with smart capabilities
def smart_progress(
    iterable: Optional[Iterable[T]] = None,
    desc: str = "",
    total: Optional[int] = None,
    monitor_resources: bool = True,
    **kwargs,
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
        memory_threshold: float = 90.0,
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
            return float(
                max(self.min_rate_limit_sec, min(self.max_rate_limit_sec, rate_limit))
            )
        except Exception:
            # If we can't get resource information, fall back to base rate
            return float(self.base_rate_limit_sec)

    def wait(self):
        """Wait for the appropriate amount of time."""
        current_time = time.time()
        
        # Skip wait on very first call (when last_call_time is still 0)
        if self.last_call_time == 0.0:
            self.last_call_time = current_time
            return
            
        time_since_last_call = current_time - self.last_call_time
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
        # Standard library import that's guaranteed to be available
        import json

        try:
            # Ensure the name is valid as a filename
            safe_name = name.replace(" ", "-").replace("/", "_").lower()
            filter_path = self.filters_dir / f"{safe_name}.json"

            # Write the filter data to a JSON file
            with open(filter_path, "w") as f:
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
        # Standard library import that's guaranteed to be available
        import json

        try:
            # Ensure the name is valid as a filename
            safe_name = name.replace(" ", "-").replace("/", "_").lower()
            filter_path = self.filters_dir / f"{safe_name}.json"

            # Check if the filter exists
            if not filter_path.exists():
                return None

            # Read the filter data from the JSON file
            with open(filter_path, "r") as f:
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


# Make FallbackTqdm available for testing purposes when tqdm is available
# This allows tests to import FallbackTqdm regardless of whether tqdm is installed
