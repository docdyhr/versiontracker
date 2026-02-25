"""Version handling module for VersionTracker.

This package provides version parsing, comparison, and analysis functionality.
All public symbols are re-exported here for backward compatibility.
"""

# Models
# Batch processing
from .batch import (
    HAS_BATCH_PROGRESS,
    _get_config_settings,
    check_outdated_apps,
    create_app_batches,
    handle_batch_result,
    process_app_batch,
    process_single_app,
)
from .batch import check_outdated_apps as batch_check_outdated_apps

# Comparator
from .comparator import (
    _apply_version_truncation,
    _both_have_app_builds,
    _check_version_metadata,
    _compare_application_builds,
    _compare_base_and_prerelease_versions,
    _compare_base_versions,
    _compare_build_numbers,
    _compare_none_suffixes,
    _compare_prerelease,
    _compare_prerelease_suffixes,
    _compare_string_suffixes,
    _compare_unicode_suffixes,
    _convert_to_version_tuples,
    _convert_versions_to_tuples,
    _extract_build_number,
    _extract_prerelease_type_and_suffix,
    _get_unicode_priority,
    _handle_application_prefixes,
    _handle_empty_and_malformed_versions,
    _handle_empty_version_cases,
    _handle_malformed_versions,
    _handle_none_and_empty_versions,
    _handle_semver_build_metadata,
    _handle_standalone_unicode_chars,
    _has_application_build_pattern,
    _is_prerelease,
    _is_version_malformed,
    _map_unicode_to_english_type,
    _normalize_app_version_string,
    _parse_or_default,
    _perform_version_comparison,
    _process_prerelease_suffix,
    _set_version_comparison_status,
    compare_versions,
    get_version_difference,
    get_version_info,
    is_version_newer,
)

# Fuzzy matching
from .fuzzy import (
    USE_FUZZYWUZZY,
    USE_RAPIDFUZZ,
    compare_fuzzy,
    get_partial_ratio_scorer,
    partial_ratio,
    similarity_score,
)

# Homebrew integration
from .homebrew import (
    _search_homebrew_casks,
    check_latest_version,
    find_matching_cask,
    get_homebrew_cask_info,
)
from .models import ApplicationInfo, VersionInfo, VersionStatus

# Parser
from .parser import (
    _build_final_version_tuple,
    _build_prerelease_tuple,
    _build_with_metadata,
    _clean_version_string,
    _extract_build_metadata,
    _extract_prerelease_info,
    _handle_mixed_format,
    _handle_special_beta_format,
    _is_mixed_format,
    _is_multi_component_version,
    _normalize_to_three_components,
    _parse_numeric_parts,
    parse_version,
)

# Utilities
from .utils import (
    VERSION_PATTERN_DICT,
    VERSION_PATTERNS,
    _dict_to_tuple,
    _parse_version_components,
    _parse_version_to_dict,
    _tuple_to_dict,
    compose_version_tuple,
    decompose_version,
    get_compiled_pattern,
)

# Legacy aliases for renamed functions (backward compatibility)
_normalize_unicode_prerelease_type = _map_unicode_to_english_type
_parse_prerelease_suffix = _process_prerelease_suffix
_extract_standalone_unicode_prerelease = _handle_standalone_unicode_chars

# Legacy aliases for batch functions (were private, now public)
_create_app_batches = create_app_batches
_handle_batch_result = handle_batch_result
_process_app_batch = process_app_batch
_process_single_app = process_single_app

# Legacy constant alias
HAS_VERSION_PROGRESS = HAS_BATCH_PROGRESS

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
    "get_version_info",
    # Batch processing
    "batch_check_outdated_apps",
    "check_outdated_apps",
    "create_app_batches",
    "handle_batch_result",
    "process_app_batch",
    "process_single_app",
    # Fuzzy matching
    "compare_fuzzy",
    "get_partial_ratio_scorer",
    "partial_ratio",
    "similarity_score",
    # Homebrew
    "check_latest_version",
    "find_matching_cask",
    "get_homebrew_cask_info",
    # Utilities
    "compose_version_tuple",
    "decompose_version",
    "get_compiled_pattern",
    # Private helpers (exported for test compatibility)
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
    "_extract_standalone_unicode_prerelease",
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
    "_normalize_unicode_prerelease_type",
    "_parse_numeric_parts",
    "_parse_or_default",
    "_parse_prerelease_suffix",
    "_parse_version_components",
    "_parse_version_to_dict",
    "_perform_version_comparison",
    "_process_app_batch",
    "_process_single_app",
    "_search_homebrew_casks",
    "_set_version_comparison_status",
    "_tuple_to_dict",
    # Constants
    "HAS_VERSION_PROGRESS",
    "USE_FUZZYWUZZY",
    "USE_RAPIDFUZZ",
    "VERSION_PATTERNS",
    "VERSION_PATTERN_DICT",
]
