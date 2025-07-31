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

    # Import ALL existing functions from main version.py (safe imports only)
    _apply_version_truncation = _version_main._apply_version_truncation
    _both_have_app_builds = _version_main._both_have_app_builds
    _build_final_version_tuple = _version_main._build_final_version_tuple
    _build_prerelease_tuple = _version_main._build_prerelease_tuple
    _build_with_metadata = _version_main._build_with_metadata
    _check_version_metadata = _version_main._check_version_metadata
    _clean_version_string = _version_main._clean_version_string
    _compare_application_builds = _version_main._compare_application_builds
    _compare_base_and_prerelease_versions = _version_main._compare_base_and_prerelease_versions
    _compare_base_versions = _version_main._compare_base_versions
    _compare_build_numbers = _version_main._compare_build_numbers
    _compare_none_suffixes = _version_main._compare_none_suffixes
    _compare_prerelease = _version_main._compare_prerelease
    _compare_prerelease_suffixes = _version_main._compare_prerelease_suffixes
    _compare_string_suffixes = _version_main._compare_string_suffixes
    _compare_unicode_suffixes = _version_main._compare_unicode_suffixes
    _convert_to_version_tuples = _version_main._convert_to_version_tuples
    _convert_versions_to_tuples = _version_main._convert_versions_to_tuples
    _create_app_batches = _version_main._create_app_batches
    _dict_to_tuple = _version_main._dict_to_tuple
    _extract_build_metadata = _version_main._extract_build_metadata
    _extract_build_number = _version_main._extract_build_number
    _extract_prerelease_info = _version_main._extract_prerelease_info
    _extract_prerelease_type_and_suffix = _version_main._extract_prerelease_type_and_suffix
    _get_config_settings = _version_main._get_config_settings
    _get_unicode_priority = _version_main._get_unicode_priority
    _handle_application_prefixes = _version_main._handle_application_prefixes
    _handle_batch_result = _version_main._handle_batch_result
    _handle_empty_and_malformed_versions = _version_main._handle_empty_and_malformed_versions
    _handle_empty_version_cases = _version_main._handle_empty_version_cases
    _handle_malformed_versions = _version_main._handle_malformed_versions
    _handle_mixed_format = _version_main._handle_mixed_format
    _handle_none_and_empty_versions = _version_main._handle_none_and_empty_versions
    _handle_semver_build_metadata = _version_main._handle_semver_build_metadata
    _handle_special_beta_format = _version_main._handle_special_beta_format
    _has_application_build_pattern = _version_main._has_application_build_pattern
    _is_mixed_format = _version_main._is_mixed_format
    _is_multi_component_version = _version_main._is_multi_component_version
    _is_prerelease = _version_main._is_prerelease
    _is_version_malformed = _version_main._is_version_malformed
    _normalize_app_version_string = _version_main._normalize_app_version_string
    _normalize_to_three_components = _version_main._normalize_to_three_components
    _parse_numeric_parts = _version_main._parse_numeric_parts
    _parse_or_default = _version_main._parse_or_default
    _parse_version_components = _version_main._parse_version_components
    _parse_version_to_dict = _version_main._parse_version_to_dict
    _perform_version_comparison = _version_main._perform_version_comparison
    _process_app_batch = _version_main._process_app_batch
    _process_single_app = _version_main._process_single_app
    _search_homebrew_casks = _version_main._search_homebrew_casks
    _set_version_comparison_status = _version_main._set_version_comparison_status
    _tuple_to_dict = _version_main._tuple_to_dict
    check_latest_version = _version_main.check_latest_version
    check_outdated_apps = _version_main.check_outdated_apps
    compare_fuzzy = _version_main.compare_fuzzy
    compose_version_tuple = _version_main.compose_version_tuple
    decompose_version = _version_main.decompose_version
    find_matching_cask = _version_main.find_matching_cask
    get_compiled_pattern = _version_main.get_compiled_pattern
    get_homebrew_cask_info = _version_main.get_homebrew_cask_info
    get_partial_ratio_scorer = _version_main.get_partial_ratio_scorer
    get_version_info = _version_main.get_version_info
    partial_ratio = _version_main.partial_ratio
    similarity_score = _version_main.similarity_score

    # Import ALL existing classes from main version.py
    # _EarlyReturn = _version_main._EarlyReturn  # Commented out due to duplicate definition issue

    # Import ALL existing constants from main version.py
    HAS_VERSION_PROGRESS = _version_main.HAS_VERSION_PROGRESS
    USE_FUZZYWUZZY = _version_main.USE_FUZZYWUZZY
    USE_RAPIDFUZZ = _version_main.USE_RAPIDFUZZ
    VERSION_PATTERNS = _version_main.VERSION_PATTERNS
    VERSION_PATTERN_DICT = _version_main.VERSION_PATTERN_DICT

