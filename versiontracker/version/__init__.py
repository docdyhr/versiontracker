"""Version handling module for VersionTracker."""

# Import models
# Import comparator functions
# Import legacy functions from main version.py file that weren't refactored
import importlib.util
import os
from typing import Optional

from .comparator import compare_versions, get_version_difference, is_version_newer
from .models import ApplicationInfo, VersionInfo, VersionStatus

# Import parser functions
from .parser import parse_version

# Import the main version.py file directly (not the version/ package)
_version_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "version.py")
_spec = importlib.util.spec_from_file_location("versiontracker_version_main", _version_py_path)
if _spec is not None and _spec.loader is not None:
    _version_main = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_version_main)
    # Import the missing function
    partial_ratio = _version_main.partial_ratio
    similarity_score = _version_main.similarity_score
    check_latest_version = _version_main.check_latest_version
    check_outdated_apps = _version_main.check_outdated_apps
    find_matching_cask = _version_main.find_matching_cask
    get_homebrew_cask_info = _version_main.get_homebrew_cask_info
    get_version_info = _version_main.get_version_info
else:

    def partial_ratio(s1: str, s2: str, score_cutoff: Optional[int] = None) -> int:
        """Fallback partial ratio function."""
        return 100 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0

    def similarity_score(s1: str, s2: str) -> int:
        """Fallback similarity score function."""
        return partial_ratio(s1, s2)

    def check_latest_version(*args, **kwargs):
        """Fallback function."""
        return None

    def check_outdated_apps(*args, **kwargs):
        """Fallback function."""
        return []

    def find_matching_cask(*args, **kwargs):
        """Fallback function."""
        return None

    def get_homebrew_cask_info(*args, **kwargs):
        """Fallback function."""
        return None

    def get_version_info(*args, **kwargs):
        """Fallback function."""
        return None


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
    # Legacy functions from main version.py
    "partial_ratio",
    "similarity_score",
    "check_latest_version",
    "check_outdated_apps",
    "find_matching_cask",
    "get_homebrew_cask_info",
    "get_version_info",
]
