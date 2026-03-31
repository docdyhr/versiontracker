"""Pytest configuration and fixtures for VersionTracker tests."""

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Ensure the project root is in the Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_subprocess() -> Generator[Mock, None, None]:
    """Mock subprocess.run for testing command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="", check_returncode=Mock())
        yield mock_run


@pytest.fixture
def mock_homebrew() -> Generator[Mock, None, None]:
    """Mock Homebrew operations."""
    with patch("versiontracker.homebrew.Homebrew") as mock_brew:
        instance = Mock()
        instance.search_casks.return_value = []
        instance.get_cask_info.return_value = None
        mock_brew.return_value = instance
        yield instance


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create a temporary configuration file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
cache:
    enabled: true
    ttl: 3600
    directory: /tmp/versiontracker_test
"""
    )
    return config_file


@pytest.fixture(autouse=True)
def reset_config() -> Generator[None, None, None]:
    """Reset the global config singleton before and after each test.

    The singleton lives at versiontracker.config._config_instance (module-level,
    not on the class). Resetting it to None ensures each test starts with a clean
    state and that lazy initialisation in get_config() triggers fresh.
    """
    import versiontracker.config as _cfg_mod

    original = _cfg_mod._config_instance
    _cfg_mod._config_instance = None
    yield
    _cfg_mod._config_instance = original


@pytest.fixture
def sample_app() -> dict[str, object]:
    """Create a sample application dictionary for testing."""
    return {
        "name": "Test App",
        "version": "1.2.3",
        "path": "/Applications/Test App.app",
        "bundle_id": "com.example.testapp",
    }


# Configure pytest plugins
pytest_plugins = [
    "pytest_cov",
]
