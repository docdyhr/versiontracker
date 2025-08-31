"""Application management module for VersionTracker."""

# Import cache components
# Import legacy functions from main apps.py file that weren't refactored
import importlib.util
import os
from typing import Any

# Import cache functions that tests depend on
from ..cache import read_cache

# Import partial_ratio from version module for compatibility with tests
from ..version import partial_ratio
from .cache import (
    AdaptiveRateLimiter,
    RateLimiter,
    RateLimiterProtocol,
    SimpleRateLimiter,
    _AdaptiveRateLimiter,
    clear_homebrew_casks_cache,
)

# Import finder components
from .finder import (
    _create_batches,
    get_applications,
    get_applications_from_system_profiler,
    get_homebrew_casks_list,
    is_app_in_app_store,
    is_homebrew_available,
)

# Import matcher components
from .matcher import (
    _process_brew_search,
    filter_brew_candidates,
    filter_out_brews,
    get_homebrew_cask_name,
    search_brew_cask,
)

# Import the main app_finder.py file directly (not the apps/ package)
_apps_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app_finder.py")
_spec = importlib.util.spec_from_file_location("versiontracker_apps_main", _apps_py_path)
if _spec is not None and _spec.loader is not None:
    _apps_main = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_apps_main)

    # Import ALL EXISTING functions from main apps.py (safe imports only)

    def _batch_process_brew_search(*args: Any, **kwargs: Any) -> Any:
        """Process brew search in batches."""
        return _apps_main._batch_process_brew_search(*args, **kwargs)

    def _check_cache_for_cask(*args: Any, **kwargs: Any) -> Any:
        """Check cache for cask information."""
        return _apps_main._check_cache_for_cask(*args, **kwargs)

    def _create_rate_limiter(*args: Any, **kwargs: Any) -> Any:
        """Create appropriate rate limiter."""
        return _apps_main._create_rate_limiter(*args, **kwargs)

    def _execute_brew_search(*args: Any, **kwargs: Any) -> Any:
        """Execute brew search command."""
        return _apps_main._execute_brew_search(*args, **kwargs)

    def _get_error_message(*args: Any, **kwargs: Any) -> Any:
        """Get error message from exception."""
        return _apps_main._get_error_message(*args, **kwargs)

    def _get_existing_brews(*args: Any, **kwargs: Any) -> Any:
        """Get existing brew installations."""
        return _apps_main._get_existing_brews(*args, **kwargs)

    def _handle_batch_error(*args: Any, **kwargs: Any) -> Any:
        """Handle batch processing errors."""
        return _apps_main._handle_batch_error(*args, **kwargs)

    def _handle_brew_search_result(*args, **kwargs):
        """Handle brew search result."""
        return _apps_main._handle_brew_search_result(*args, **kwargs)

    def _handle_future_result(*args, **kwargs):
        """Handle future execution result."""
        return _apps_main._handle_future_result(*args, **kwargs)

    def _populate_cask_versions(*args, **kwargs):
        """Populate cask version information."""
        return _apps_main._populate_cask_versions(*args, **kwargs)

    def _process_batch_result(*args, **kwargs):
        """Process batch execution result."""
        return _apps_main._process_batch_result(*args, **kwargs)

    def _process_brew_batch(*args, **kwargs):
        """Process batch of brew operations."""
        return _apps_main._process_brew_batch(*args, **kwargs)

    def _process_brew_search_batches(*args, **kwargs):
        """Process brew search operations in batches."""
        return _apps_main._process_brew_search_batches(*args, **kwargs)

    def _process_with_progress_bar(*args, **kwargs):
        """Process operations with progress bar."""
        return _apps_main._process_with_progress_bar(*args, **kwargs)

    def _process_without_progress_bar(*args, **kwargs):
        """Process operations without progress bar."""
        return _apps_main._process_without_progress_bar(*args, **kwargs)

    def _should_show_progress(*args, **kwargs):
        """Determine if progress bar should be shown."""
        return _apps_main._should_show_progress(*args, **kwargs)

    def _update_cache_with_installable(*args, **kwargs):
        """Update cache with installable cask information."""
        return _apps_main._update_cache_with_installable(*args, **kwargs)

    def check_brew_install_candidates(*args: Any, **kwargs: Any) -> list[tuple[str, str, bool]]:
        """Check which applications can be installed via Homebrew."""
        return _apps_main.check_brew_install_candidates(*args, **kwargs)

    def check_brew_update_candidates(*args: Any, **kwargs: Any) -> list[tuple[str, str, str]]:
        """Check which Homebrew casks can be updated."""
        return _apps_main.check_brew_update_candidates(*args, **kwargs)

    def get_cask_version(*args: Any, **kwargs: Any) -> str | None:
        """Get version of a Homebrew cask."""
        return _apps_main.get_cask_version(*args, **kwargs)

    def get_homebrew_casks(*args: Any, **kwargs: Any) -> list[str]:
        """Get list of installed Homebrew casks."""
        return _apps_main.get_homebrew_casks(*args, **kwargs)

    # Expose the cache_clear method from the original decorated function
    get_homebrew_casks.cache_clear = _apps_main.get_homebrew_casks.cache_clear  # type: ignore  # type: ignore

    # Also expose the manual cache clearing function for comprehensive cache management
    get_homebrew_casks.clear_all_caches = _apps_main.clear_homebrew_casks_cache  # type: ignore

    def is_brew_cask_installable(*args: Any, **kwargs: Any) -> bool:
        """Check if a cask can be installed via Homebrew."""
        return _apps_main.is_brew_cask_installable(*args, **kwargs)

    def smart_progress(*args, **kwargs):
        """Smart progress bar wrapper."""
        return _apps_main.smart_progress(*args, **kwargs)

    def run_command(*args, **kwargs):
        """Run system command."""
        return _apps_main.run_command(*args, **kwargs)

    def write_cache(*args, **kwargs):
        """Write data to cache."""
        return _apps_main.write_cache(*args, **kwargs)

    # Import ALL EXISTING constants from main apps.py
    BREW_CMD = _apps_main.BREW_CMD
    BREW_PATH = _apps_main.BREW_PATH
    BREW_SEARCH = _apps_main.BREW_SEARCH
    HAS_PROGRESS = _apps_main.HAS_PROGRESS
    MAX_ERRORS = _apps_main.MAX_ERRORS
    _brew_search_cache = _apps_main._brew_search_cache
