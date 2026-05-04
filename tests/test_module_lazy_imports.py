"""Tests for versiontracker.__init__ lazy-import __getattr__ paths."""

import pytest


def test_lazy_get_applications():
    """__getattr__ loads get_applications from apps on demand."""
    from versiontracker import __getattr__

    fn = __getattr__("get_applications")
    assert callable(fn)


def test_lazy_get_homebrew_casks():
    """__getattr__ loads get_homebrew_casks from apps on demand."""
    from versiontracker import __getattr__

    fn = __getattr__("get_homebrew_casks")
    assert callable(fn)


def test_lazy_config_class():
    """__getattr__ returns the real Config class."""
    from versiontracker import __getattr__
    from versiontracker.config import Config as RealConfig

    result = __getattr__("Config")
    assert result is RealConfig


def test_lazy_get_config():
    """__getattr__ returns the real get_config callable."""
    from versiontracker import __getattr__
    from versiontracker.config import get_config as real_get_config

    fn = __getattr__("get_config")
    assert fn is real_get_config


def test_lazy_version_tracker_error():
    """__getattr__ returns the real VersionTrackerError class."""
    from versiontracker import __getattr__
    from versiontracker.exceptions import VersionTrackerError as RealError

    result = __getattr__("VersionTrackerError")
    assert result is RealError


def test_lazy_unknown_attribute_raises():
    """__getattr__ raises AttributeError for unknown names."""
    from versiontracker import __getattr__

    with pytest.raises(AttributeError, match="no attribute"):
        __getattr__("completely_nonexistent_xyz_123")
