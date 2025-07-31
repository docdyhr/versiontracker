"""Application management module for VersionTracker."""

# Import cache components
# Import legacy functions from main apps.py file that weren't refactored
import importlib.util
import os
import sys
from typing import List

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

# Import the main apps.py file directly (not the apps/ package)
_apps_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "apps.py")
_spec = importlib.util.spec_from_file_location("versiontracker_apps_main", _apps_py_path)
if _spec is not None and _spec.loader is not None:
    _apps_main = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_apps_main)

    # Import ALL EXISTING functions from main apps.py (safe imports only)
    _batch_process_brew_search = _apps_main._batch_process_brew_search
    _check_cache_for_cask = _apps_main._check_cache_for_cask
    _create_rate_limiter = _apps_main._create_rate_limiter
    _execute_brew_search = _apps_main._execute_brew_search
    _get_error_message = _apps_main._get_error_message
    _get_existing_brews = _apps_main._get_existing_brews
    _handle_batch_error = _apps_main._handle_batch_error
    _handle_brew_search_result = _apps_main._handle_brew_search_result
    _handle_future_result = _apps_main._handle_future_result
    _populate_cask_versions = _apps_main._populate_cask_versions
    _process_batch_result = _apps_main._process_batch_result
    _process_brew_batch = _apps_main._process_brew_batch
    _process_brew_search_batches = _apps_main._process_brew_search_batches
    _process_with_progress_bar = _apps_main._process_with_progress_bar
    _process_without_progress_bar = _apps_main._process_without_progress_bar
    _should_show_progress = _apps_main._should_show_progress
    _update_cache_with_installable = _apps_main._update_cache_with_installable
    check_brew_install_candidates = _apps_main.check_brew_install_candidates
    check_brew_update_candidates = _apps_main.check_brew_update_candidates
    get_cask_version = _apps_main.get_cask_version
    get_homebrew_casks = _apps_main.get_homebrew_casks
    is_brew_cask_installable = _apps_main.is_brew_cask_installable

    # Import ALL EXISTING constants from main apps.py
    BREW_CMD = _apps_main.BREW_CMD
    BREW_PATH = _apps_main.BREW_PATH
    BREW_SEARCH = _apps_main.BREW_SEARCH
    HAS_PROGRESS = _apps_main.HAS_PROGRESS
    MAX_ERRORS = _apps_main.MAX_ERRORS
    _brew_casks_cache = _apps_main._brew_casks_cache
    _brew_search_cache = _apps_main._brew_search_cache
else:
    # Comprehensive fallback functions if main apps.py cannot be loaded
    def get_homebrew_casks() -> List[str]:
        return []

    def check_brew_install_candidates(*args, **kwargs):
        return []

    def _process_brew_batch(*args, **kwargs):
        return []

    def get_cask_version(*args, **kwargs):
        return None

    def is_brew_cask_installable(*args, **kwargs):
        return False

    def _create_rate_limiter(*args, **kwargs):
        return SimpleRateLimiter(1.0)

    def check_brew_update_candidates(*args, **kwargs):
        return []

    # Private function fallbacks
    def _batch_process_brew_search(*args, **kwargs):
        return []

    def _check_cache_for_cask(*args, **kwargs):
        return None

    def _execute_brew_search(*args, **kwargs):
        return []

    def _get_error_message(*args, **kwargs):
        return "Unknown error"

    def _get_existing_brews(*args, **kwargs):
        return []

    def _handle_batch_error(*args, **kwargs):
        return None

    def _handle_brew_search_result(*args, **kwargs):
        return None

    def _handle_future_result(*args, **kwargs):
        return None

    def _populate_cask_versions(*args, **kwargs):
        return {}

    def _process_batch_result(*args, **kwargs):
        return []

    def _process_brew_search_batches(*args, **kwargs):
        return []

    def _process_with_progress_bar(*args, **kwargs):
        return []

    def _process_without_progress_bar(*args, **kwargs):
        return []

    def _should_show_progress(*args, **kwargs):
        return False

    def _update_cache_with_installable(*args, **kwargs):
        return None

    # Fallback constants
    BREW_CMD = "brew"
    BREW_PATH = "/usr/local/bin/brew"
    BREW_SEARCH = "brew search --cask"
    HAS_PROGRESS = False
    MAX_ERRORS = 5
    _brew_casks_cache = {}
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
    "_brew_casks_cache",
    "_brew_search_cache",
    # Compatibility import for tests
    "partial_ratio",
]