else:
    # Comprehensive fallback functions if main apps.py cannot be loaded
    def get_homebrew_casks(*args: Any, **kwargs: Any) -> list[str]:
        """Fallback: Get list of installed Homebrew casks."""
        return []

    def check_brew_install_candidates(*args: Any, **kwargs: Any) -> list[tuple[str, str, bool]]:
        """Fallback: Check which applications can be installed via Homebrew."""
        return []

    def _process_brew_batch(*args: Any, **kwargs: Any) -> Any:
        """Fallback: Process batch of brew operations."""
        return []

    def get_cask_version(*args: Any, **kwargs: Any) -> str | None:
        """Fallback: Get version of a Homebrew cask."""
        return None

    def is_brew_cask_installable(*args: Any, **kwargs: Any) -> bool:
        """Fallback: Check if a cask can be installed via Homebrew."""
        return False

    def _create_rate_limiter(*args: Any, **kwargs: Any) -> Any:
        """Fallback: Create appropriate rate limiter."""
        return SimpleRateLimiter(1.0)

    def run_command(*args: Any, **kwargs: Any) -> Any:
        """Fallback: Run system command."""
        return ("", 1)

    def write_cache(*args: Any, **kwargs: Any) -> Any:
        """Fallback: Write data to cache."""
        return False

    def check_brew_update_candidates(*args: Any, **kwargs: Any) -> list[tuple[str, str, str]]:
        """Fallback: Check which Homebrew casks can be updated."""
        return []

    # Private function fallbacks
    def _batch_process_brew_search(*args, **kwargs):
        """Fallback: Process brew search in batches."""
        return []

    def _check_cache_for_cask(*args, **kwargs):
        """Fallback: Check cache for cask information."""
        return None

    def _execute_brew_search(*args, **kwargs):
        """Fallback: Execute brew search command."""
        return []

    def _get_error_message(*args, **kwargs):
        """Fallback: Get error message from exception."""
        return "Unknown error"

    def _get_existing_brews(*args, **kwargs):
        """Fallback: Get existing brew installations."""
        return []

    def _handle_batch_error(*args: Any, **kwargs: Any) -> Any:
        """Fallback: Handle batch processing errors."""
        # Extract arguments for backward compatibility
        args[0] if len(args) > 0 else kwargs.get("error")
        error_count = args[1] if len(args) > 1 else kwargs.get("error_count", 0)
        batch = args[2] if len(args) > 2 else kwargs.get("batch", [])
        # Return proper tuple structure: (results, error_count, exception)
        failed_results = [(name, version, False) for name, version in batch] if batch else []
        return (failed_results, error_count + 1, None)

    def _handle_brew_search_result(*args, **kwargs):
        """Fallback: Handle brew search result."""
        return None

    def _handle_future_result(*args, **kwargs):
        """Fallback: Handle future execution result."""
        # Extract arguments for backward compatibility
        args[0] if len(args) > 0 else kwargs.get("future")
        name = args[1] if len(args) > 1 else kwargs.get("name", "unknown")
        version = args[2] if len(args) > 2 else kwargs.get("version", "0.0.0")
        # Return proper tuple structure: ((name, version, result), exception)
        return ((name, version, False), None)

    def _populate_cask_versions(*args, **kwargs):
        """Fallback: Populate cask version information."""
        return {}

    def _process_batch_result(*args, **kwargs):
        """Fallback: Process batch execution result."""
        return []

    def _process_brew_search_batches(*args, **kwargs):
        """Fallback: Process brew search operations in batches."""
        return []

    def _process_with_progress_bar(*args, **kwargs):
        """Fallback: Process operations with progress bar."""
        return []

    def _process_without_progress_bar(*args, **kwargs):
        """Fallback: Process operations without progress bar."""
        return []

    def _should_show_progress(*args, **kwargs):
        """Fallback: Determine if progress bar should be shown."""
        return False

    def _update_cache_with_installable(*args, **kwargs):
        """Fallback: Update cache with installable cask information."""
        return None

    # Fallback constants
    BREW_CMD = "brew"
    BREW_PATH = "/usr/local/bin/brew"
    BREW_SEARCH = "brew search --cask"
    HAS_PROGRESS = False
    MAX_ERRORS = 5
    _brew_search_cache = {}


