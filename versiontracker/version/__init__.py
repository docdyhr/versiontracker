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

    # Import all legacy functions and constants from main version.py
    # Functions
    partial_ratio = _version_main.partial_ratio
    similarity_score = _version_main.similarity_score
    check_latest_version = _version_main.check_latest_version
    check_outdated_apps = _version_main.check_outdated_apps
    find_matching_cask = _version_main.find_matching_cask
    get_homebrew_cask_info = _version_main.get_homebrew_cask_info
    get_version_info = _version_main.get_version_info
    compare_fuzzy = _version_main.compare_fuzzy
    compose_version_tuple = _version_main.compose_version_tuple
    decompose_version = _version_main.decompose_version
    get_compiled_pattern = _version_main.get_compiled_pattern

    # Private functions (used in tests)
    _dict_to_tuple = _version_main._dict_to_tuple
    _parse_version_components = _version_main._parse_version_components
    _parse_version_to_dict = _version_main._parse_version_to_dict
    _tuple_to_dict = _version_main._tuple_to_dict

    # Constants
    USE_FUZZYWUZZY = _version_main.USE_FUZZYWUZZY
    USE_RAPIDFUZZ = _version_main.USE_RAPIDFUZZ
    VERSION_PATTERNS = _version_main.VERSION_PATTERNS
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

    def compare_fuzzy(*args, **kwargs):
        """Fallback function."""
        return 0

    def compose_version_tuple(*args, **kwargs):
        """Fallback function."""
        return (0, 0, 0)

    def decompose_version(*args, **kwargs):
        """Fallback function."""
        return {}

    def get_compiled_pattern(*args, **kwargs):
        """Fallback function."""
        import re

        return re.compile(r".*")

    def _dict_to_tuple(*args, **kwargs):
        """Fallback function."""
        return (0, 0, 0)

    def _parse_version_components(*args, **kwargs):
        """Fallback function."""
        return {}

    def _parse_version_to_dict(*args, **kwargs):
        """Fallback function."""
        return {}

    def _tuple_to_dict(*args, **kwargs):
        """Fallback function."""
        return {}

    # Fallback constants
    USE_FUZZYWUZZY = False
    USE_RAPIDFUZZ = False
    import re

    VERSION_PATTERNS = [
        re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?$"),  # semantic
        re.compile(r"^(\d+)\.(\d+)$"),  # simple
    ]


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
    "compare_fuzzy",
    "compose_version_tuple",
    "decompose_version",
    "get_compiled_pattern",
    # Private functions (used in tests)
    "_dict_to_tuple",
    "_parse_version_components",
    "_parse_version_to_dict",
    "_tuple_to_dict",
    # Constants
    "USE_FUZZYWUZZY",
    "USE_RAPIDFUZZ",
    "VERSION_PATTERNS",
]