else:
    # Comprehensive fallback functions if main version.py cannot be loaded
    def partial_ratio(s1: str, s2: str, score_cutoff: Optional[int] = None) -> int:
        """Fallback partial ratio function."""
        return 100 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0

    def similarity_score(s1: str, s2: str) -> int:
        """Fallback similarity score function."""
        return partial_ratio(s1, s2)

    # All other functions as no-op fallbacks
    def check_latest_version(*args, **kwargs): return None
    def check_outdated_apps(*args, **kwargs): return []
    def find_matching_cask(*args, **kwargs): return None
    def get_homebrew_cask_info(*args, **kwargs): return None
    def get_version_info(*args, **kwargs): return None
    def compare_fuzzy(*args, **kwargs): return 0
    def compose_version_tuple(*args, **kwargs): return (0, 0, 0)
    def decompose_version(*args, **kwargs): return {}
    def get_compiled_pattern(*args, **kwargs): 
        import re
        return re.compile(r".*")
    def _dict_to_tuple(*args, **kwargs): return (0, 0, 0)
    def _parse_version_components(*args, **kwargs): return {}
    def _parse_version_to_dict(*args, **kwargs): return {}
    def _tuple_to_dict(*args, **kwargs): return {}
    def get_partial_ratio_scorer(*args, **kwargs): return lambda x, y: 0
    
    # Private function fallbacks
    def _apply_version_truncation(*args, **kwargs): return None
    def _both_have_app_builds(*args, **kwargs): return False
    def _build_final_version_tuple(*args, **kwargs): return (0, 0, 0)
    def _build_prerelease_tuple(*args, **kwargs): return (0, 0, 0)
    def _build_with_metadata(*args, **kwargs): return None
    def _check_version_metadata(*args, **kwargs): return None
    def _clean_version_string(*args, **kwargs): return ""
    def _compare_application_builds(*args, **kwargs): return 0
    def _compare_base_and_prerelease_versions(*args, **kwargs): return 0
    def _compare_base_versions(*args, **kwargs): return 0
    def _compare_build_numbers(*args, **kwargs): return 0
    def _compare_none_suffixes(*args, **kwargs): return 0
    def _compare_prerelease(*args, **kwargs): return 0
    def _compare_prerelease_suffixes(*args, **kwargs): return 0
    def _compare_string_suffixes(*args, **kwargs): return 0
    def _compare_unicode_suffixes(*args, **kwargs): return 0
    def _convert_to_version_tuples(*args, **kwargs): return ((0, 0, 0), (0, 0, 0))
    def _convert_versions_to_tuples(*args, **kwargs): return ((0, 0, 0), (0, 0, 0))
    def _create_app_batches(*args, **kwargs): return []
    def _extract_build_metadata(*args, **kwargs): return None
    def _extract_build_number(*args, **kwargs): return None
    def _extract_prerelease_info(*args, **kwargs): return None
    def _extract_prerelease_type_and_suffix(*args, **kwargs): return (None, None)
    def _get_config_settings(*args, **kwargs): return {}
    def _get_unicode_priority(*args, **kwargs): return 0
    def _handle_application_prefixes(*args, **kwargs): return None
    def _handle_batch_result(*args, **kwargs): return None
    def _handle_empty_and_malformed_versions(*args, **kwargs): return None
    def _handle_empty_version_cases(*args, **kwargs): return None
    def _handle_malformed_versions(*args, **kwargs): return None
    def _handle_mixed_format(*args, **kwargs): return None
    def _handle_none_and_empty_versions(*args, **kwargs): return None
    def _handle_semver_build_metadata(*args, **kwargs): return None
    def _handle_special_beta_format(*args, **kwargs): return None
    def _has_application_build_pattern(*args, **kwargs): return False
    def _is_mixed_format(*args, **kwargs): return False
    def _is_multi_component_version(*args, **kwargs): return False
    def _is_prerelease(*args, **kwargs): return False
    def _is_version_malformed(*args, **kwargs): return False
    def _normalize_app_version_string(*args, **kwargs): return ""
    def _normalize_to_three_components(*args, **kwargs): return (0, 0, 0)
    def _parse_numeric_parts(*args, **kwargs): return []
    def _parse_or_default(*args, **kwargs): return 0
    def _perform_version_comparison(*args, **kwargs): return 0
    def _process_app_batch(*args, **kwargs): return []
    def _process_single_app(*args, **kwargs): return None
    def _search_homebrew_casks(*args, **kwargs): return []
    def _set_version_comparison_status(*args, **kwargs): return None
    
    # Fallback classes
    class _EarlyReturn:
        pass

    # Fallback constants
    HAS_VERSION_PROGRESS = False
    USE_FUZZYWUZZY = False
    USE_RAPIDFUZZ = False
    VERSION_PATTERN_DICT = {}
    import re
    VERSION_PATTERNS = [
        re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?$"),  # semantic
        re.compile(r"^(\d+)\.(\d+)$"),  # simple
    ]


