"""Application management module for VersionTracker."""

# Import cache components
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
]
