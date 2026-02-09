"""Batch processing utilities for version checking.

This module provides batch processing functions for checking application versions
against Homebrew casks, with support for parallel processing and progress reporting.
"""

from __future__ import annotations

import concurrent.futures
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from versiontracker.exceptions import NetworkError
from versiontracker.exceptions import TimeoutError as VTTimeoutError
from versiontracker.version.comparator import compare_versions, is_version_newer
from versiontracker.version.homebrew import get_homebrew_cask_info
from versiontracker.version.models import ApplicationInfo, VersionStatus

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

# Progress bar availability
HAS_BATCH_PROGRESS = False
try:
    from versiontracker.ui import smart_progress

    HAS_BATCH_PROGRESS = True
except ImportError:
    from collections.abc import Iterator as IteratorType

    def _fallback_progress[T](
        iterable: Iterable[T] | None = None,
        desc: str = "",
        total: int | None = None,
        monitor_resources: bool = True,
        **kwargs: Any,
    ) -> IteratorType[T]:
        """Fallback when smart_progress is not available."""
        if iterable is None:
            return iter([])
        return iter(iterable)

    smart_progress = _fallback_progress


def _get_config_settings() -> tuple[bool, int]:
    """Get configuration settings for batch processing.

    Returns:
        Tuple of (show_progress, max_workers)
    """
    try:
        from versiontracker.config import get_config

        config = get_config()
        # Access config settings via _config dict
        ui_settings = config._config.get("ui", {})
        show_progress = ui_settings.get("show_progress", True)
        perf_settings = config._config.get("performance", {})
        max_workers = perf_settings.get("max_workers", 4)
        return show_progress, max_workers
    except Exception:
        return True, 4


def process_single_app(
    app_info: tuple[str, str],
    use_enhanced_matching: bool = True,
) -> ApplicationInfo:
    """Process a single application to check its version status.

    Args:
        app_info: Tuple of (app_name, current_version)
        use_enhanced_matching: Whether to use enhanced fuzzy matching

    Returns:
        ApplicationInfo object with version status
    """
    app_name, current_version = app_info

    try:
        # Get Homebrew cask information
        homebrew_info = get_homebrew_cask_info(app_name, use_enhanced_matching)

        if not homebrew_info:
            return ApplicationInfo(
                name=app_name,
                version_string=current_version,
                status=VersionStatus.UNKNOWN,
                error_message="Not found in Homebrew",
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
            status=status,
        )

    except VTTimeoutError:
        return ApplicationInfo(
            name=app_name,
            version_string=current_version,
            status=VersionStatus.ERROR,
            error_message="Network timeout",
        )
    except (OSError, subprocess.SubprocessError, NetworkError) as e:
        logger.error("Error processing %s: %s", app_name, e)
        return ApplicationInfo(
            name=app_name,
            version_string=current_version,
            status=VersionStatus.ERROR,
            error_message=str(e),
        )


def process_app_batch(
    apps: list[tuple[str, str]],
    use_enhanced_matching: bool = True,
) -> list[ApplicationInfo]:
    """Process a batch of applications.

    Args:
        apps: List of application tuples (name, version)
        use_enhanced_matching: Whether to use enhanced fuzzy matching

    Returns:
        List of ApplicationInfo objects
    """
    return [process_single_app(app, use_enhanced_matching) for app in apps]


def create_app_batches(
    apps: list[tuple[str, str]],
    batch_size: int,
) -> list[list[tuple[str, str]]]:
    """Create batches of applications for parallel processing.

    Args:
        apps: List of applications
        batch_size: Size of each batch

    Returns:
        List of application batches
    """
    return [apps[i : i + batch_size] for i in range(0, len(apps), batch_size)]


def handle_batch_result(
    future: concurrent.futures.Future[list[ApplicationInfo]],
    results: list[ApplicationInfo],
    error_count: int,
    max_errors: int,
) -> int:
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
    except (RuntimeError, concurrent.futures.TimeoutError) as e:
        logger.error("Batch processing failed: %s", e)
        error_count += 1
        if error_count >= max_errors:
            raise NetworkError(f"Too many batch processing failures: {e}") from e
        return error_count


def check_outdated_apps(
    apps: list[tuple[str, str]],
    batch_size: int = 50,
    use_enhanced_matching: bool = True,
) -> list[tuple[str, dict[str, str], VersionStatus]]:
    """Check which applications are outdated compared to their Homebrew versions.

    Args:
        apps: List of applications with name and version
        batch_size: How many applications to check in one batch
        use_enhanced_matching: Whether to use enhanced fuzzy matching

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
    batches = create_app_batches(apps, batch_size)

    results: list[ApplicationInfo] = []
    error_count = 0
    max_errors = 3

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit batch processing tasks
        futures = [executor.submit(process_app_batch, batch, use_enhanced_matching) for batch in batches]

        # Process results as they complete with progress bar
        if HAS_BATCH_PROGRESS and show_progress:
            # Use smart progress to show progress with time estimation
            for future in smart_progress(
                concurrent.futures.as_completed(futures),
                total=len(futures),
                desc="Checking for updates",
                unit="batch",
                monitor_resources=True,
                ncols=80,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            ):
                error_count = handle_batch_result(future, results, error_count, max_errors)
        else:
            # Process without progress bar
            for future in concurrent.futures.as_completed(futures):
                error_count = handle_batch_result(future, results, error_count, max_errors)

    # Convert results to expected format
    return [
        (
            app_info.name,
            {
                "installed": app_info.version_string,
                "latest": app_info.latest_version or "Unknown",
            },
            app_info.status,
        )
        for app_info in results
    ]
