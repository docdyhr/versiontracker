"""Version comparison and checking functionality for VersionTracker."""

# Standard library imports
import concurrent.futures
import logging
import multiprocessing
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from types import ModuleType
from typing import Dict, List, Optional, Tuple

# Internal imports
from versiontracker.exceptions import NetworkError, TimeoutError
from versiontracker.ui import smart_progress
from versiontracker.utils import normalise_name

# Third-party imports (optional with fallbacks)
try:
    from packaging import version as packaging_version
except ImportError:
    class _PackagingVersionStub(ModuleType):
        def parse(self, version_string):
            """Stub parse method."""
            return version_string
    packaging_version = _PackagingVersionStub("packaging.version")

# Try to import progress bar library
HAS_VERSION_PROGRESS = False
try:
    from tqdm.auto import tqdm
    HAS_VERSION_PROGRESS = True
except ImportError:
    class MinimalTqdm:
        """Minimal implementation of tqdm progress bar when the library is not available."""
        
        def __init__(self, iterable=None, **kwargs):
            """Initialize minimal progress bar."""
            self.iterable = iterable
            self.total = kwargs.get('total', 0)
            self.desc = kwargs.get('desc', '')
            
        def __iter__(self):
            """Return iterator over the iterable."""
            return iter(self.iterable) if self.iterable else iter([])
            
        def __enter__(self):
            """Context manager entry."""
            return self
            
        def __exit__(self, *args):
            """Context manager exit."""
            pass
            
        def update(self, n=1):
            """Update progress (no-op in minimal implementation)."""
            pass
    
    tqdm = MinimalTqdm

# Fuzzy matching library imports with fallbacks
USE_RAPIDFUZZ = False
USE_FUZZYWUZZY = False
fuzz = None
fuzz_process = None
_partial_ratio = None

try:
    import rapidfuzz.fuzz as rapidfuzz_fuzz
    import rapidfuzz.process as rapidfuzz_process
    from rapidfuzz.fuzz import partial_ratio as rapidfuzz_partial_ratio
    
    fuzz = rapidfuzz_fuzz
    fuzz_process = rapidfuzz_process
    _partial_ratio = rapidfuzz_partial_ratio
    USE_RAPIDFUZZ = True
except ImportError:
    try:
        import fuzzywuzzy.fuzz as fuzzywuzzy_fuzz
        import fuzzywuzzy.process as fuzzywuzzy_process
        from fuzzywuzzy.fuzz import partial_ratio as fuzzywuzzy_partial_ratio
        
        fuzz = fuzzywuzzy_fuzz
        fuzz_process = fuzzywuzzy_process
        _partial_ratio = fuzzywuzzy_partial_ratio
        USE_FUZZYWUZZY = True
    except ImportError:
        # Create minimal fallback implementations
        class MinimalFuzz:
            """Minimal implementation of fuzzy matching when no library is available."""
            
            @staticmethod
            def ratio(s1: str, s2: str, **kwargs) -> int:
                """Calculate the ratio of similarity between two strings."""
                return 100 if s1 == s2 else 0
            
            @staticmethod
            def partial_ratio(s1: str, s2: str, **kwargs) -> int:
                """Calculate the partial ratio of similarity between two strings."""
                return 100 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0
        
        class MinimalProcess:
            """Minimal implementation of fuzzy process matching."""
            
            @staticmethod
            def extractOne(query: str, choices: List[str], **kwargs) -> Optional[Tuple[str, int]]:
                """Extract the best match from choices."""
                if not choices:
                    return None
                
                best_match = None
                best_score = 0
                
                for choice in choices:
                    if query.lower() == choice.lower():
                        score = 100
                    elif query.lower() in choice.lower():
                        score = 80
                    elif choice.lower() in query.lower():
                        score = 70
                    else:
                        score = 0
                    
                    if score > best_score:
                        best_score = score
                        best_match = choice
                
                return (best_match, best_score) if best_match else (choices[0], 0)
        
        fuzz = MinimalFuzz()
        fuzz_process = MinimalProcess()
        _partial_ratio = fuzz.partial_ratio

# Set up logging
logger = logging.getLogger(__name__)


class VersionStatus(Enum):
    """Enumeration of version comparison results."""
    
    UP_TO_DATE = "up_to_date"
    OUTDATED = "outdated"
    NEWER = "newer"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class ApplicationInfo:
    """Information about an installed application."""
    
    name: str
    version_string: str
    bundle_id: Optional[str] = None
    path: Optional[str] = None
    homebrew_name: Optional[str] = None
    latest_version: Optional[str] = None
    status: VersionStatus = VersionStatus.UNKNOWN
    error_message: Optional[str] = None


