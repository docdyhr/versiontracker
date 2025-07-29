"""Data models and enums for version handling."""

from dataclasses import dataclass
from enum import Enum

# Forward reference for parse_version to avoid circular imports
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    pass


class VersionStatus(Enum):
    """Enumeration of version comparison results."""

    UNKNOWN = 0
    UP_TO_DATE = 1
    OUTDATED = 2
    NEWER = 3
    NOT_FOUND = 4
    ERROR = 5


@dataclass
class ApplicationInfo:
    """Information about an installed application."""

    name: str
    version_string: str
    bundle_id: Optional[str] = None
    path: Optional[str] = None
    homebrew_name: Optional[str] = None
    latest_version: Optional[str] = None
    latest_parsed: Optional[Tuple[int, ...]] = None
    status: VersionStatus = VersionStatus.UNKNOWN
    error_message: Optional[str] = None
    outdated_by: Optional[Tuple[int, ...]] = None
    newer_by: Optional[Tuple[int, ...]] = None

    @property
    def parsed(self) -> Optional[Tuple[int, ...]]:
        """Get the parsed version tuple."""
        if not self.version_string or not self.version_string.strip():
            return None
        # Import here to avoid circular imports
        from .parser import parse_version

        return parse_version(self.version_string)


# Compatibility aliases
VersionInfo = ApplicationInfo  # Alias for backward compatibility
