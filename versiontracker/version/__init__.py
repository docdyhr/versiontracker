"""Version handling module for VersionTracker."""

# Import models
# Import comparator functions
from .comparator import compare_versions, get_version_difference, is_version_newer
from .models import ApplicationInfo, VersionInfo, VersionStatus

# Import parser functions
from .parser import parse_version

# Note: Legacy functions remain in the main version.py file:
# - check_latest_version
# - check_outdated_apps
# - find_matching_cask
# - get_homebrew_cask_info
# - get_version_info
# - similarity_score
# - partial_ratio

__all__ = [
    # Models
    "ApplicationInfo",
    "VersionInfo",
    "VersionStatus",
    # Parser
    "parse_version",
    # Comparator
    "compare_versions",
    "is_version_newer",
    "get_version_difference",
]