__all__ = [
    # Cache components from submodules
    "AdaptiveRateLimiter",
    "RateLimiter",
    "RateLimiterProtocol",
    "SimpleRateLimiter",
    "_AdaptiveRateLimiter",
    "clear_homebrew_casks_cache",
    "read_cache",
    # Finder components from submodules
    "get_applications",
    "get_applications_from_system_profiler",
    "get_homebrew_casks_list",
    "is_app_in_app_store",
    "is_homebrew_available",
    "_create_batches",
    # Matcher components from submodules
    "filter_brew_candidates",
    "filter_out_brews",
    "get_homebrew_cask_name",
    "search_brew_cask",
    "_process_brew_search",
    # ALL functions from main apps.py
    "_batch_process_brew_search",
    "_check_cache_for_cask",
    "_create_rate_limiter",
    "_execute_brew_search",
    "_get_error_message",
    "_get_existing_brews",
    "_handle_batch_error",
    "_handle_brew_search_result",
    "_handle_future_result",
    "_populate_cask_versions",
    "_process_batch_result",
    "_process_brew_batch",
    "_process_brew_search_batches",
    "_process_with_progress_bar",
    "_process_without_progress_bar",
    "_should_show_progress",
    "_update_cache_with_installable",
    "check_brew_install_candidates",
    "check_brew_update_candidates",
    "get_cask_version",
    "get_homebrew_casks",
    "is_brew_cask_installable",
    # Constants
    "BREW_CMD",
    "BREW_PATH",
    "BREW_SEARCH",
    "HAS_PROGRESS",
    "MAX_ERRORS",
    "_brew_search_cache",
    # Compatibility import for tests
    "partial_ratio",
]