@dataclass
class VersionInfo:
    """Information about a version comparison."""

    name: str
    version_string: str
    latest_version: Optional[str] = None
    latest_parsed: Optional[Tuple[int, ...]] = None
    status: VersionStatus = VersionStatus.UNKNOWN
    outdated_by: Optional[Tuple[int, int, int]] = None

    def __post_init__(self) -> None:
        self.parsed: Optional[Tuple[int, ...]] = parse_version(self.version_string)

        if self.latest_version and self.latest_parsed is None:
            self.latest_parsed = parse_version(self.latest_version)

        if self.parsed is not None and self.latest_parsed is not None:
            self.outdated_by = get_version_difference(self.parsed, self.latest_parsed)
            cmp = compare_versions(self.version_string, self.latest_version)
            if cmp < 0:
                self.status = VersionStatus.OUTDATED
            elif cmp > 0:
                self.status = VersionStatus.NEWER
            else:
                self.status = VersionStatus.UP_TO_DATE


def parse_version(version_string: Optional[str]) -> Optional[Tuple[int, ...]]:
    """Parse a version string into a tuple of integers for comparison.
    
    Args:
        version_string: The version string to parse
        
    Returns:
        Tuple of integers representing the version
        
    Examples:
        >>> parse_version("1.2.3")
        (1, 2, 3)
        >>> parse_version("2.0.1-beta")
        (2, 0, 1)
    """
    if not version_string or not str(version_string).strip():
        return None
    
    version_str = str(version_string)

    # Extract the first version-like substring
    match = re.search(r"\d+(?:\.\d+)*", version_str)
    if not match:
        return None

    parts = [int(p) for p in match.group(0).split(".") if p]

    while len(parts) < 3:
        parts.append(0)

    return tuple(parts[:3])


from typing import Union