__all__ = [
    # Models from submodules
    "ApplicationInfo",
    "VersionInfo",
    "VersionStatus",
    # Parser
    "parse_version",
    # Comparator
    "compare_versions",
    "is_version_newer",
    "get_version_difference",
    # ALL existing functions from main version.py
    "_apply_version_truncation",
    "_both_have_app_builds",
    "_build_final_version_tuple",
    "_build_prerelease_tuple",
    "_build_with_metadata",
    "_check_version_metadata",
    "_clean_version_string",
    "_compare_application_builds",
    "_compare_base_and_prerelease_versions",
    "_compare_base_versions",
    "_compare_build_numbers",
    "_compare_none_suffixes",
    "_compare_prerelease",
    "_compare_prerelease_suffixes",
    "_compare_string_suffixes",
    "_compare_unicode_suffixes",
    "_convert_to_version_tuples",
    "_convert_versions_to_tuples",
    "_create_app_batches",
    "_dict_to_tuple",
    "_extract_build_metadata",
    "_extract_build_number",
    "_extract_prerelease_info",
    "_extract_prerelease_type_and_suffix",
    "_get_config_settings",
    "_get_unicode_priority",
    "_handle_application_prefixes",
    "_handle_batch_result",
    "_handle_empty_and_malformed_versions",
    "_handle_empty_version_cases",
    "_handle_malformed_versions",
    "_handle_mixed_format",
    "_handle_none_and_empty_versions",
    "_handle_semver_build_metadata",
    "_handle_special_beta_format",
    "_has_application_build_pattern",
    "_is_mixed_format",
    "_is_multi_component_version",
    "_is_prerelease",
    "_is_version_malformed",
    "_normalize_app_version_string",
    "_normalize_to_three_components",
    "_parse_numeric_parts",
    "_parse_or_default",
    "_parse_version_components",
    "_parse_version_to_dict",
    "_perform_version_comparison",
    "_process_app_batch",
    "_process_single_app",
    "_search_homebrew_casks",
    "_set_version_comparison_status",
    "_tuple_to_dict",
    "check_latest_version",
    "check_outdated_apps",
    "compare_fuzzy",
    "compose_version_tuple",
    "decompose_version",
    "find_matching_cask",
    "get_compiled_pattern",
    "get_homebrew_cask_info",
    "get_partial_ratio_scorer",
    "get_version_info",
    "partial_ratio",
    "similarity_score",
    # Classes
    "_EarlyReturn",
    # Constants
    "HAS_VERSION_PROGRESS",
    "USE_FUZZYWUZZY",
    "USE_RAPIDFUZZ",
    "VERSION_PATTERNS",
    "VERSION_PATTERN_DICT",
]
