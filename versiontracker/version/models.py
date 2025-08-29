"""Data models and enums for version handling."""

from dataclasses import dataclass
from enum import Enum

# Forward reference for parse_version to avoid circular imports
from typing import TYPE_CHECKING

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
    bundle_id: str | None = None
    path: str | None = None
    homebrew_name: str | None = None
    latest_version: str | None = None
    latest_parsed: tuple[int, ...] | None = None
    status: VersionStatus = VersionStatus.UNKNOWN
    error_message: str | None = None
    outdated_by: tuple[int, ...] | None = None
    newer_by: tuple[int, ...] | None = None

    @property
    def parsed(self) -> tuple[int, ...] | None:
        """Get the parsed version tuple."""
        if not self.version_string or not self.version_string.strip():
            return None
        # Import here to avoid circular imports
        from .parser import parse_version

        return parse_version(self.version_string)


# Compatibility aliases
VersionInfo = ApplicationInfo  # Alias for backward compatibility
