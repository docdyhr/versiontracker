"""Application management module for VersionTracker."""

# Import cache components
# Import legacy functions from main apps.py file that weren't refactored
import importlib.util
import os
import sys
from typing import List

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
    # Import the missing functions
    get_homebrew_casks = _apps_main.get_homebrew_casks
    check_brew_install_candidates = _apps_main.check_brew_install_candidates
    _process_brew_batch = _apps_main._process_brew_batch
    get_cask_version = _apps_main.get_cask_version
    is_brew_cask_installable = _apps_main.is_brew_cask_installable
    _create_rate_limiter = _apps_main._create_rate_limiter
else:

    def get_homebrew_casks() -> List[str]:
        """Fallback if main apps.py cannot be loaded."""
        return []

    def check_brew_install_candidates(*args, **kwargs):
        """Fallback if main apps.py cannot be loaded."""
        return []

    def _process_brew_batch(*args, **kwargs):
        """Fallback if main apps.py cannot be loaded."""
        return []

    def get_cask_version(*args, **kwargs):
        """Fallback if main apps.py cannot be loaded."""
        return None

    def is_brew_cask_installable(*args, **kwargs):
        """Fallback if main apps.py cannot be loaded."""
        return False

    def _create_rate_limiter(*args, **kwargs):
        """Fallback if main apps.py cannot be loaded."""
        return SimpleRateLimiter(1.0)


__all__ = [
    # Cache components
    "AdaptiveRateLimiter",
    "RateLimiter",
    "RateLimiterProtocol",
    "SimpleRateLimiter",
    "_AdaptiveRateLimiter",
    "clear_homebrew_casks_cache",
    # Finder components
    "get_applications",
    "get_applications_from_system_profiler",
    "get_homebrew_casks_list",
    "is_app_in_app_store",
    "is_homebrew_available",
    "_create_batches",
    # Matcher components
    "filter_brew_candidates",
    "filter_out_brews",
    "get_homebrew_cask_name",
    "search_brew_cask",
    "_process_brew_search",
    # Legacy functions from main apps.py
    "get_homebrew_casks",
    "check_brew_install_candidates",
    "_process_brew_batch",
    "get_cask_version",
    "is_brew_cask_installable",
    "_create_rate_limiter",
]
