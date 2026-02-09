"""Homebrew integration for version checking.

This module provides functions for querying Homebrew cask information,
finding matching casks for applications, and checking latest versions.

Typical usage:
    from versiontracker.version.homebrew import get_homebrew_cask_info, check_latest_version

    info = get_homebrew_cask_info("firefox")
    # {'name': 'firefox', 'version': '121.0', 'description': '...'}

    version = check_latest_version("Visual Studio Code")
    # '1.85.1'
"""

import json
import logging
import subprocess

from versiontracker.exceptions import TimeoutError as VTTimeoutError
from versiontracker.utils import normalise_name
from versiontracker.version.fuzzy import get_fuzz

logger = logging.getLogger(__name__)


def get_homebrew_cask_info(app_name: str, use_enhanced: bool = True) -> dict[str, str] | None:
    """Get Homebrew cask information for an application.

    Queries Homebrew for cask information, first trying an exact match,
    then falling back to fuzzy search if needed.

    Args:
        app_name: Name of the application
        use_enhanced: Whether to use enhanced matching for fuzzy search

    Returns:
        Dictionary with cask information:
            - name: Cask token/name
            - version: Latest version available
            - description: Cask description
        Returns None if not found.

    Raises:
        VTTimeoutError: If Homebrew operation times out

    Examples:
        >>> get_homebrew_cask_info("firefox")
        {'name': 'firefox', 'version': '121.0', 'description': 'Web browser'}
    """
    try:
        # First try exact match
        # brew is a known system command, using list args is safe
        result = subprocess.run(  # nosec B603 B607
            ["brew", "info", "--cask", app_name, "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
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
                logger.warning("Failed to parse JSON for cask %s", app_name)

        # If exact match fails, try fuzzy search
        return _search_homebrew_casks(app_name, use_enhanced)

    except subprocess.TimeoutExpired:
        logger.warning("Timeout while checking Homebrew cask for %s", app_name)
        raise VTTimeoutError(f"Homebrew operation timed out for {app_name}") from None
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Error checking Homebrew cask for %s: %s", app_name, e)
        return None


def _get_homebrew_casks_list() -> list[str] | None:
    """Get list of all available Homebrew casks.

    Returns:
        List of cask names or None if operation fails

    Raises:
        VTTimeoutError: If Homebrew search times out
    """
    try:
        # brew is a known system command, using list args is safe
        result = subprocess.run(  # nosec B603 B607
            ["brew", "search", "--cask"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return None

        casks = result.stdout.strip().split("\n")
        casks = [cask.strip() for cask in casks if cask.strip()]

        return casks if casks else None

    except subprocess.TimeoutExpired:
        logger.warning("Timeout while fetching Homebrew casks list")
        raise VTTimeoutError("Homebrew search timed out") from None
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Error fetching Homebrew casks list: %s", e)
        return None


def _try_enhanced_cask_matching(app_name: str, casks: list[str]) -> str | None:
    """Try enhanced matching for cask search.

    Uses the enhanced_matching module if available for better matching.

    Args:
        app_name: Application name to match
        casks: List of available cask names

    Returns:
        Best matching cask name or None
    """
    try:
        from versiontracker.enhanced_matching import find_best_enhanced_match

        match_result = find_best_enhanced_match(app_name, casks, threshold=70)
        if match_result:
            return match_result[0]
    except ImportError:
        logger.debug("Enhanced matching not available, falling back to basic matching")

    return None


def _basic_fuzzy_cask_matching(app_name: str, casks: list[str]) -> str | None:
    """Perform basic fuzzy matching for cask search.

    Args:
        app_name: Application name to match
        casks: List of available cask names

    Returns:
        Best matching cask name or None
    """
    fuzz = get_fuzz()
    normalized_app_name = normalise_name(app_name)
    best_match: str | None = None
    best_score = 0

    for cask in casks:
        normalized_cask = normalise_name(cask)

        # Calculate similarity score
        if fuzz:
            score = fuzz.ratio(normalized_app_name, normalized_cask)
            if score > best_score and score > 70:  # Minimum threshold
                best_score = score
                best_match = cask

    return best_match


def _search_homebrew_casks(app_name: str, use_enhanced: bool = True) -> dict[str, str] | None:
    """Search for Homebrew casks using fuzzy matching.

    Args:
        app_name: Name of the application to search for
        use_enhanced: Whether to use enhanced matching

    Returns:
        Dictionary with cask information or None if not found

    Raises:
        VTTimeoutError: If Homebrew search times out
    """
    try:
        casks = _get_homebrew_casks_list()
        if not casks:
            return None

        # Try enhanced matching first if enabled
        best_match = None
        if use_enhanced:
            best_match = _try_enhanced_cask_matching(app_name, casks)

        # Fallback to basic fuzzy matching if enhanced didn't work
        if not best_match:
            best_match = _basic_fuzzy_cask_matching(app_name, casks)

        if best_match:
            return get_homebrew_cask_info(best_match)

        return None

    except subprocess.TimeoutExpired:
        logger.warning("Timeout while searching Homebrew casks for %s", app_name)
        raise VTTimeoutError(f"Homebrew search timed out for {app_name}") from None
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Error searching Homebrew casks for %s: %s", app_name, e)
        return None


def check_latest_version(app_name: str) -> str | None:
    """Check the latest version available for an application.

    Queries Homebrew for the latest version of the specified application.

    Args:
        app_name: Name of the application

    Returns:
        Latest version string or None if not found

    Examples:
        >>> check_latest_version("Firefox")
        '121.0'
        >>> check_latest_version("nonexistent-app")
        None
    """
    homebrew_info = get_homebrew_cask_info(app_name)
    if homebrew_info:
        return homebrew_info.get("version", None)
    return None


def find_matching_cask(app_name: str, threshold: int = 70, use_enhanced: bool = True) -> str | None:
    """Find a matching Homebrew cask for an application.

    Searches for a Homebrew cask that matches the given application name,
    using fuzzy matching to handle naming variations.

    Args:
        app_name: Name of the application
        threshold: Minimum similarity threshold (0-100)
        use_enhanced: Whether to use enhanced matching

    Returns:
        Name of matching cask or None if not found

    Examples:
        >>> find_matching_cask("Visual Studio Code")
        'visual-studio-code'
        >>> find_matching_cask("VS Code", threshold=60)
        'visual-studio-code'
    """
    try:
        # Get list of all casks
        # brew is a known system command, using list args is safe
        result = subprocess.run(  # nosec B603 B607
            ["brew", "search", "--cask"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return None

        casks = result.stdout.strip().split("\n")
        casks = [cask.strip() for cask in casks if cask.strip()]

        if not casks:
            return None

        # Use enhanced matching if available and enabled
        if use_enhanced:
            try:
                from versiontracker.enhanced_matching import find_best_enhanced_match

                match_result = find_best_enhanced_match(app_name, casks, threshold)
                if match_result:
                    return match_result[0]
            except ImportError:
                logger.debug("Enhanced matching not available, falling back to basic matching")

        # Fallback to basic fuzzy matching
        fuzz = get_fuzz()
        normalized_app_name = normalise_name(app_name)
        fallback_best_match: str | None = None
        best_score = 0

        for cask in casks:
            normalized_cask = normalise_name(cask)

            # Calculate similarity score
            if fuzz:
                score = fuzz.ratio(normalized_app_name, normalized_cask)
                if score > best_score and score >= threshold:
                    best_score = score
                    fallback_best_match = cask

        return fallback_best_match

    except (OSError, subprocess.SubprocessError, AttributeError) as e:
        logger.error("Error finding matching cask for %s: %s", app_name, e)
        return None


def is_homebrew_available() -> bool:
    """Check if Homebrew is available on the system.

    Returns:
        True if Homebrew is installed and accessible

    Examples:
        >>> is_homebrew_available()
        True  # On macOS with Homebrew installed
    """
    try:
        result = subprocess.run(  # nosec B603 B607
            ["brew", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return False