def compare_versions(
    version1: Optional[Union[str, Tuple[int, ...]]],
    version2: Optional[Union[str, Tuple[int, ...]]],
) -> int:
    """Compare two version strings.
    
    Args:
        version1: First version string
        version2: Second version string
        
    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    def _to_tuple(v: Optional[Union[str, Tuple[int, ...]]]) -> Tuple[int, ...]:
        if isinstance(v, tuple):
            return v
        parsed = parse_version(v)
        return parsed or (0,)

    v1_tuple = _to_tuple(version1)
    v2_tuple = _to_tuple(version2)
    
    # Pad with zeros to make equal length
    max_len = max(len(v1_tuple), len(v2_tuple))
    v1_padded = v1_tuple + (0,) * (max_len - len(v1_tuple))
    v2_padded = v2_tuple + (0,) * (max_len - len(v2_tuple))
    
    if v1_padded < v2_padded:
        return -1
    elif v1_padded > v2_padded:
        return 1
    else:
        return 0


def get_version_difference(
    version1: Optional[str | Tuple[int, ...]],
    version2: Optional[str | Tuple[int, ...]],
) -> Optional[Tuple[int, int, int]]:
    """Return the difference between two versions.

    Args:
        version1: First version string or tuple
        version2: Second version string or tuple

    Returns:
        Tuple of (major_diff, minor_diff, patch_diff) or ``None`` if either
        version cannot be parsed.
    """

    v1_tuple = (
        version1 if isinstance(version1, tuple) else parse_version(version1)
    )
    v2_tuple = (
        version2 if isinstance(version2, tuple) else parse_version(version2)
    )

    if v1_tuple is None or v2_tuple is None:
        return None

    max_len = max(len(v1_tuple), len(v2_tuple), 3)
    v1_padded = v1_tuple + (0,) * (max_len - len(v1_tuple))
    v2_padded = v2_tuple + (0,) * (max_len - len(v2_tuple))

    return (
        v2_padded[0] - v1_padded[0],
        v2_padded[1] - v1_padded[1],
        v2_padded[2] - v1_padded[2],
    )


def is_version_newer(current: str, latest: str) -> bool:
    """Check if the latest version is newer than the current version.
    
    Args:
        current: Current version string
        latest: Latest version string
        
    Returns:
        True if latest is newer than current
    """
    return compare_versions(current, latest) < 0


@lru_cache(maxsize=128)
def get_homebrew_cask_info(app_name: str) -> Optional[Dict[str, str]]:
    """Get Homebrew cask information for an application.
    
    Args:
        app_name: Name of the application
        
    Returns:
        Dictionary with cask information or None if not found
    """
    try:
        # First try exact match
        result = subprocess.run(
            ["brew", "info", "--cask", app_name, "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        
        if result.returncode == 0:
            import json
            try:
                cask_data = json.loads(result.stdout)
                if cask_data and isinstance(cask_data, list) and len(cask_data) > 0:
                    cask = cask_data[0]
                    return {
                        "name": cask.get("token", app_name),
                        "version": cask.get("version", "unknown"),
                        "description": cask.get("desc", ""),
                    }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON for cask {app_name}")
        
        # If exact match fails, try fuzzy search
        return _search_homebrew_casks(app_name)
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout while checking Homebrew cask for {app_name}")
        raise TimeoutError(f"Homebrew operation timed out for {app_name}")
    except Exception as e:
        logger.error(f"Error checking Homebrew cask for {app_name}: {e}")
        return None


def _search_homebrew_casks(app_name: str) -> Optional[Dict[str, str]]:
    """Search for Homebrew casks using fuzzy matching.
    
    Args:
        app_name: Name of the application to search for
        
    Returns:
        Dictionary with cask information or None if not found
    """
    try:
        # Get list of all casks
        result = subprocess.run(
            ["brew", "search", "--cask"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )
        
        if result.returncode != 0:
            return None
        
        casks = result.stdout.strip().split('\n')
        casks = [cask.strip() for cask in casks if cask.strip()]
        
        if not casks:
            return None
        
        # Use fuzzy matching to find the best match
        normalized_app_name = normalise_name(app_name)
        best_match = None
        best_score = 0
        
        for cask in casks:
            normalized_cask = normalise_name(cask)
            
            # Calculate similarity score
            if fuzz:
                score = fuzz.ratio(normalized_app_name, normalized_cask)
                if score > best_score and score > 70:  # Minimum threshold
                    best_score = score
                    best_match = cask
        
        if best_match:
            # Get detailed info for the best match
            return get_homebrew_cask_info(best_match)
        
        return None
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout while searching Homebrew casks for {app_name}")
        raise TimeoutError(f"Homebrew search timed out for {app_name}")
    except Exception as e:
        logger.error(f"Error searching Homebrew casks for {app_name}: {e}")
        return None


def _get_config_settings() -> Tuple[bool, int]:
    """Get configuration settings for version checking.
    
    Returns:
        Tuple of (show_progress, max_workers)
    """
    try:
        from versiontracker.config import get_config

        config = get_config()
        show_progress = config.ui.progress if hasattr(config, 'ui') else True
        max_workers = min(
            config.performance.max_workers if hasattr(config, 'performance') else 4,
            multiprocessing.cpu_count()
        )
        return show_progress, max_workers
    except Exception:
        # Fallback to default values
        return True, min(4, multiprocessing.cpu_count())


def _process_single_app(app_info: Tuple[str, str]) -> ApplicationInfo:
    """Process a single application to check its version status.
    
    Args:
        app_info: Tuple of (app_name, current_version)
        
    Returns:
        ApplicationInfo object with version status
    """
    app_name, current_version = app_info
    
    try:
        # Get Homebrew cask information
        homebrew_info = get_homebrew_cask_info(app_name)
        
        if not homebrew_info:
            return ApplicationInfo(
                name=app_name,
                version_string=current_version,
                status=VersionStatus.UNKNOWN,
                error_message="Not found in Homebrew"
            )
        
        latest_version = homebrew_info.get("version", "unknown")
        homebrew_name = homebrew_info.get("name", app_name)
        
        # Compare versions
        if latest_version == "unknown" or latest_version == "latest":
            status = VersionStatus.UNKNOWN
        elif is_version_newer(current_version, latest_version):
            status = VersionStatus.OUTDATED
        elif compare_versions(current_version, latest_version) == 0:
            status = VersionStatus.UP_TO_DATE
        else:
            status = VersionStatus.NEWER
        
        return ApplicationInfo(
            name=app_name,
            version_string=current_version,
            homebrew_name=homebrew_name,
            latest_version=latest_version,
            status=status
        )
        
    except TimeoutError:
        return ApplicationInfo(
            name=app_name,
            version_string=current_version,
            status=VersionStatus.ERROR,
            error_message="Network timeout"
        )
    except Exception as e:
        logger.error(f"Error processing {app_name}: {e}")
        return ApplicationInfo(
            name=app_name,
            version_string=current_version,
            status=VersionStatus.ERROR,
            error_message=str(e)
        )


def _process_app_batch(apps: List[Tuple[str, str]]) -> List[ApplicationInfo]:
    """Process a batch of applications.
    
    Args:
        apps: List of application tuples (name, version)
        
    Returns:
        List of ApplicationInfo objects
    """
    return [_process_single_app(app) for app in apps]


def _create_app_batches(apps: List[Tuple[str, str]], batch_size: int) -> List[List[Tuple[str, str]]]:
    """Create batches of applications for parallel processing.
    
    Args:
        apps: List of applications
        batch_size: Size of each batch
        
    Returns:
        List of application batches
    """
    return [apps[i:i + batch_size] for i in range(0, len(apps), batch_size)]


def _handle_batch_result(future, results: List[ApplicationInfo], error_count: int, max_errors: int):
    """Handle the result of a batch processing future.
    
    Args:
        future: The completed future
        results: List to append successful results to
        error_count: Current error count
        max_errors: Maximum allowed errors
        
    Returns:
        Updated error count
        
    Raises:
        NetworkError: If too many errors occur
    """
    try:
        batch_results = future.result()
        results.extend(batch_results)
        return error_count
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        error_count += 1
        if error_count >= max_errors:
            raise NetworkError(f"Too many batch processing failures: {e}")
        return error_count


def check_outdated_apps(
    apps: List[Tuple[str, str]], batch_size: int = 50
) -> List[Tuple[str, Dict[str, str], VersionStatus]]:
    """Check which applications are outdated compared to their Homebrew versions.
    
    Args:
        apps: List of applications with name and version
        batch_size: How many applications to check in one batch
        
    Returns:
        List of tuples with application name, version info and status
        
    Raises:
        NetworkError: If there's a persistent network-related issue
        TimeoutError: If operations consistently time out
        RuntimeError: For other critical errors
    """
    if not apps:
        return []
    
    # Get configuration settings
    show_progress, max_workers = _get_config_settings()
    
    # Create batches for parallel processing
    batches = _create_app_batches(apps, batch_size)
    
    results: List[ApplicationInfo] = []
    error_count = 0
    max_errors = 3
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit batch processing tasks
        futures = [executor.submit(_process_app_batch, batch) for batch in batches]
        
        # Process results as they complete with progress bar
        if HAS_VERSION_PROGRESS and show_progress:
            # Use smart progress to show progress with time estimation and system resources
            for future in smart_progress(
                concurrent.futures.as_completed(futures),
                total=len(futures),
                desc="Checking for updates",
                unit="batch",
                monitor_resources=True,
                ncols=80,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            ):
                error_count = _handle_batch_result(future, results, error_count, max_errors)
        else:
            # Process without progress bar
            for future in concurrent.futures.as_completed(futures):
                error_count = _handle_batch_result(future, results, error_count, max_errors)
    
    # Convert results to expected format
    return [
        (
            app_info.name,
            {
                "installed": app_info.version_string,
                "latest": app_info.latest_version or "Unknown",
            },
            app_info.status
        )
        for app_info in results
    ]


def partial_ratio(s1: str, s2: str, score_cutoff: Optional[int] = None) -> int:
    """Calculate partial ratio between two strings.
    
    Provides compatibility between rapidfuzz and fuzzywuzzy, with fallbacks.
    
    Args:
        s1: First string to compare
        s2: Second string to compare
        score_cutoff: Optional score cutoff (ignored for compatibility)
        
    Returns:
        Similarity score from 0-100
    """
    if not s1 or not s2:
        return 0
    
    try:
        return int(_partial_ratio(s1, s2))
    except Exception as e:
        logger.error(f"Error calculating partial ratio for '{s1}' vs '{s2}': {e}")
        # Simple fallback
        return 100 if s1.lower() == s2.lower() else (70 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0)


def get_partial_ratio_scorer():
    """Return a scorer function compatible with rapidfuzz/fuzzywuzzy extractOne."""
    if USE_RAPIDFUZZ:
        def rapidfuzz_scorer(s1, s2, *, score_cutoff=None):
            return float(fuzz.partial_ratio(s1, s2))
        return rapidfuzz_scorer
    elif USE_FUZZYWUZZY:
        def fuzzywuzzy_scorer(s1, s2, *, score_cutoff=None):
            return float(fuzz.partial_ratio(s1, s2))
        return fuzzywuzzy_scorer
    else:
        def fallback_scorer(s1, s2, *, score_cutoff=None):
            return float(_partial_ratio(s1, s2))
        return fallback_scorer


# Export public interface
__all__ = [
    'VersionStatus',
    'ApplicationInfo',
    'VersionInfo',
    'parse_version',
    'compare_versions',
    'get_version_difference',
    'is_version_newer',
    'get_homebrew_cask_info',
    'check_outdated_apps',
    'get_partial_ratio_scorer',
    'partial_ratio'
]